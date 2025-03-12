"""
Job Scheduler for the Batch Processing Plugin.

Provides job scheduling with advanced features like:
- Dependency resolution
- Priority-based scheduling
- Resource-aware scheduling
- Deadline-based scheduling
"""

import time
import logging
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set, Callable, Tuple, Union

from ..models.job import Job, JobStatus, JobPriority
from ..jobs.job_queue import JobQueue
from ..core.execution_engines import ExecutionEngine, ResourceMonitor

logger = logging.getLogger(__name__)

class SchedulePolicy:
    """
    Base class for job scheduling policies.
    
    A policy determines when and how jobs are scheduled for execution.
    """
    
    def __init__(self):
        """Initialize the scheduling policy."""
        pass
    
    def schedule(self, job_queue: JobQueue, jobs: List[Job]) -> List[Job]:
        """
        Apply scheduling policy to a list of jobs.
        
        Args:
            job_queue: The job queue
            jobs: List of jobs to schedule
            
        Returns:
            List of jobs in scheduled order
        """
        raise NotImplementedError("Subclasses must implement schedule()")


class PrioritySchedulePolicy(SchedulePolicy):
    """
    Priority-based scheduling policy.
    
    Jobs with higher priority are scheduled before jobs with lower priority.
    """
    
    def schedule(self, job_queue: JobQueue, jobs: List[Job]) -> List[Job]:
        """
        Apply priority-based scheduling to a list of jobs.
        
        Args:
            job_queue: The job queue
            jobs: List of jobs to schedule
            
        Returns:
            List of jobs in priority order
        """
        # Sort jobs by priority (highest first)
        return sorted(jobs, key=lambda job: job.priority.value, reverse=True)


class DeadlineSchedulePolicy(SchedulePolicy):
    """
    Deadline-based scheduling policy.
    
    Jobs with earlier deadlines are scheduled before jobs with later deadlines.
    """
    
    def schedule(self, job_queue: JobQueue, jobs: List[Job]) -> List[Job]:
        """
        Apply deadline-based scheduling to a list of jobs.
        
        Args:
            job_queue: The job queue
            jobs: List of jobs to schedule
            
        Returns:
            List of jobs in deadline order
        """
        # Sort jobs by deadline (earliest first)
        # We check the metadata for a deadline field
        def get_deadline(job: Job) -> float:
            deadline = job.metadata.get("deadline")
            if deadline:
                if isinstance(deadline, datetime):
                    return deadline.timestamp()
                elif isinstance(deadline, (int, float)):
                    return float(deadline)
            return float('inf')  # No deadline or invalid deadline format
        
        return sorted(jobs, key=get_deadline)


class FairShareSchedulePolicy(SchedulePolicy):
    """
    Fair share scheduling policy.
    
    Ensures all users or groups get a fair share of resources based on
    their allocated shares or quotas.
    """
    
    def __init__(self, shares: Optional[Dict[str, int]] = None):
        """
        Initialize fair share scheduling policy.
        
        Args:
            shares: Optional dictionary mapping user or group IDs to share values
        """
        super().__init__()
        self.shares = shares or {}
        self.usage: Dict[str, float] = {}
    
    def record_usage(self, user_id: str, cpu_time: float) -> None:
        """
        Record resource usage for a user or group.
        
        Args:
            user_id: User or group ID
            cpu_time: CPU time used
        """
        self.usage[user_id] = self.usage.get(user_id, 0.0) + cpu_time
    
    def schedule(self, job_queue: JobQueue, jobs: List[Job]) -> List[Job]:
        """
        Apply fair share scheduling to a list of jobs.
        
        Args:
            job_queue: The job queue
            jobs: List of jobs to schedule
            
        Returns:
            List of jobs in fair share order
        """
        def get_priority(job: Job) -> float:
            user_id = job.metadata.get("user_id", "default")
            share = self.shares.get(user_id, 1)
            usage = self.usage.get(user_id, 0.0)
            
            # Higher priority for users with higher shares and lower usage
            if share == 0:
                return 0  # No share, lowest priority
            else:
                return job.priority.value * (share / (usage + 1.0))
        
        return sorted(jobs, key=get_priority, reverse=True)


class ResourceAwareSchedulePolicy(SchedulePolicy):
    """
    Resource-aware scheduling policy.
    
    Schedules jobs based on their resource requirements and available resources.
    """
    
    def __init__(self, resource_monitor: ResourceMonitor):
        """
        Initialize resource-aware scheduling policy.
        
        Args:
            resource_monitor: Resource monitor for checking available resources
        """
        super().__init__()
        self.resource_monitor = resource_monitor
    
    def schedule(self, job_queue: JobQueue, jobs: List[Job]) -> List[Job]:
        """
        Apply resource-aware scheduling to a list of jobs.
        
        Args:
            job_queue: The job queue
            jobs: List of jobs to schedule
            
        Returns:
            List of jobs ordered by resource fitness
        """
        # Get current resource usage
        usage = self.resource_monitor.get_resource_usage()
        
        # Filter jobs that can run with current resources
        runnable_jobs = []
        deferred_jobs = []
        
        for job in jobs:
            # Check job resource requirements
            cpu_req = job.metadata.get("cpu_requirement", 0.1)  # Default: 10% CPU
            memory_req = job.metadata.get("memory_requirement", 0.1)  # Default: 10% memory
            
            # Check if resources are available
            if (usage["cpu_average"] + cpu_req <= self.resource_monitor.cpu_limit and
                usage["memory_average"] + memory_req <= self.resource_monitor.memory_limit):
                runnable_jobs.append(job)
            else:
                deferred_jobs.append(job)
        
        # Sort runnable jobs by priority
        runnable_jobs.sort(key=lambda job: job.priority.value, reverse=True)
        
        # Sort deferred jobs by priority
        deferred_jobs.sort(key=lambda job: job.priority.value, reverse=True)
        
        # Return runnable jobs first, then deferred jobs
        return runnable_jobs + deferred_jobs


class JobScheduler:
    """
    Job scheduler for managing and scheduling batch processing jobs.
    """
    
    def __init__(self, job_queue: JobQueue, execution_engine: ExecutionEngine,
                 scheduling_policy: Optional[SchedulePolicy] = None,
                 scheduling_interval: float = 1.0):
        """
        Initialize the job scheduler.
        
        Args:
            job_queue: Queue for managing jobs
            execution_engine: Engine for executing jobs
            scheduling_policy: Optional policy for job scheduling
            scheduling_interval: Interval in seconds for scheduling loop
        """
        self.job_queue = job_queue
        self.execution_engine = execution_engine
        self.scheduling_policy = scheduling_policy or PrioritySchedulePolicy()
        self.scheduling_interval = scheduling_interval
        
        self._running = False
        self._scheduler_thread: Optional[threading.Thread] = None
        self._lock = threading.RLock()
        
        # Job statistics
        self.stats = {
            "total_jobs": 0,
            "completed_jobs": 0,
            "failed_jobs": 0,
            "canceled_jobs": 0,
            "avg_execution_time": 0.0,
            "max_execution_time": 0.0,
            "min_execution_time": float('inf'),
            "avg_queue_time": 0.0
        }
        
        # Set of jobs that have been processed for statistics
        self._processed_stats = set()
    
    def start(self) -> bool:
        """
        Start the job scheduler.
        
        Returns:
            True if the scheduler was started successfully
        """
        with self._lock:
            if self._running:
                return True
            
            try:
                self._running = True
                
                # Start execution engine
                if not self.execution_engine.start():
                    logger.error("Failed to start execution engine")
                    self._running = False
                    return False
                
                # Start scheduler thread
                self._scheduler_thread = threading.Thread(
                    target=self._scheduling_loop,
                    daemon=True,
                    name="JobSchedulerThread"
                )
                self._scheduler_thread.start()
                
                logger.info("Started job scheduler")
                return True
            
            except Exception as e:
                logger.error(f"Error starting job scheduler: {e}")
                self._running = False
                return False
    
    def stop(self) -> bool:
        """
        Stop the job scheduler.
        
        Returns:
            True if the scheduler was stopped successfully
        """
        with self._lock:
            if not self._running:
                return True
            
            try:
                self._running = False
                
                # Stop execution engine
                self.execution_engine.stop()
                
                # Wait for scheduler thread to finish
                if self._scheduler_thread:
                    self._scheduler_thread.join(timeout=5.0)
                
                logger.info("Stopped job scheduler")
                return True
            
            except Exception as e:
                logger.error(f"Error stopping job scheduler: {e}")
                return False
    
    def submit_job(self, job: Job) -> bool:
        """
        Submit a job for scheduling.
        
        Args:
            job: Job to submit
            
        Returns:
            True if the job was submitted successfully
        """
        try:
            # Record job in statistics
            with self._lock:
                self.stats["total_jobs"] += 1
            
            # Submit to execution engine
            # The engine will add the job to the queue
            return self.execution_engine.submit_job(job)
        
        except Exception as e:
            logger.error(f"Error submitting job {job.job_id}: {e}")
            return False
    
    def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a job.
        
        Args:
            job_id: ID of the job to cancel
            
        Returns:
            True if the job was canceled successfully
        """
        try:
            # Try to cancel in execution engine first
            if self.execution_engine.cancel_job(job_id):
                with self._lock:
                    self.stats["canceled_jobs"] += 1
                return True
            
            # If not running in engine, try to cancel in queue
            return self.job_queue.cancel_job(job_id)
        
        except Exception as e:
            logger.error(f"Error canceling job {job_id}: {e}")
            return False
    
    def pause_job(self, job_id: str) -> bool:
        """
        Pause a job.
        
        Args:
            job_id: ID of the job to pause
            
        Returns:
            True if the job was paused successfully
        """
        try:
            # Try to pause in execution engine first
            if self.execution_engine.pause_job(job_id):
                return True
            
            # If not running in engine, try to pause in queue
            return self.job_queue.pause_job(job_id)
        
        except Exception as e:
            logger.error(f"Error pausing job {job_id}: {e}")
            return False
    
    def resume_job(self, job_id: str) -> bool:
        """
        Resume a paused job.
        
        Args:
            job_id: ID of the job to resume
            
        Returns:
            True if the job was resumed successfully
        """
        try:
            # Try to resume in execution engine first
            if self.execution_engine.resume_job(job_id):
                return True
            
            # If not running in engine, try to resume in queue
            return self.job_queue.resume_job(job_id)
        
        except Exception as e:
            logger.error(f"Error resuming job {job_id}: {e}")
            return False
    
    def get_job(self, job_id: str) -> Optional[Job]:
        """
        Get a job by ID.
        
        Args:
            job_id: ID of the job to get
            
        Returns:
            The job or None if not found
        """
        return self.job_queue.get_job(job_id)
    
    def get_all_jobs(self) -> List[Job]:
        """
        Get all jobs.
        
        Returns:
            List of all jobs
        """
        return self.job_queue.get_all_jobs()
    
    def get_active_jobs(self) -> List[Job]:
        """
        Get a list of currently active jobs.
        
        Returns:
            List of active jobs
        """
        return self.execution_engine.get_active_jobs()
    
    def get_job_stats(self) -> Dict[str, Any]:
        """
        Get job statistics.
        
        Returns:
            Dictionary with job statistics
        """
        with self._lock:
            return dict(self.stats)
    
    def clear_jobs(self) -> bool:
        """
        Clear all jobs.
        
        Returns:
            True if all jobs were cleared successfully
        """
        try:
            # Cancel active jobs in execution engine
            active_jobs = self.execution_engine.get_active_jobs()
            for job in active_jobs:
                self.execution_engine.cancel_job(job.job_id)
            
            # Clear job queue
            self.job_queue.clear()
            
            return True
        
        except Exception as e:
            logger.error(f"Error clearing jobs: {e}")
            return False
    
    def set_scheduling_policy(self, policy: SchedulePolicy) -> None:
        """
        Set the scheduling policy.
        
        Args:
            policy: Scheduling policy to use
        """
        with self._lock:
            self.scheduling_policy = policy
            logger.info(f"Set scheduling policy to {policy.__class__.__name__}")
    
    def _scheduling_loop(self) -> None:
        """
        Main scheduling loop that applies the scheduling policy.
        """
        logger.debug("Starting job scheduling loop")
        
        while self._running:
            try:
                time.sleep(self.scheduling_interval)
                
                # Get pending jobs
                pending_jobs = self.job_queue.get_jobs_by_status(JobStatus.PENDING)
                
                if not pending_jobs:
                    continue
                
                # Apply scheduling policy
                scheduled_jobs = self.scheduling_policy.schedule(self.job_queue, pending_jobs)
                
                # Update job statistics
                for job in self.job_queue.get_jobs_by_status(JobStatus.COMPLETED):
                    if job.started_at and job.completed_at:
                        duration = job.completed_at - job.started_at
                        
                        with self._lock:
                            # Only update stats once per completed job
                            if job.job_id not in self._processed_stats:
                                self._processed_stats.add(job.job_id)
                                
                                self.stats["completed_jobs"] += 1
                                self.stats["avg_execution_time"] = (
                                    (self.stats["avg_execution_time"] * (self.stats["completed_jobs"] - 1) + duration) / 
                                    self.stats["completed_jobs"]
                                )
                                self.stats["max_execution_time"] = max(self.stats["max_execution_time"], duration)
                                self.stats["min_execution_time"] = min(self.stats["min_execution_time"], duration)
                
                # Add more sophisticated scheduling and resource management here
                
            except Exception as e:
                logger.error(f"Error in scheduling loop: {e}")
                time.sleep(1.0)
        
        logger.debug("Job scheduling loop stopped")