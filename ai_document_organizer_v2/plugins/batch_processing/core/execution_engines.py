"""
Execution Engines for the Batch Processing Plugin.

Provides thread-based and process-based execution engines for running
batch processing jobs, with resource monitoring and adaptive scaling.
"""

import os
import time
import logging
import threading
import multiprocessing
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, Future
from typing import Dict, List, Any, Optional, Set, Callable, Tuple, Union

import psutil

from ..models.job import Job, JobStatus, JobPriority
from ..jobs.job_queue import JobQueue

logger = logging.getLogger(__name__)

class ResourceMonitor:
    """
    Monitors system resources like CPU and memory usage.
    Provides feedback for adaptive worker scaling.
    """
    
    def __init__(self, interval: float = 1.0, 
                 cpu_limit: float = 0.9, 
                 memory_limit: float = 0.8):
        """
        Initialize the resource monitor.
        
        Args:
            interval: Monitoring interval in seconds
            cpu_limit: CPU usage limit as a fraction (0.0 to 1.0)
            memory_limit: Memory usage limit as a fraction (0.0 to 1.0)
        """
        self.interval = interval
        self.cpu_limit = cpu_limit
        self.memory_limit = memory_limit
        self._running = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._lock = threading.RLock()
        
        # Resource usage history
        self.cpu_history: List[float] = []
        self.memory_history: List[float] = []
        self.history_size = 10  # Keep last N measurements
        
        # Current values
        self.current_cpu_usage = 0.0
        self.current_memory_usage = 0.0
        self.disk_io_usage = 0.0
        self.network_io_usage = 0.0
        self.last_updated = 0.0
        
    def start(self) -> None:
        """Start resource monitoring."""
        with self._lock:
            if self._running:
                return
            
            self._running = True
            self._monitor_thread = threading.Thread(
                target=self._monitor_resources,
                daemon=True,
                name="ResourceMonitorThread"
            )
            self._monitor_thread.start()
            logger.debug("Resource monitor started")
    
    def stop(self) -> None:
        """Stop resource monitoring."""
        with self._lock:
            if not self._running:
                return
            
            self._running = False
            if self._monitor_thread:
                self._monitor_thread.join(timeout=5.0)
                self._monitor_thread = None
            
            logger.debug("Resource monitor stopped")
    
    def _monitor_resources(self) -> None:
        """Monitor system resources at regular intervals."""
        while self._running:
            try:
                # Get CPU and memory usage
                self.current_cpu_usage = psutil.cpu_percent(interval=None) / 100.0
                self.current_memory_usage = psutil.virtual_memory().percent / 100.0
                
                # Get disk and network I/O rates
                # These would typically require comparing values over time
                # for a simplified example, we'll just get current values
                self.disk_io_usage = psutil.disk_io_counters().read_bytes + psutil.disk_io_counters().write_bytes
                self.network_io_usage = psutil.net_io_counters().bytes_sent + psutil.net_io_counters().bytes_recv
                
                self.last_updated = time.time()
                
                # Update history with new values
                with self._lock:
                    self.cpu_history.append(self.current_cpu_usage)
                    self.memory_history.append(self.current_memory_usage)
                    
                    # Keep history at desired size
                    while len(self.cpu_history) > self.history_size:
                        self.cpu_history.pop(0)
                    while len(self.memory_history) > self.history_size:
                        self.memory_history.pop(0)
                
                # Sleep for the monitoring interval
                time.sleep(self.interval)
            
            except Exception as e:
                logger.error(f"Error in resource monitoring: {e}")
                time.sleep(self.interval)
    
    def get_average_cpu_usage(self) -> float:
        """
        Get the average CPU usage from history.
        
        Returns:
            Average CPU usage as a fraction (0.0 to 1.0)
        """
        with self._lock:
            if not self.cpu_history:
                return 0.0
            return sum(self.cpu_history) / len(self.cpu_history)
    
    def get_average_memory_usage(self) -> float:
        """
        Get the average memory usage from history.
        
        Returns:
            Average memory usage as a fraction (0.0 to 1.0)
        """
        with self._lock:
            if not self.memory_history:
                return 0.0
            return sum(self.memory_history) / len(self.memory_history)
    
    def is_cpu_overloaded(self) -> bool:
        """
        Check if CPU is overloaded.
        
        Returns:
            True if CPU usage exceeds the limit
        """
        return self.get_average_cpu_usage() > self.cpu_limit
    
    def is_memory_overloaded(self) -> bool:
        """
        Check if memory is overloaded.
        
        Returns:
            True if memory usage exceeds the limit
        """
        return self.get_average_memory_usage() > self.memory_limit
    
    def get_resource_usage(self) -> Dict[str, Any]:
        """
        Get current resource usage statistics.
        
        Returns:
            Dictionary with resource usage information
        """
        return {
            "cpu_usage": self.current_cpu_usage,
            "memory_usage": self.current_memory_usage,
            "disk_io_usage": self.disk_io_usage,
            "network_io_usage": self.network_io_usage,
            "cpu_average": self.get_average_cpu_usage(),
            "memory_average": self.get_average_memory_usage(),
            "last_updated": self.last_updated,
            "cpu_overloaded": self.is_cpu_overloaded(),
            "memory_overloaded": self.is_memory_overloaded()
        }
    
    def can_add_workers(self, count: int = 1) -> bool:
        """
        Check if resources are available to add more workers.
        
        Args:
            count: Number of workers to add
            
        Returns:
            True if resources are available
        """
        cpu_headroom = self.cpu_limit - self.get_average_cpu_usage()
        memory_headroom = self.memory_limit - self.get_average_memory_usage()
        
        # Estimate resource needs per worker
        # This is a simplified model - in production, you'd want to track
        # actual usage per worker type
        cpu_per_worker = 0.1  # Assuming one worker uses ~10% CPU
        memory_per_worker = 0.05  # Assuming one worker uses ~5% memory
        
        return (cpu_headroom >= cpu_per_worker * count and 
                memory_headroom >= memory_per_worker * count)


class ExecutionEngine:
    """
    Base class for execution engines that process jobs from a queue.
    """
    
    def __init__(self, job_queue: JobQueue, max_workers: int = None,
                 resource_monitor: Optional[ResourceMonitor] = None):
        """
        Initialize the execution engine.
        
        Args:
            job_queue: Queue to process jobs from
            max_workers: Maximum number of worker threads/processes
            resource_monitor: Optional resource monitor for adaptive scaling
        """
        self.job_queue = job_queue
        self.max_workers = max_workers or self._get_default_worker_count()
        self.resource_monitor = resource_monitor
        
        self._running = False
        self._futures: Dict[str, Tuple[Future, Job]] = {}
        self._lock = threading.RLock()
    
    def _get_default_worker_count(self) -> int:
        """
        Get the default worker count based on system resources.
        
        Returns:
            Default worker count
        """
        return max(1, min(32, multiprocessing.cpu_count()))
    
    def start(self) -> bool:
        """
        Start the execution engine.
        
        Returns:
            True if the engine was started successfully
        """
        raise NotImplementedError("Subclasses must implement start()")
    
    def stop(self) -> bool:
        """
        Stop the execution engine.
        
        Returns:
            True if the engine was stopped successfully
        """
        raise NotImplementedError("Subclasses must implement stop()")
    
    def submit_job(self, job: Job) -> bool:
        """
        Submit a job for execution.
        
        Args:
            job: Job to submit
            
        Returns:
            True if the job was submitted successfully
        """
        raise NotImplementedError("Subclasses must implement submit_job()")
    
    def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a running job.
        
        Args:
            job_id: ID of the job to cancel
            
        Returns:
            True if the job was canceled successfully
        """
        raise NotImplementedError("Subclasses must implement cancel_job()")
    
    def pause_job(self, job_id: str) -> bool:
        """
        Pause a running job.
        
        Args:
            job_id: ID of the job to pause
            
        Returns:
            True if the job was paused successfully
        """
        raise NotImplementedError("Subclasses must implement pause_job()")
    
    def resume_job(self, job_id: str) -> bool:
        """
        Resume a paused job.
        
        Args:
            job_id: ID of the job to resume
            
        Returns:
            True if the job was resumed successfully
        """
        raise NotImplementedError("Subclasses must implement resume_job()")
    
    def get_active_jobs(self) -> List[Job]:
        """
        Get a list of currently active jobs.
        
        Returns:
            List of active jobs
        """
        raise NotImplementedError("Subclasses must implement get_active_jobs()")


class ThreadExecutionEngine(ExecutionEngine):
    """
    Thread-based execution engine that processes jobs using a thread pool.
    """
    
    def __init__(self, job_queue: JobQueue, max_workers: int = None,
                 resource_monitor: Optional[ResourceMonitor] = None,
                 adaptive_scaling: bool = True,
                 scaling_interval: float = 5.0):
        """
        Initialize the thread execution engine.
        
        Args:
            job_queue: Queue to process jobs from
            max_workers: Maximum number of worker threads
            resource_monitor: Optional resource monitor for adaptive scaling
            adaptive_scaling: Whether to dynamically adjust worker count
            scaling_interval: Interval in seconds for checking if scaling is needed
        """
        super().__init__(job_queue, max_workers, resource_monitor)
        
        self._executor: Optional[ThreadPoolExecutor] = None
        self._scheduler_thread: Optional[threading.Thread] = None
        self._adaptive_scaling = adaptive_scaling
        self._scaling_interval = scaling_interval
        self._current_worker_count = 0
    
    def start(self) -> bool:
        """
        Start the thread execution engine.
        
        Returns:
            True if the engine was started successfully
        """
        with self._lock:
            if self._running:
                return True
            
            try:
                self._running = True
                
                # Create thread pool
                self._executor = ThreadPoolExecutor(
                    max_workers=self.max_workers,
                    thread_name_prefix="BatchWorker"
                )
                
                # Start resource monitor if available
                if self.resource_monitor:
                    self.resource_monitor.start()
                
                # Start scheduler thread
                self._scheduler_thread = threading.Thread(
                    target=self._scheduler_loop,
                    daemon=True,
                    name="BatchSchedulerThread"
                )
                self._scheduler_thread.start()
                
                logger.info(f"Started thread execution engine with {self.max_workers} workers")
                return True
            
            except Exception as e:
                logger.error(f"Error starting thread execution engine: {e}")
                self._running = False
                return False
    
    def stop(self) -> bool:
        """
        Stop the thread execution engine.
        
        Returns:
            True if the engine was stopped successfully
        """
        with self._lock:
            if not self._running:
                return True
            
            try:
                self._running = False
                
                # Stop resource monitor if available
                if self.resource_monitor:
                    self.resource_monitor.stop()
                
                # Wait for scheduler thread to finish
                if self._scheduler_thread:
                    self._scheduler_thread.join(timeout=5.0)
                
                # Cancel and shutdown executor
                if self._executor:
                    self._executor.shutdown(wait=False, cancel_futures=True)
                    self._executor = None
                
                logger.info("Stopped thread execution engine")
                return True
            
            except Exception as e:
                logger.error(f"Error stopping thread execution engine: {e}")
                return False
    
    def submit_job(self, job: Job) -> bool:
        """
        Submit a job for execution.
        
        Args:
            job: Job to submit
            
        Returns:
            True if the job was submitted successfully
        """
        if not self._running or not self._executor:
            return False
        
        try:
            # Add the job to the queue
            success = self.job_queue.add_job(job)
            return success
        
        except Exception as e:
            logger.error(f"Error submitting job {job.job_id}: {e}")
            return False
    
    def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a running job.
        
        Args:
            job_id: ID of the job to cancel
            
        Returns:
            True if the job was canceled successfully
        """
        with self._lock:
            if job_id in self._futures:
                future, job = self._futures[job_id]
                future.cancel()
                job.mark_canceled()
                del self._futures[job_id]
                return True
            
            # If the job is in the queue but not running
            return self.job_queue.cancel_job(job_id)
    
    def pause_job(self, job_id: str) -> bool:
        """
        Pause a running job.
        
        Args:
            job_id: ID of the job to pause
            
        Returns:
            True if the job was paused successfully
        """
        # Note: True pause/resume is tricky with ThreadPoolExecutor
        # as it doesn't support pausing futures
        # This implementation marks the job as paused but can't actually
        # pause execution once it's started
        with self._lock:
            if job_id in self._futures:
                _, job = self._futures[job_id]
                job.mark_paused()
                # We don't actually pause execution, just mark it paused
                # In a more sophisticated implementation, jobs could check
                # for pause signals and yield execution
                return True
            
            # If the job is in the queue but not running
            return self.job_queue.pause_job(job_id)
    
    def resume_job(self, job_id: str) -> bool:
        """
        Resume a paused job.
        
        Args:
            job_id: ID of the job to resume
            
        Returns:
            True if the job was resumed successfully
        """
        # Since we can't truly pause jobs, resume just resubmits the job
        # to the queue if it's paused
        with self._lock:
            job = self.job_queue.get_job(job_id)
            if not job or job.status != JobStatus.PAUSED:
                return False
            
            return self.job_queue.resume_job(job_id)
    
    def get_active_jobs(self) -> List[Job]:
        """
        Get a list of currently active jobs.
        
        Returns:
            List of active jobs
        """
        with self._lock:
            return [job for _, job in self._futures.values()]
    
    def _scheduler_loop(self) -> None:
        """
        Main scheduler loop that processes jobs from the queue.
        """
        logger.debug("Starting scheduler loop")
        
        while self._running:
            try:
                # Adaptive scaling if enabled and resource monitor available
                if (self._adaptive_scaling and 
                    self.resource_monitor and 
                    self._executor):
                    self._adjust_worker_count()
                
                # Get next job from the queue
                job = self.job_queue.get_next_job(timeout=1.0)
                if not job or not self._running:
                    continue
                
                # Execute the job
                if self._executor:
                    future = self._executor.submit(
                        self._execute_job,
                        job
                    )
                    
                    # Store future and job
                    with self._lock:
                        self._futures[job.job_id] = (future, job)
                    
                    # Add callback to handle job completion
                    future.add_done_callback(
                        lambda f, job_id=job.job_id: self._handle_job_completion(f, job_id)
                    )
                    
                    logger.debug(f"Scheduled job {job.job_id} for execution")
            
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                time.sleep(1.0)
        
        logger.debug("Scheduler loop stopped")
    
    def _execute_job(self, job: Job) -> Any:
        """
        Execute a job and handle the result.
        
        Args:
            job: Job to execute
            
        Returns:
            Result of the job execution
        """
        try:
            # Update job status
            job.mark_running()
            self.job_queue.update_job(job)
            
            logger.debug(f"Executing job {job.job_id}: {job.name}")
            
            # Execute the job function
            result = job.func(*job.args, **job.kwargs)
            
            # Mark job as completed
            job.mark_completed(result)
            self.job_queue.update_job(job)
            
            logger.debug(f"Job {job.job_id} completed successfully")
            return result
        
        except Exception as e:
            logger.error(f"Error executing job {job.job_id}: {e}")
            job.mark_failed(e)
            self.job_queue.update_job(job)
            
            # If job can be retried, requeue it
            if job.can_retry():
                logger.info(f"Retrying job {job.job_id} (attempt {job.retries + 1}/{job.max_retries})")
                self.job_queue.retry_job(job.job_id)
            
            raise
    
    def _handle_job_completion(self, future: Future, job_id: str) -> None:
        """
        Handle the completion of a job.
        
        Args:
            future: Future object for the job
            job_id: ID of the completed job
        """
        with self._lock:
            if job_id in self._futures:
                del self._futures[job_id]
    
    def _adjust_worker_count(self) -> None:
        """
        Adjust the number of workers based on resource usage.
        """
        if not self.resource_monitor or not self._executor:
            return
        
        try:
            # Get resource usage
            usage = self.resource_monitor.get_resource_usage()
            
            # Get current worker count from executor
            # This is a bit of a hack since ThreadPoolExecutor doesn't expose this
            workers = getattr(self._executor, "_max_workers", self.max_workers)
            
            # Check if resources are overloaded
            if usage["cpu_overloaded"] or usage["memory_overloaded"]:
                # Reduce workers by 25% but keep at least 1
                new_workers = max(1, int(workers * 0.75))
                if new_workers < workers:
                    logger.info(f"Resources overloaded, reducing workers from {workers} to {new_workers}")
                    # Create a new executor with fewer workers
                    new_executor = ThreadPoolExecutor(
                        max_workers=new_workers,
                        thread_name_prefix="BatchWorker"
                    )
                    
                    # Replace the old executor
                    old_executor = self._executor
                    self._executor = new_executor
                    
                    # Shutdown the old executor gracefully
                    old_executor.shutdown(wait=False, cancel_futures=False)
            
            # Check if resources are underutilized
            elif (not usage["cpu_overloaded"] and 
                  not usage["memory_overloaded"] and
                  workers < self.max_workers and
                  self.resource_monitor.can_add_workers()):
                
                # Increase workers by 25% but don't exceed max_workers
                new_workers = min(self.max_workers, int(workers * 1.25) + 1)
                if new_workers > workers:
                    logger.info(f"Resources underutilized, increasing workers from {workers} to {new_workers}")
                    # Create a new executor with more workers
                    new_executor = ThreadPoolExecutor(
                        max_workers=new_workers,
                        thread_name_prefix="BatchWorker"
                    )
                    
                    # Replace the old executor
                    old_executor = self._executor
                    self._executor = new_executor
                    
                    # Shutdown the old executor gracefully
                    old_executor.shutdown(wait=False, cancel_futures=False)
        
        except Exception as e:
            logger.error(f"Error adjusting worker count: {e}")


class ProcessExecutionEngine(ExecutionEngine):
    """
    Process-based execution engine that processes jobs using a process pool.
    Suitable for CPU-intensive tasks that benefit from parallel processing.
    """
    
    def __init__(self, job_queue: JobQueue, max_workers: int = None,
                 resource_monitor: Optional[ResourceMonitor] = None,
                 adaptive_scaling: bool = True,
                 scaling_interval: float = 10.0):
        """
        Initialize the process execution engine.
        
        Args:
            job_queue: Queue to process jobs from
            max_workers: Maximum number of worker processes
            resource_monitor: Optional resource monitor for adaptive scaling
            adaptive_scaling: Whether to dynamically adjust worker count
            scaling_interval: Interval in seconds for checking if scaling is needed
        """
        super().__init__(job_queue, max_workers, resource_monitor)
        
        self._executor: Optional[ProcessPoolExecutor] = None
        self._scheduler_thread: Optional[threading.Thread] = None
        self._adaptive_scaling = adaptive_scaling
        self._scaling_interval = scaling_interval
        self._current_worker_count = 0
        
        # For job serialization/deserialization
        # Note: In a real implementation, you'd need more sophisticated
        # serialization for functions and complex objects
        self._job_cache: Dict[str, Dict[str, Any]] = {}
    
    def start(self) -> bool:
        """
        Start the process execution engine.
        
        Returns:
            True if the engine was started successfully
        """
        with self._lock:
            if self._running:
                return True
            
            try:
                self._running = True
                
                # Create process pool
                self._executor = ProcessPoolExecutor(
                    max_workers=self.max_workers
                )
                
                # Start resource monitor if available
                if self.resource_monitor:
                    self.resource_monitor.start()
                
                # Start scheduler thread
                self._scheduler_thread = threading.Thread(
                    target=self._scheduler_loop,
                    daemon=True,
                    name="BatchProcessSchedulerThread"
                )
                self._scheduler_thread.start()
                
                logger.info(f"Started process execution engine with {self.max_workers} workers")
                return True
            
            except Exception as e:
                logger.error(f"Error starting process execution engine: {e}")
                self._running = False
                return False
    
    def stop(self) -> bool:
        """
        Stop the process execution engine.
        
        Returns:
            True if the engine was stopped successfully
        """
        with self._lock:
            if not self._running:
                return True
            
            try:
                self._running = False
                
                # Stop resource monitor if available
                if self.resource_monitor:
                    self.resource_monitor.stop()
                
                # Wait for scheduler thread to finish
                if self._scheduler_thread:
                    self._scheduler_thread.join(timeout=5.0)
                
                # Cancel and shutdown executor
                if self._executor:
                    self._executor.shutdown(wait=False, cancel_futures=True)
                    self._executor = None
                
                logger.info("Stopped process execution engine")
                return True
            
            except Exception as e:
                logger.error(f"Error stopping process execution engine: {e}")
                return False
    
    def submit_job(self, job: Job) -> bool:
        """
        Submit a job for execution.
        
        Args:
            job: Job to submit
            
        Returns:
            True if the job was submitted successfully
        """
        if not self._running or not self._executor:
            return False
        
        try:
            # Add the job to the queue
            success = self.job_queue.add_job(job)
            
            # Cache the job for process executor
            # Note: This assumes the job function is defined in the main module
            # or is otherwise importable in the worker processes
            # In a real implementation, you'd need to ensure the function
            # is serializable or use a different approach
            with self._lock:
                self._job_cache[job.job_id] = {
                    "name": job.name,
                    "args": job.args,
                    "kwargs": job.kwargs,
                    "job_id": job.job_id
                }
            
            return success
        
        except Exception as e:
            logger.error(f"Error submitting job {job.job_id}: {e}")
            return False
    
    def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a running job.
        
        Args:
            job_id: ID of the job to cancel
            
        Returns:
            True if the job was canceled successfully
        """
        with self._lock:
            if job_id in self._futures:
                future, job = self._futures[job_id]
                future.cancel()
                job.mark_canceled()
                del self._futures[job_id]
                
                # Remove from job cache
                if job_id in self._job_cache:
                    del self._job_cache[job_id]
                
                return True
            
            # If the job is in the queue but not running
            result = self.job_queue.cancel_job(job_id)
            
            # Remove from job cache
            if job_id in self._job_cache:
                del self._job_cache[job_id]
            
            return result
    
    def pause_job(self, job_id: str) -> bool:
        """
        Pause a running job.
        
        Args:
            job_id: ID of the job to pause
            
        Returns:
            True if the job was paused successfully
        """
        # Note: True pause/resume is not possible with ProcessPoolExecutor
        # This implementation only marks the job as paused
        with self._lock:
            if job_id in self._futures:
                # We can't truly pause a process, so we'll just mark it
                # and handle it in the job logic
                _, job = self._futures[job_id]
                job.mark_paused()
                return True
            
            # If the job is in the queue but not running
            return self.job_queue.pause_job(job_id)
    
    def resume_job(self, job_id: str) -> bool:
        """
        Resume a paused job.
        
        Args:
            job_id: ID of the job to resume
            
        Returns:
            True if the job was resumed successfully
        """
        # Since we can't truly pause jobs in processes, resume just
        # resubmits the job to the queue if it's paused
        with self._lock:
            job = self.job_queue.get_job(job_id)
            if not job or job.status != JobStatus.PAUSED:
                return False
            
            return self.job_queue.resume_job(job_id)
    
    def get_active_jobs(self) -> List[Job]:
        """
        Get a list of currently active jobs.
        
        Returns:
            List of active jobs
        """
        with self._lock:
            return [job for _, job in self._futures.values()]
    
    def _scheduler_loop(self) -> None:
        """
        Main scheduler loop that processes jobs from the queue.
        """
        logger.debug("Starting process scheduler loop")
        
        while self._running:
            try:
                # Adaptive scaling if enabled and resource monitor available
                if (self._adaptive_scaling and 
                    self.resource_monitor and 
                    self._executor):
                    self._adjust_worker_count()
                
                # Get next job from the queue
                job = self.job_queue.get_next_job(timeout=1.0)
                if not job or not self._running:
                    continue
                
                # Execute the job
                if self._executor:
                    # Get job from cache
                    with self._lock:
                        job_data = self._job_cache.get(job.job_id)
                    
                    if not job_data:
                        logger.error(f"Job data not found in cache for job {job.job_id}")
                        job.mark_failed(Exception("Job data not found in cache"))
                        self.job_queue.update_job(job)
                        continue
                    
                    # Create a process-safe job representation
                    # In a real implementation, you'd need more sophisticated
                    # serialization for the function and complex arguments
                    # Here, we assume the function is available in worker processes
                    future = self._executor.submit(
                        _process_job_wrapper,
                        job.func.__name__,  # Function name to lookup in worker
                        job_data["args"],
                        job_data["kwargs"],
                        job_data["job_id"]
                    )
                    
                    # Store future and job
                    with self._lock:
                        self._futures[job.job_id] = (future, job)
                    
                    # Add callback to handle job completion
                    future.add_done_callback(
                        lambda f, job_id=job.job_id: self._handle_job_completion(f, job_id)
                    )
                    
                    logger.debug(f"Scheduled job {job.job_id} for process execution")
            
            except Exception as e:
                logger.error(f"Error in process scheduler loop: {e}")
                time.sleep(1.0)
        
        logger.debug("Process scheduler loop stopped")
    
    def _handle_job_completion(self, future: Future, job_id: str) -> None:
        """
        Handle the completion of a job.
        
        Args:
            future: Future object for the job
            job_id: ID of the completed job
        """
        with self._lock:
            if job_id not in self._futures:
                return
            
            _, job = self._futures[job_id]
            del self._futures[job_id]
            
            try:
                # Get the result
                result = future.result()
                
                # Mark job as completed
                job.mark_completed(result)
                self.job_queue.update_job(job)
                
                logger.debug(f"Job {job_id} completed successfully")
            
            except Exception as e:
                logger.error(f"Error in job {job_id}: {e}")
                job.mark_failed(e)
                self.job_queue.update_job(job)
                
                # If job can be retried, requeue it
                if job.can_retry():
                    logger.info(f"Retrying job {job_id} (attempt {job.retries + 1}/{job.max_retries})")
                    self.job_queue.retry_job(job_id)
            
            # Remove from job cache
            if job_id in self._job_cache:
                del self._job_cache[job_id]
    
    def _adjust_worker_count(self) -> None:
        """
        Adjust the number of workers based on resource usage.
        """
        if not self.resource_monitor or not self._executor:
            return
        
        try:
            # Get resource usage
            usage = self.resource_monitor.get_resource_usage()
            
            # Get current worker count from executor
            workers = getattr(self._executor, "_max_workers", self.max_workers)
            
            # Check if resources are overloaded
            if usage["cpu_overloaded"] or usage["memory_overloaded"]:
                # Reduce workers by 25% but keep at least 1
                new_workers = max(1, int(workers * 0.75))
                if new_workers < workers:
                    logger.info(f"Resources overloaded, reducing workers from {workers} to {new_workers}")
                    # Create a new executor with fewer workers
                    new_executor = ProcessPoolExecutor(
                        max_workers=new_workers
                    )
                    
                    # Replace the old executor
                    old_executor = self._executor
                    self._executor = new_executor
                    
                    # Shutdown the old executor gracefully
                    old_executor.shutdown(wait=False, cancel_futures=False)
            
            # Check if resources are underutilized
            elif (not usage["cpu_overloaded"] and 
                  not usage["memory_overloaded"] and
                  workers < self.max_workers and
                  self.resource_monitor.can_add_workers()):
                
                # Increase workers by 25% but don't exceed max_workers
                new_workers = min(self.max_workers, int(workers * 1.25) + 1)
                if new_workers > workers:
                    logger.info(f"Resources underutilized, increasing workers from {workers} to {new_workers}")
                    # Create a new executor with more workers
                    new_executor = ProcessPoolExecutor(
                        max_workers=new_workers
                    )
                    
                    # Replace the old executor
                    old_executor = self._executor
                    self._executor = new_executor
                    
                    # Shutdown the old executor gracefully
                    old_executor.shutdown(wait=False, cancel_futures=False)
        
        except Exception as e:
            logger.error(f"Error adjusting worker count: {e}")


def _process_job_wrapper(func_name, args, kwargs, job_id):
    """
    Wrapper function for executing jobs in worker processes.
    
    Args:
        func_name: Name of the function to execute
        args: Positional arguments for the function
        kwargs: Keyword arguments for the function
        job_id: ID of the job
        
    Returns:
        Result of the function execution
    """
    try:
        # In a real implementation, you'd need a registry of functions
        # available to worker processes or a different approach for
        # serializing and executing functions
        # This is a simplified example
        import sys
        import importlib
        
        # Look for the function in loaded modules
        for module_name, module in sys.modules.items():
            if hasattr(module, func_name):
                func = getattr(module, func_name)
                if callable(func):
                    return func(*args, **kwargs)
        
        # If not found, try importing the function from the main module
        if 'ai_document_organizer_v2' in sys.modules:
            main_module = sys.modules['ai_document_organizer_v2']
            if hasattr(main_module, func_name):
                func = getattr(main_module, func_name)
                if callable(func):
                    return func(*args, **kwargs)
        
        raise ValueError(f"Function {func_name} not found in worker process")
    
    except Exception as e:
        logger.error(f"Error in worker process for job {job_id}: {e}")
        raise