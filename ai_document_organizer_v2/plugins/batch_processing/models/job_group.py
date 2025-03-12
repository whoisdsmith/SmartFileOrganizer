"""
Job group models for the Batch Processing Plugin.
"""

import enum
import time
import uuid
from typing import Any, Dict, List, Optional, Set, Tuple, Union, Callable


class JobGroup:
    """
    Represents a group of related jobs.
    
    A job group is used to manage multiple related jobs together, 
    with options for parallel or sequential execution.
    """
    
    def __init__(self,
                name: str,
                group_id: Optional[str] = None,
                description: Optional[str] = None,
                job_ids: Optional[List[str]] = None,
                sequential: bool = False,
                cancel_on_failure: bool = False,
                metadata: Optional[Dict[str, Any]] = None,
                created_at: Optional[float] = None):
        """
        Initialize a job group.
        
        Args:
            name: Group name
            group_id: Optional group ID (generated if not provided)
            description: Optional group description
            job_ids: Optional list of job IDs in this group
            sequential: Whether to process jobs sequentially or in parallel
            cancel_on_failure: Whether to cancel remaining jobs if one fails
            metadata: Optional metadata dictionary
            created_at: Optional creation timestamp
        """
        self.name = name
        self.group_id = group_id or f"group_{str(uuid.uuid4())}"
        self.description = description
        self.job_ids = job_ids or []
        self.sequential = sequential
        self.cancel_on_failure = cancel_on_failure
        self.metadata = metadata or {}
        self.created_at = created_at or time.time()
        self.updated_at = self.created_at
        
        # Internal state
        self.completed_jobs = []
        self.failed_jobs = []
        self.canceled_jobs = []
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary.
        
        Returns:
            Dictionary representation of the job group
        """
        return {
            "group_id": self.group_id,
            "name": self.name,
            "description": self.description,
            "job_ids": self.job_ids,
            "sequential": self.sequential,
            "cancel_on_failure": self.cancel_on_failure,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "completed_jobs": self.completed_jobs,
            "failed_jobs": self.failed_jobs,
            "canceled_jobs": self.canceled_jobs
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'JobGroup':
        """
        Create a job group from a dictionary.
        
        Args:
            data: Dictionary containing job group data
            
        Returns:
            JobGroup instance
        """
        group = cls(
            name=data.get("name", ""),
            group_id=data.get("group_id"),
            description=data.get("description"),
            job_ids=data.get("job_ids", []),
            sequential=data.get("sequential", False),
            cancel_on_failure=data.get("cancel_on_failure", False),
            metadata=data.get("metadata", {}),
            created_at=data.get("created_at")
        )
        
        # Set additional state
        group.updated_at = data.get("updated_at", group.created_at)
        group.completed_jobs = data.get("completed_jobs", [])
        group.failed_jobs = data.get("failed_jobs", [])
        group.canceled_jobs = data.get("canceled_jobs", [])
        
        return group
    
    def add_job(self, job_id: str) -> None:
        """
        Add a job to the group.
        
        Args:
            job_id: ID of the job to add
        """
        if job_id not in self.job_ids:
            self.job_ids.append(job_id)
            self.updated_at = time.time()
    
    def remove_job(self, job_id: str) -> bool:
        """
        Remove a job from the group.
        
        Args:
            job_id: ID of the job to remove
            
        Returns:
            True if the job was removed, False if it wasn't found
        """
        if job_id in self.job_ids:
            self.job_ids.remove(job_id)
            self.updated_at = time.time()
            return True
        return False
    
    def mark_job_completed(self, job_id: str) -> None:
        """
        Mark a job as completed.
        
        Args:
            job_id: ID of the completed job
        """
        if job_id in self.job_ids and job_id not in self.completed_jobs:
            self.completed_jobs.append(job_id)
            self.updated_at = time.time()
    
    def mark_job_failed(self, job_id: str) -> None:
        """
        Mark a job as failed.
        
        Args:
            job_id: ID of the failed job
        """
        if job_id in self.job_ids and job_id not in self.failed_jobs:
            self.failed_jobs.append(job_id)
            self.updated_at = time.time()
    
    def mark_job_canceled(self, job_id: str) -> None:
        """
        Mark a job as canceled.
        
        Args:
            job_id: ID of the canceled job
        """
        if job_id in self.job_ids and job_id not in self.canceled_jobs:
            self.canceled_jobs.append(job_id)
            self.updated_at = time.time()
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get the status of the job group.
        
        Returns:
            Dictionary with status information
        """
        total_jobs = len(self.job_ids)
        completed_count = len(self.completed_jobs)
        failed_count = len(self.failed_jobs)
        canceled_count = len(self.canceled_jobs)
        running_count = total_jobs - completed_count - failed_count - canceled_count
        
        progress = 0.0
        if total_jobs > 0:
            progress = (completed_count + failed_count + canceled_count) / total_jobs
        
        # Determine overall status
        status = "running"
        if total_jobs == 0:
            status = "empty"
        elif running_count == 0:
            if failed_count > 0:
                status = "failed"
            elif canceled_count > 0:
                status = "canceled"
            else:
                status = "completed"
        
        return {
            "status": status,
            "total_jobs": total_jobs,
            "completed": completed_count,
            "failed": failed_count,
            "canceled": canceled_count,
            "running": running_count,
            "progress": progress
        }
    
    def is_complete(self) -> bool:
        """
        Check if all jobs in the group are complete (success, failure, or canceled).
        
        Returns:
            True if all jobs are complete, False otherwise
        """
        total_finished = len(self.completed_jobs) + len(self.failed_jobs) + len(self.canceled_jobs)
        return total_finished == len(self.job_ids)
    
    def should_cancel_remaining(self) -> bool:
        """
        Check if remaining jobs should be canceled.
        
        Returns:
            True if remaining jobs should be canceled, False otherwise
        """
        return self.cancel_on_failure and len(self.failed_jobs) > 0
    
    def get_next_jobs_to_run(self, max_jobs: int = 10) -> List[str]:
        """
        Get the next jobs to run.
        
        Args:
            max_jobs: Maximum number of jobs to return
            
        Returns:
            List of job IDs to run next
        """
        if not self.job_ids:
            return []
        
        # If failed and should cancel, return empty list
        if self.should_cancel_remaining():
            return []
        
        # Get pending jobs
        completed_set = set(self.completed_jobs + self.failed_jobs + self.canceled_jobs)
        pending_jobs = [job_id for job_id in self.job_ids if job_id not in completed_set]
        
        # If sequential, return only the first pending job if there are completed jobs
        if self.sequential and self.completed_jobs:
            return pending_jobs[:1] if pending_jobs else []
        
        # Otherwise, return up to max_jobs pending jobs
        return pending_jobs[:max_jobs]
    
    def set_metadata(self, key: str, value: Any) -> None:
        """
        Set a metadata value.
        
        Args:
            key: Metadata key
            value: Metadata value
        """
        self.metadata[key] = value
        self.updated_at = time.time()
    
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