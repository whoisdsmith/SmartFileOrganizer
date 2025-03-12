"""
Job models for the Batch Processing Plugin.
"""

import enum
import time
import uuid
from typing import Any, Dict, List, Optional, Set, Tuple, Union, Callable


class JobStatus(enum.Enum):
    """Job status enumeration."""
    CREATED = "created"       # Job has been created but not submitted
    QUEUED = "queued"         # Job is in the queue waiting to be processed
    RUNNING = "running"       # Job is currently running
    PAUSED = "paused"         # Job execution is paused
    COMPLETED = "completed"   # Job has completed successfully
    FAILED = "failed"         # Job failed to complete
    CANCELED = "canceled"     # Job was canceled by the user
    WAITING = "waiting"       # Job is waiting for a dependency


class JobPriority(enum.Enum):
    """Job priority enumeration."""
    LOW = "low"               # Low priority job
    NORMAL = "normal"         # Normal priority job
    HIGH = "high"             # High priority job
    CRITICAL = "critical"     # Critical priority job


class Job:
    """
    Represents a batch processing job.
    
    A job is a unit of work that can be processed asynchronously.
    """
    
    def __init__(self,
                task_name: str,
                task_func: Callable,
                task_args: Optional[Dict[str, Any]] = None,
                job_id: Optional[str] = None,
                priority: JobPriority = JobPriority.NORMAL,
                max_retries: int = 0,
                retry_delay: int = 60,
                timeout: Optional[int] = None,
                dependencies: Optional[List[str]] = None,
                metadata: Optional[Dict[str, Any]] = None,
                created_at: Optional[float] = None):
        """
        Initialize a job.
        
        Args:
            task_name: Name of the task
            task_func: Function to execute for this job
            task_args: Arguments to pass to the task function
            job_id: Optional job ID (generated if not provided)
            priority: Job priority
            max_retries: Maximum number of retries for failed jobs
            retry_delay: Delay in seconds between retries
            timeout: Timeout in seconds for the job execution (None for no timeout)
            dependencies: List of job IDs that must complete before this job
            metadata: Optional metadata dictionary
            created_at: Optional creation timestamp
        """
        self.task_name = task_name
        self.task_func = task_func
        self.task_args = task_args or {}
        
        # Job identification
        self.job_id = job_id or f"job_{str(uuid.uuid4())}"
        
        # Job configuration
        self.priority = priority
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.timeout = timeout
        self.dependencies = dependencies or []
        self.metadata = metadata or {}
        
        # Job state
        self.status = JobStatus.CREATED
        self.created_at = created_at or time.time()
        self.queued_at = None
        self.started_at = None
        self.completed_at = None
        self.last_retry_at = None
        self.retry_count = 0
        self.error = None
        self.result = None
        self.progress = 0.0  # Progress from 0.0 to 1.0
        
        # Job group association
        self.group_id = None
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary.
        
        Returns:
            Dictionary representation of the job
        """
        # Task function can't be serialized to JSON, so we exclude it
        return {
            "job_id": self.job_id,
            "task_name": self.task_name,
            "task_args": self.task_args,
            "priority": self.priority.value,
            "max_retries": self.max_retries,
            "retry_delay": self.retry_delay,
            "timeout": self.timeout,
            "dependencies": self.dependencies,
            "metadata": self.metadata,
            "status": self.status.value,
            "created_at": self.created_at,
            "queued_at": self.queued_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "last_retry_at": self.last_retry_at,
            "retry_count": self.retry_count,
            "error": self.error,
            "progress": self.progress,
            "group_id": self.group_id
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any], task_func: Optional[Callable] = None) -> 'Job':
        """
        Create a job from a dictionary.
        
        Args:
            data: Dictionary containing job data
            task_func: Function to execute for this job (required if not in running state)
            
        Returns:
            Job instance
        """
        # Convert string values to enums
        priority = JobPriority(data.get("priority", "normal"))
        
        # Create job without initializing status and timestamps
        job = cls(
            task_name=data.get("task_name", ""),
            task_func=task_func,
            task_args=data.get("task_args", {}),
            job_id=data.get("job_id"),
            priority=priority,
            max_retries=data.get("max_retries", 0),
            retry_delay=data.get("retry_delay", 60),
            timeout=data.get("timeout"),
            dependencies=data.get("dependencies", []),
            metadata=data.get("metadata", {}),
            created_at=data.get("created_at")
        )
        
        # Set state values
        if "status" in data:
            job.status = JobStatus(data["status"])
        
        job.queued_at = data.get("queued_at")
        job.started_at = data.get("started_at")
        job.completed_at = data.get("completed_at")
        job.last_retry_at = data.get("last_retry_at")
        job.retry_count = data.get("retry_count", 0)
        job.error = data.get("error")
        job.progress = data.get("progress", 0.0)
        job.group_id = data.get("group_id")
        
        if "result" in data:
            job.result = data["result"]
        
        return job
    
    def mark_queued(self) -> None:
        """Mark the job as queued."""
        self.status = JobStatus.QUEUED
        self.queued_at = time.time()
    
    def mark_running(self) -> None:
        """Mark the job as running."""
        self.status = JobStatus.RUNNING
        self.started_at = time.time()
    
    def mark_paused(self) -> None:
        """Mark the job as paused."""
        self.status = JobStatus.PAUSED
    
    def mark_completed(self, result: Any = None) -> None:
        """
        Mark the job as completed.
        
        Args:
            result: Optional result of the job
        """
        self.status = JobStatus.COMPLETED
        self.completed_at = time.time()
        self.result = result
        self.progress = 1.0
    
    def mark_failed(self, error: str) -> None:
        """
        Mark the job as failed.
        
        Args:
            error: Error message describing the failure
        """
        self.status = JobStatus.FAILED
        self.completed_at = time.time()
        self.error = error
    
    def mark_canceled(self) -> None:
        """Mark the job as canceled."""
        self.status = JobStatus.CANCELED
        self.completed_at = time.time()
    
    def mark_waiting(self) -> None:
        """Mark the job as waiting for dependencies."""
        self.status = JobStatus.WAITING
    
    def increment_retry(self) -> None:
        """Increment retry count and update last retry timestamp."""
        self.retry_count += 1
        self.last_retry_at = time.time()
    
    def can_retry(self) -> bool:
        """
        Check if the job can be retried.
        
        Returns:
            True if the job can be retried, False otherwise
        """
        return self.status == JobStatus.FAILED and self.retry_count < self.max_retries
    
    def update_progress(self, progress: float) -> None:
        """
        Update job progress.
        
        Args:
            progress: Progress value between 0.0 and 1.0
        """
        self.progress = max(0.0, min(1.0, progress))
    
    def is_terminal_state(self) -> bool:
        """
        Check if the job is in a terminal state (completed, failed, canceled).
        
        Returns:
            True if job is in terminal state, False otherwise
        """
        return self.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELED]
    
    def get_execution_time(self) -> Optional[float]:
        """
        Get the execution time in seconds.
        
        Returns:
            Execution time or None if not completed or started
        """
        if self.started_at and self.completed_at:
            return self.completed_at - self.started_at
        return None
    
    def get_wait_time(self) -> Optional[float]:
        """
        Get the wait time in queue in seconds.
        
        Returns:
            Wait time or None if not queued or started
        """
        if self.queued_at and self.started_at:
            return self.started_at - self.queued_at
        elif self.queued_at and not self.started_at:
            return time.time() - self.queued_at
        return None
    
    def get_age(self) -> float:
        """
        Get the age of the job in seconds.
        
        Returns:
            Age in seconds
        """
        return time.time() - self.created_at
    
    def set_metadata(self, key: str, value: Any) -> None:
        """
        Set a metadata value.
        
        Args:
            key: Metadata key
            value: Metadata value
        """
        self.metadata[key] = value
    
    def get_metadata(self, key: str, default: Any = None) -> Any:
        """
        Get a metadata value.
        
        Args:
            key: Metadata key
            default: Default value if the key is not found
            
        Returns:
            Metadata value or default
        """
        return self.metadata.get(key, default)