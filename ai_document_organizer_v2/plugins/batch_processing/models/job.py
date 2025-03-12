"""
Job model for batch processing plugin.
"""

import enum
import time
import uuid
from typing import Any, Callable, Dict, List, Optional, Union


class JobStatus(enum.Enum):
    """Job status enum."""
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class JobPriority(enum.Enum):
    """Job priority enum."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class Job:
    """
    Job model for batch processing.
    
    This class represents a job that can be executed asynchronously.
    """
    
    def __init__(self, 
                func: Callable, 
                args: Optional[List[Any]] = None, 
                kwargs: Optional[Dict[str, Any]] = None,
                name: Optional[str] = None,
                priority: Union[str, JobPriority] = JobPriority.NORMAL,
                tags: Optional[List[str]] = None,
                metadata: Optional[Dict[str, Any]] = None,
                timeout: int = 3600,
                retries: int = 3,
                retry_delay: int = 60,
                group_id: Optional[str] = None):
        """
        Initialize a job.
        
        Args:
            func: Function to execute
            args: Positional arguments to pass to the function
            kwargs: Keyword arguments to pass to the function
            name: Optional job name
            priority: Job priority (high, normal, low)
            tags: Optional list of tags
            metadata: Optional metadata dictionary
            timeout: Timeout in seconds
            retries: Number of retries on failure
            retry_delay: Delay in seconds between retries
            group_id: Optional group ID for batch operations
        """
        # Job identification
        self.job_id = str(uuid.uuid4())
        self.name = name or f"job_{self.job_id[:8]}"
        self.group_id = group_id
        
        # Job function and args
        self.func = func
        self.args = args or []
        self.kwargs = kwargs or {}
        
        # Job metadata
        self.tags = tags or []
        self.metadata = metadata or {}
        
        # Job status
        self.status = JobStatus.PENDING
        self.result = None
        self.error = None
        
        # Job configuration
        if isinstance(priority, str):
            try:
                self.priority = JobPriority(priority.lower())
            except ValueError:
                self.priority = JobPriority.NORMAL
        else:
            self.priority = priority
        
        self.timeout = timeout
        self.retries = retries
        self.retry_count = 0
        self.retry_delay = retry_delay
        
        # Job timing
        self.created_at = time.time()
        self.queue_time = None
        self.start_time = None
        self.end_time = None
        
        # Job progress
        self.progress = 0.0
        self.progress_message = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert job to dictionary.
        
        Returns:
            Dictionary representation of the job
        """
        return {
            "job_id": self.job_id,
            "name": self.name,
            "group_id": self.group_id,
            "status": self.status.value,
            "priority": self.priority.value,
            "tags": self.tags,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "queue_time": self.queue_time,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "timeout": self.timeout,
            "retries": self.retries,
            "retry_count": self.retry_count,
            "retry_delay": self.retry_delay,
            "progress": self.progress,
            "progress_message": self.progress_message,
            "error": self.error
        }
    
    @property
    def is_finished(self) -> bool:
        """
        Check if the job is finished.
        
        Returns:
            True if the job is completed, failed, or cancelled
        """
        return self.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]
    
    @property
    def is_active(self) -> bool:
        """
        Check if the job is active.
        
        Returns:
            True if the job is queued, running, or paused
        """
        return self.status in [JobStatus.QUEUED, JobStatus.RUNNING, JobStatus.PAUSED]
    
    @property
    def execution_time(self) -> Optional[float]:
        """
        Get the execution time in seconds.
        
        Returns:
            Execution time in seconds or None if the job hasn't started or finished
        """
        if not self.start_time:
            return None
        
        end = self.end_time or time.time()
        return end - self.start_time
    
    @property
    def wait_time(self) -> Optional[float]:
        """
        Get the wait time in seconds.
        
        Returns:
            Wait time in seconds or None if the job hasn't been queued
        """
        if not self.queue_time:
            return None
        
        start = self.start_time or time.time()
        return start - self.queue_time
    
    @property
    def total_time(self) -> Optional[float]:
        """
        Get the total time in seconds.
        
        Returns:
            Total time in seconds or None if the job hasn't finished
        """
        if not self.end_time:
            return None
        
        return self.end_time - self.created_at
    
    def can_retry(self) -> bool:
        """
        Check if the job can be retried.
        
        Returns:
            True if the job can be retried
        """
        return self.retry_count < self.retries
    
    def increment_retry(self) -> int:
        """
        Increment the retry count.
        
        Returns:
            New retry count
        """
        self.retry_count += 1
        return self.retry_count
    
    def mark_queued(self) -> None:
        """Mark the job as queued."""
        self.status = JobStatus.QUEUED
        self.queue_time = time.time()
    
    def mark_running(self) -> None:
        """Mark the job as running."""
        self.status = JobStatus.RUNNING
        self.start_time = time.time()
    
    def mark_completed(self, result: Any = None) -> None:
        """
        Mark the job as completed.
        
        Args:
            result: Optional result to store
        """
        self.status = JobStatus.COMPLETED
        self.result = result
        self.end_time = time.time()
        self.progress = 100.0
        self.progress_message = "Completed"
    
    def mark_failed(self, error: str = "") -> None:
        """
        Mark the job as failed.
        
        Args:
            error: Optional error message
        """
        self.status = JobStatus.FAILED
        self.error = error
        self.end_time = time.time()
        self.progress_message = f"Failed: {error}"
    
    def mark_cancelled(self) -> None:
        """Mark the job as cancelled."""
        self.status = JobStatus.CANCELLED
        self.end_time = time.time()
        self.progress_message = "Cancelled"
    
    def mark_paused(self) -> None:
        """Mark the job as paused."""
        self.status = JobStatus.PAUSED
        self.progress_message = "Paused"
    
    def mark_waiting(self) -> None:
        """Mark the job as pending."""
        self.status = JobStatus.PENDING
        self.progress_message = "Waiting"
    
    def update_progress(self, progress: float, message: str = "") -> None:
        """
        Update job progress.
        
        Args:
            progress: Progress percentage (0-100)
            message: Optional progress message
        """
        self.progress = max(0.0, min(100.0, progress))
        if message:
            self.progress_message = message


class JobQueue:
    """
    Queue for jobs with priority support.
    """
    
    def __init__(self):
        """Initialize the job queue."""
        self.queue = {
            JobPriority.CRITICAL: [],
            JobPriority.HIGH: [],
            JobPriority.NORMAL: [],
            JobPriority.LOW: []
        }
        self.job_map = {}
    
    def put(self, job: Job) -> None:
        """
        Add a job to the queue.
        
        Args:
            job: Job to add to the queue
        """
        self.queue[job.priority].append(job)
        self.job_map[job.job_id] = job
        job.mark_queued()
    
    def get(self) -> Optional[Job]:
        """
        Get the next job from the queue.
        
        Returns:
            Next job or None if queue is empty
        """
        # Try to get a job in priority order
        for priority in [JobPriority.CRITICAL, JobPriority.HIGH, JobPriority.NORMAL, JobPriority.LOW]:
            if self.queue[priority]:
                job = self.queue[priority].pop(0)
                del self.job_map[job.job_id]
                return job
        
        return None
    
    def peek(self) -> Optional[Job]:
        """
        Peek at the next job in the queue without removing it.
        
        Returns:
            Next job or None if queue is empty
        """
        # Try to peek at a job in priority order
        for priority in [JobPriority.CRITICAL, JobPriority.HIGH, JobPriority.NORMAL, JobPriority.LOW]:
            if self.queue[priority]:
                return self.queue[priority][0]
        
        return None
    
    def remove(self, job_id: str) -> Optional[Job]:
        """
        Remove a job from the queue.
        
        Args:
            job_id: ID of the job to remove
            
        Returns:
            Removed job or None if not found
        """
        if job_id not in self.job_map:
            return None
        
        job = self.job_map[job_id]
        self.queue[job.priority].remove(job)
        del self.job_map[job_id]
        return job
    
    def contains(self, job_id: str) -> bool:
        """
        Check if a job is in the queue.
        
        Args:
            job_id: ID of the job to check
            
        Returns:
            True if the job is in the queue, False otherwise
        """
        return job_id in self.job_map
    
    def get_job(self, job_id: str) -> Optional[Job]:
        """
        Get a job from the queue without removing it.
        
        Args:
            job_id: ID of the job to get
            
        Returns:
            Job or None if not found
        """
        return self.job_map.get(job_id)
    
    def size(self) -> int:
        """
        Get the size of the queue.
        
        Returns:
            Number of jobs in the queue
        """
        return len(self.job_map)
    
    def is_empty(self) -> bool:
        """
        Check if the queue is empty.
        
        Returns:
            True if the queue is empty, False otherwise
        """
        return self.size() == 0
    
    def clear(self) -> None:
        """Clear the queue."""
        self.queue = {
            JobPriority.CRITICAL: [],
            JobPriority.HIGH: [],
            JobPriority.NORMAL: [],
            JobPriority.LOW: []
        }
        self.job_map = {}
    
    def get_all_jobs(self) -> List[Job]:
        """
        Get all jobs in the queue.
        
        Returns:
            List of all jobs in the queue
        """
        return list(self.job_map.values())
    
    def get_jobs_by_priority(self, priority: JobPriority) -> List[Job]:
        """
        Get jobs with the specified priority.
        
        Args:
            priority: Priority to filter by
            
        Returns:
            List of jobs with the specified priority
        """
        return self.queue[priority][:]
    
    def get_jobs_by_status(self, status: JobStatus) -> List[Job]:
        """
        Get jobs with the specified status.
        
        Args:
            status: Status to filter by
            
        Returns:
            List of jobs with the specified status
        """
        return [job for job in self.job_map.values() if job.status == status]
    
    def get_jobs_by_tag(self, tag: str) -> List[Job]:
        """
        Get jobs with the specified tag.
        
        Args:
            tag: Tag to filter by
            
        Returns:
            List of jobs with the specified tag
        """
        return [job for job in self.job_map.values() if tag in job.tags]
    
    def get_jobs_by_group(self, group_id: str) -> List[Job]:
        """
        Get jobs with the specified group ID.
        
        Args:
            group_id: Group ID to filter by
            
        Returns:
            List of jobs with the specified group ID
        """
        return [job for job in self.job_map.values() if job.group_id == group_id]