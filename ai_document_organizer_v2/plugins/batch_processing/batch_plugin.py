"""
Batch Processing Plugin for AI Document Organizer V2.

Provides batch processing capabilities for document processing tasks.
"""

import concurrent.futures
import logging
import threading
import time
import uuid
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from ai_document_organizer_v2.core.plugin_base import PluginBase
from .models.job import Job, JobQueue, JobStatus, JobPriority


logger = logging.getLogger(__name__)


class BatchProcessingPlugin(PluginBase):
    """
    Plugin for batch processing of document processing tasks.
    
    This plugin provides a job queue and scheduling system for asynchronously
    processing large numbers of documents in batches.
    """
    
    plugin_name = "batch_processing"
    plugin_version = "1.0.0"
    plugin_description = "Batch processing capabilities for document processing tasks"
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the batch processing plugin.
        
        Args:
            config: Optional configuration dictionary
        """
        super().__init__(config)
        
        # Configuration
        self.config = config or {}
        self.max_concurrent_jobs = self.config.get("max_concurrent_jobs", 5)
        self.max_queue_size = self.config.get("max_queue_size", 1000)
        self.default_timeout = self.config.get("default_timeout", 3600)  # 1 hour
        self.default_retries = self.config.get("default_retries", 3)
        self.default_retry_delay = self.config.get("default_retry_delay", 60)  # 1 minute
        self.monitor_interval = self.config.get("monitor_interval", 1.0)  # 1 second
        
        # Job management
        self.job_queue = JobQueue()
        self.active_jobs: Dict[str, Job] = {}
        self.completed_jobs: Dict[str, Job] = {}
        self.job_results: Dict[str, Any] = {}
        self.job_group_map: Dict[str, List[str]] = {}
        
        # Thread management
        self.executor = None
        self.monitor_thread = None
        self.running = False
        self.stop_event = threading.Event()
        self.lock = threading.RLock()
        
        # Scheduling and metrics
        self.scheduling_policy = "fairshare"  # Options: "fifo", "priority", "fairshare"
        self.job_metrics: Dict[str, Dict[str, Any]] = {}
        self.system_metrics: Dict[str, Any] = {
            "jobs_processed": 0,
            "jobs_succeeded": 0,
            "jobs_failed": 0,
            "jobs_canceled": 0,
            "total_processing_time": 0.0,
            "start_time": None,
            "uptime": 0.0,
        }
    
    def initialize(self) -> bool:
        """
        Initialize the plugin.
        
        Returns:
            True if initialization was successful, False otherwise
        """
        try:
            # Create thread pool executor
            self.executor = concurrent.futures.ThreadPoolExecutor(
                max_workers=self.max_concurrent_jobs,
                thread_name_prefix="batch_worker"
            )
            
            logger.info(f"Batch processing plugin initialized with max_concurrent_jobs={self.max_concurrent_jobs}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to initialize batch processing plugin: {e}")
            return False
    
    def shutdown(self) -> bool:
        """
        Shutdown the plugin.
        
        Returns:
            True if shutdown was successful, False otherwise
        """
        try:
            # Stop the plugin first
            if self.running:
                self.stop()
            
            # Shutdown the executor
            if self.executor:
                self.executor.shutdown(wait=True)
                self.executor = None
            
            logger.info("Batch processing plugin shutdown")
            return True
        
        except Exception as e:
            logger.error(f"Failed to shutdown batch processing plugin: {e}")
            return False
    
    def activate(self) -> bool:
        """
        Activate the plugin. This starts the job processor.
        
        Returns:
            True if activation was successful, False otherwise
        """
        try:
            if not self.running:
                self.start()
            return True
        
        except Exception as e:
            logger.error(f"Failed to activate batch processing plugin: {e}")
            return False
    
    def deactivate(self) -> bool:
        """
        Deactivate the plugin. This stops the job processor.
        
        Returns:
            True if deactivation was successful, False otherwise
        """
        try:
            if self.running:
                self.stop()
            return True
        
        except Exception as e:
            logger.error(f"Failed to deactivate batch processing plugin: {e}")
            return False
    
    def get_type(self) -> str:
        """
        Get the plugin type.
        
        Returns:
            Plugin type string
        """
        return "batch_processing"
    
    def get_capabilities(self) -> List[str]:
        """
        Get the plugin capabilities.
        
        Returns:
            List of capability strings
        """
        return [
            "batch_processing",
            "job_queue",
            "job_scheduling",
            "parallel_execution",
            "retry_mechanism",
            "progress_tracking",
            "resource_monitoring"
        ]
    
    def get_info(self) -> Dict[str, Any]:
        """
        Get information about the plugin.
        
        Returns:
            Dictionary with plugin information
        """
        with self.lock:
            queue_size = self.job_queue.size()
            active_jobs = len(self.active_jobs)
            completed_jobs = len(self.completed_jobs)
            
            return {
                "name": self.plugin_name,
                "version": self.plugin_version,
                "description": self.plugin_description,
                "status": "active" if self.running else "inactive",
                "max_concurrent_jobs": self.max_concurrent_jobs,
                "max_queue_size": self.max_queue_size,
                "queue_size": queue_size,
                "active_jobs": active_jobs,
                "completed_jobs": completed_jobs,
                "metrics": self.system_metrics,
                "scheduling_policy": self.scheduling_policy
            }
    
    def start(self) -> bool:
        """
        Start the job processor.
        
        Returns:
            True if the processor was started, False otherwise
        """
        if self.running:
            logger.warning("Batch processor is already running")
            return True
        
        try:
            self.running = True
            self.stop_event.clear()
            
            # Start monitor thread
            self.monitor_thread = threading.Thread(
                target=self._monitor_jobs,
                name="batch_monitor"
            )
            self.monitor_thread.daemon = True
            self.monitor_thread.start()
            
            self.system_metrics["start_time"] = time.time()
            logger.info("Batch processor started")
            return True
        
        except Exception as e:
            self.running = False
            logger.error(f"Failed to start batch processor: {e}")
            return False
    
    def stop(self) -> bool:
        """
        Stop the job processor.
        
        Returns:
            True if the processor was stopped, False otherwise
        """
        if not self.running:
            logger.warning("Batch processor is not running")
            return True
        
        try:
            self.running = False
            self.stop_event.set()
            
            # Wait for monitor thread to stop
            if self.monitor_thread and self.monitor_thread.is_alive():
                self.monitor_thread.join(timeout=10.0)
            
            # Cancel all active jobs
            with self.lock:
                for job_id, job in list(self.active_jobs.items()):
                    self._cancel_job(job)
            
            logger.info("Batch processor stopped")
            return True
        
        except Exception as e:
            logger.error(f"Failed to stop batch processor: {e}")
            return False
    
    def submit_job(self, 
                  func: Callable, 
                  *args, 
                  name: Optional[str] = None,
                  priority: Union[str, JobPriority] = JobPriority.NORMAL,
                  tags: Optional[List[str]] = None,
                  metadata: Optional[Dict[str, Any]] = None,
                  timeout: Optional[int] = None,
                  retries: int = None,
                  retry_delay: int = None,
                  group_id: Optional[str] = None) -> str:
        """
        Submit a job for processing.
        
        Args:
            func: Function to execute
            *args: Positional arguments to pass to the function
            name: Optional job name
            priority: Job priority (high, normal, low)
            tags: Optional list of tags
            metadata: Optional metadata dictionary
            timeout: Optional timeout in seconds
            retries: Number of retries on failure (None for default)
            retry_delay: Delay in seconds between retries (None for default)
            group_id: Optional group ID for batch operations
            
        Returns:
            Job ID
        """
        with self.lock:
            if self.job_queue.size() >= self.max_queue_size:
                raise ValueError(f"Job queue full (max size: {self.max_queue_size})")
            
            # Prepare job
            job = Job(
                func=func,
                args=list(args),
                kwargs={},
                name=name,
                priority=priority,
                tags=tags,
                metadata=metadata,
                timeout=timeout or self.default_timeout,
                retries=retries if retries is not None else self.default_retries,
                retry_delay=retry_delay if retry_delay is not None else self.default_retry_delay,
                group_id=group_id
            )
            
            # Add to job group if specified
            if group_id:
                if group_id not in self.job_group_map:
                    self.job_group_map[group_id] = []
                self.job_group_map[group_id].append(job.job_id)
            
            # Add to queue
            self.job_queue.put(job)
            
            logger.debug(f"Job {job.job_id} ({job.name}) submitted with priority {job.priority.value}")
            return job.job_id
    
    def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a job.
        
        Args:
            job_id: ID of the job to cancel
            
        Returns:
            True if the job was canceled, False otherwise
        """
        with self.lock:
            # Check if job is in queue
            if self.job_queue.contains(job_id):
                job = self.job_queue.remove(job_id)
                
                if job:
                    job.status = JobStatus.CANCELLED
                    self.completed_jobs[job_id] = job
                    self.system_metrics["jobs_canceled"] += 1
                    logger.info(f"Job {job_id} canceled from queue")
                    return True
            
            # Check if job is active
            if job_id in self.active_jobs:
                job = self.active_jobs[job_id]
                return self._cancel_job(job)
            
            # Job not found
            logger.warning(f"Job {job_id} not found for cancellation")
            return False
    
    def pause_job(self, job_id: str) -> bool:
        """
        Pause a job.
        
        Args:
            job_id: ID of the job to pause
            
        Returns:
            True if the job was paused, False otherwise
        """
        with self.lock:
            # Can only pause active jobs
            if job_id in self.active_jobs:
                job = self.active_jobs[job_id]
                job.status = JobStatus.PAUSED
                logger.info(f"Job {job_id} paused")
                return True
            
            logger.warning(f"Job {job_id} not active, cannot pause")
            return False
    
    def resume_job(self, job_id: str) -> bool:
        """
        Resume a paused job.
        
        Args:
            job_id: ID of the job to resume
            
        Returns:
            True if the job was resumed, False otherwise
        """
        with self.lock:
            # Can only resume paused jobs
            if job_id in self.active_jobs:
                job = self.active_jobs[job_id]
                
                if job.status == JobStatus.PAUSED:
                    job.status = JobStatus.RUNNING
                    logger.info(f"Job {job_id} resumed")
                    return True
                
                logger.warning(f"Job {job_id} is not paused, cannot resume")
                return False
            
            logger.warning(f"Job {job_id} not active, cannot resume")
            return False
    
    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a job.
        
        Args:
            job_id: ID of the job to get
            
        Returns:
            Dictionary with job information or None if the job is not found
        """
        with self.lock:
            # Check queue
            job = self.job_queue.get_job(job_id)
            if job:
                return job.to_dict()
            
            # Check active jobs
            if job_id in self.active_jobs:
                return self.active_jobs[job_id].to_dict()
            
            # Check completed jobs
            if job_id in self.completed_jobs:
                return self.completed_jobs[job_id].to_dict()
            
            return None
    
    def get_all_jobs(self) -> List[Dict[str, Any]]:
        """
        Get information about all jobs.
        
        Returns:
            List of dictionaries with job information
        """
        with self.lock:
            jobs = []
            
            # Get queued jobs
            for job in self.job_queue.get_all_jobs():
                jobs.append(job.to_dict())
            
            # Get active jobs
            for job in self.active_jobs.values():
                jobs.append(job.to_dict())
            
            # Get completed jobs
            for job in self.completed_jobs.values():
                jobs.append(job.to_dict())
            
            return jobs
    
    def get_job_status(self, job_id: str) -> Optional[str]:
        """
        Get the status of a job.
        
        Args:
            job_id: ID of the job to get status for
            
        Returns:
            Job status string or None if the job is not found
        """
        job_info = self.get_job(job_id)
        if job_info:
            return job_info["status"]
        return None
    
    def get_job_result(self, job_id: str) -> Any:
        """
        Get the result of a completed job.
        
        Args:
            job_id: ID of the job to get result for
            
        Returns:
            Job result or None if the job is not completed or not found
        """
        with self.lock:
            if job_id in self.job_results:
                return self.job_results[job_id]
            
            if job_id in self.completed_jobs:
                return self.completed_jobs[job_id].result
            
            return None
    
    def get_job_error(self, job_id: str) -> Optional[str]:
        """
        Get the error of a failed job.
        
        Args:
            job_id: ID of the job to get error for
            
        Returns:
            Job error string or None if the job did not fail or is not found
        """
        with self.lock:
            if job_id in self.completed_jobs:
                job = self.completed_jobs[job_id]
                return job.error
            
            return None
    
    def get_active_jobs(self) -> List[Dict[str, Any]]:
        """
        Get information about all active jobs.
        
        Returns:
            List of dictionaries with job information
        """
        with self.lock:
            return [job.to_dict() for job in self.active_jobs.values()]
    
    def get_job_stats(self) -> Dict[str, Any]:
        """
        Get statistics about job processing.
        
        Returns:
            Dictionary with job statistics
        """
        with self.lock:
            stats = dict(self.system_metrics)
            
            # Update uptime
            if stats["start_time"]:
                stats["uptime"] = time.time() - stats["start_time"]
            
            return stats
    
    def clear_jobs(self, status: Optional[str] = None) -> int:
        """
        Clear completed jobs from history.
        
        Args:
            status: Optional status filter (e.g., 'completed', 'failed', 'cancelled')
            
        Returns:
            Number of jobs cleared
        """
        with self.lock:
            if status:
                # Convert string status to enum if needed
                try:
                    job_status = JobStatus(status)
                except ValueError:
                    logger.warning(f"Invalid job status: {status}")
                    return 0
                
                # Clear jobs with matching status
                jobs_to_remove = [job_id for job_id, job in self.completed_jobs.items()
                                 if job.status == job_status]
                
                for job_id in jobs_to_remove:
                    del self.completed_jobs[job_id]
                    if job_id in self.job_results:
                        del self.job_results[job_id]
                
                return len(jobs_to_remove)
            
            else:
                # Clear all completed jobs
                count = len(self.completed_jobs)
                self.completed_jobs.clear()
                self.job_results.clear()
                return count
    
    def set_scheduling_policy(self, policy: str) -> bool:
        """
        Set the job scheduling policy.
        
        Args:
            policy: Scheduling policy ('fifo', 'priority', 'fairshare')
            
        Returns:
            True if the policy was set, False otherwise
        """
        valid_policies = ["fifo", "priority", "fairshare"]
        if policy not in valid_policies:
            logger.error(f"Invalid scheduling policy: {policy} (valid: {valid_policies})")
            return False
        
        with self.lock:
            self.scheduling_policy = policy
            logger.info(f"Scheduling policy set to: {policy}")
            return True
    
    def wait_for_job(self, job_id: str, timeout: Optional[float] = None) -> bool:
        """
        Wait for a job to complete.
        
        Args:
            job_id: ID of the job to wait for
            timeout: Optional timeout in seconds
            
        Returns:
            True if the job completed successfully, False otherwise
        """
        start_time = time.time()
        while True:
            job_info = self.get_job(job_id)
            
            if not job_info:
                logger.warning(f"Job {job_id} not found")
                return False
            
            status = job_info["status"]
            if status == JobStatus.COMPLETED.value:
                return True
            
            if status in [JobStatus.FAILED.value, JobStatus.CANCELLED.value]:
                return False
            
            # Check timeout
            if timeout and (time.time() - start_time) > timeout:
                logger.warning(f"Timeout waiting for job {job_id}")
                return False
            
            # Sleep before checking again
            time.sleep(0.1)
    
    def wait_for_jobs(self, job_ids: List[str], timeout: Optional[float] = None) -> bool:
        """
        Wait for multiple jobs to complete.
        
        Args:
            job_ids: List of job IDs to wait for
            timeout: Optional timeout in seconds
            
        Returns:
            True if all jobs completed successfully, False otherwise
        """
        if not job_ids:
            return True
        
        start_time = time.time()
        pending_jobs = set(job_ids)
        
        while pending_jobs:
            # Check each pending job
            for job_id in list(pending_jobs):
                job_info = self.get_job(job_id)
                
                if not job_info:
                    logger.warning(f"Job {job_id} not found")
                    pending_jobs.remove(job_id)
                    continue
                
                status = job_info["status"]
                if status in [JobStatus.COMPLETED.value, JobStatus.FAILED.value, JobStatus.CANCELLED.value]:
                    pending_jobs.remove(job_id)
            
            # Check timeout
            if timeout and (time.time() - start_time) > timeout:
                logger.warning(f"Timeout waiting for jobs {job_ids}")
                return False
            
            # If there are still pending jobs, sleep before checking again
            if pending_jobs:
                time.sleep(0.1)
        
        # Check if all jobs completed successfully
        for job_id in job_ids:
            status = self.get_job_status(job_id)
            if status != JobStatus.COMPLETED.value:
                return False
        
        return True
    
    def create_job_group(self, name: Optional[str] = None) -> str:
        """
        Create a job group for batch operations.
        
        Args:
            name: Optional group name
            
        Returns:
            Group ID
        """
        group_id = str(uuid.uuid4())
        self.job_group_map[group_id] = []
        return group_id
    
    def _monitor_jobs(self) -> None:
        """
        Monitor and process jobs in the queue.
        """
        logger.info("Job monitor thread started")
        
        while not self.stop_event.is_set():
            try:
                # Process jobs in the queue
                self._process_jobs()
                
                # Update metrics
                self._update_metrics()
                
                # Sleep for a short interval
                time.sleep(self.monitor_interval)
            
            except Exception as e:
                logger.error(f"Error in job monitor: {e}")
                time.sleep(1.0)  # Sleep on error to avoid tight loop
        
        logger.info("Job monitor thread stopped")
    
    def _process_jobs(self) -> None:
        """
        Process jobs in the queue according to the scheduling policy.
        """
        # Skip if there are no jobs in the queue
        if self.job_queue.is_empty():
            return
        
        # Check if we can process more jobs
        with self.lock:
            if len(self.active_jobs) >= self.max_concurrent_jobs:
                return
            
            # Get the next job from the queue
            job = self.job_queue.get()
            if not job:
                return
            
            # Mark job as running
            job.status = JobStatus.RUNNING
            job.start_time = time.time()
            self.active_jobs[job.job_id] = job
            
            # Submit job to executor
            self.executor.submit(self._execute_job, job)
    
    def _execute_job(self, job: Job) -> None:
        """
        Execute a job and handle the result.
        
        Args:
            job: Job to execute
        """
        logger.debug(f"Executing job {job.job_id} ({job.name})")
        
        start_time = time.time()
        error = None
        result = None
        
        try:
            # Check if job was cancelled
            if job.status != JobStatus.RUNNING:
                logger.debug(f"Job {job.job_id} not running, skipping execution")
                return
            
            # Execute the job function
            result = job.func(*job.args, **job.kwargs)
            
            # Store result
            with self.lock:
                job.result = result
                self.job_results[job.job_id] = result
                job.status = JobStatus.COMPLETED
                job.end_time = time.time()
                
                # Move from active to completed
                if job.job_id in self.active_jobs:
                    del self.active_jobs[job.job_id]
                self.completed_jobs[job.job_id] = job
                
                # Update metrics
                self.system_metrics["jobs_processed"] += 1
                self.system_metrics["jobs_succeeded"] += 1
                self.system_metrics["total_processing_time"] += (job.end_time - job.start_time)
            
            logger.debug(f"Job {job.job_id} ({job.name}) completed successfully")
        
        except Exception as e:
            error = str(e)
            logger.error(f"Job {job.job_id} ({job.name}) failed: {error}")
            
            with self.lock:
                # Check if job should be retried
                if job.retry_count < job.retries:
                    job.retry_count += 1
                    job.status = JobStatus.QUEUED
                    job.error = error
                    job.queue_time = time.time()
                    
                    # Re-queue the job after delay
                    threading.Timer(job.retry_delay, self._requeue_job, args=[job]).start()
                    
                    logger.info(f"Job {job.job_id} will be retried ({job.retry_count}/{job.retries})")
                    
                    # Remove from active jobs
                    if job.job_id in self.active_jobs:
                        del self.active_jobs[job.job_id]
                
                else:
                    # Mark as failed
                    job.status = JobStatus.FAILED
                    job.error = error
                    job.end_time = time.time()
                    
                    # Move from active to completed
                    if job.job_id in self.active_jobs:
                        del self.active_jobs[job.job_id]
                    self.completed_jobs[job.job_id] = job
                    
                    # Update metrics
                    self.system_metrics["jobs_processed"] += 1
                    self.system_metrics["jobs_failed"] += 1
                    self.system_metrics["total_processing_time"] += (job.end_time - job.start_time)
                    
                    logger.info(f"Job {job.job_id} ({job.name}) failed after {job.retry_count} retries")
    
    def _requeue_job(self, job: Job) -> None:
        """
        Re-queue a job for retry.
        
        Args:
            job: Job to re-queue
        """
        with self.lock:
            # Put job back in the queue
            self.job_queue.put(job)
            logger.debug(f"Job {job.job_id} re-queued for retry {job.retry_count}/{job.retries}")
    
    def _cancel_job(self, job: Job) -> bool:
        """
        Cancel an active job.
        
        Args:
            job: Job to cancel
            
        Returns:
            True if the job was canceled, False otherwise
        """
        with self.lock:
            if job.job_id in self.active_jobs:
                # Mark job as cancelled
                job.status = JobStatus.CANCELLED
                job.end_time = time.time()
                
                # Move from active to completed
                del self.active_jobs[job.job_id]
                self.completed_jobs[job.job_id] = job
                
                # Update metrics
                self.system_metrics["jobs_processed"] += 1
                self.system_metrics["jobs_canceled"] += 1
                
                logger.info(f"Job {job.job_id} canceled")
                return True
            
            return False
    
    def _update_metrics(self) -> None:
        """
        Update system metrics.
        """
        if self.system_metrics["start_time"]:
            self.system_metrics["uptime"] = time.time() - self.system_metrics["start_time"]
        
        # Additional metrics could be added here