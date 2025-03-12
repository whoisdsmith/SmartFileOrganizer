"""
Job Queue for the Batch Processing Plugin.

Manages the queue of jobs to be processed, with support for priorities,
dependencies, and advanced scheduling.
"""

import time
import logging
import threading
from queue import PriorityQueue
from typing import Dict, List, Any, Optional, Set, Tuple, Iterator

from ..models.job import Job, JobStatus, JobPriority

logger = logging.getLogger(__name__)

class JobQueue:
    """
    Manages a queue of jobs with priority, dependency resolution, and scheduling.
    Thread-safe implementation for concurrent access.
    """
    
    def __init__(self):
        """Initialize a new job queue."""
        self._queue = PriorityQueue()
        self._jobs: Dict[str, Job] = {}
        self._dependency_map: Dict[str, Set[str]] = {}  # job_id -> set of dependent job_ids
        self._lock = threading.RLock()
        self._condition = threading.Condition(self._lock)
        
    def add_job(self, job: Job) -> bool:
        """
        Add a job to the queue.
        
        Args:
            job: Job to add
            
        Returns:
            True if the job was added successfully
        """
        with self._lock:
            # Check if job already exists
            if job.job_id in self._jobs:
                logger.warning(f"Job {job.job_id} already exists in the queue")
                return False
            
            # Store the job
            self._jobs[job.job_id] = job
            
            # Update dependency tracking
            for dep_id in job.dependencies:
                if dep_id not in self._dependency_map:
                    self._dependency_map[dep_id] = set()
                self._dependency_map[dep_id].add(job.job_id)
            
            # Check if the job has unresolved dependencies
            if self._has_unresolved_dependencies(job):
                job.mark_waiting()
            else:
                # No dependencies, add to the queue
                job.mark_queued()
                self._queue.put((job, job.created_at))
                self._condition.notify_all()
            
            return True
    
    def get_next_job(self, timeout: Optional[float] = None) -> Optional[Job]:
        """
        Get the next job to process.
        
        Args:
            timeout: Optional timeout in seconds
            
        Returns:
            The next job or None if queue is empty or timeout occurs
        """
        with self._condition:
            try:
                # Wait for a job to be available or timeout
                if self._queue.empty():
                    if timeout is not None:
                        self._condition.wait(timeout)
                    else:
                        self._condition.wait()
                
                if self._queue.empty():
                    return None
                
                job, _ = self._queue.get(block=False)
                job.mark_running()
                return job
            except Exception as e:
                logger.error(f"Error getting next job: {e}")
                return None
    
    def update_job(self, job: Job) -> bool:
        """
        Update a job in the queue.
        
        Args:
            job: Updated job
            
        Returns:
            True if the job was updated successfully
        """
        with self._lock:
            if job.job_id not in self._jobs:
                logger.warning(f"Job {job.job_id} not found in the queue")
                return False
            
            self._jobs[job.job_id] = job
            
            # If the job is completed, check for dependent jobs
            if job.status == JobStatus.COMPLETED and job.job_id in self._dependency_map:
                self._process_dependent_jobs(job.job_id)
            
            return True
    
    def remove_job(self, job_id: str) -> Optional[Job]:
        """
        Remove a job from the queue.
        
        Args:
            job_id: ID of the job to remove
            
        Returns:
            The removed job or None if not found
        """
        with self._lock:
            if job_id not in self._jobs:
                return None
            
            job = self._jobs.pop(job_id)
            
            # Remove from dependency map
            if job_id in self._dependency_map:
                del self._dependency_map[job_id]
            
            # Remove dependencies from other jobs
            for dep_map in self._dependency_map.values():
                if job_id in dep_map:
                    dep_map.remove(job_id)
            
            return job
    
    def get_job(self, job_id: str) -> Optional[Job]:
        """
        Get a job by ID.
        
        Args:
            job_id: ID of the job to get
            
        Returns:
            The job or None if not found
        """
        with self._lock:
            return self._jobs.get(job_id)
    
    def get_all_jobs(self) -> List[Job]:
        """
        Get all jobs in the queue.
        
        Returns:
            List of all jobs
        """
        with self._lock:
            return list(self._jobs.values())
    
    def get_jobs_by_status(self, status: JobStatus) -> List[Job]:
        """
        Get jobs by status.
        
        Args:
            status: Status to filter by
            
        Returns:
            List of jobs with the specified status
        """
        with self._lock:
            return [job for job in self._jobs.values() if job.status == status]
    
    def get_jobs_by_tag(self, tag: str) -> List[Job]:
        """
        Get jobs by tag.
        
        Args:
            tag: Tag to filter by
            
        Returns:
            List of jobs with the specified tag
        """
        with self._lock:
            return [job for job in self._jobs.values() if tag in job.tags]
    
    def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a job.
        
        Args:
            job_id: ID of the job to cancel
            
        Returns:
            True if the job was canceled successfully
        """
        with self._lock:
            if job_id not in self._jobs:
                return False
            
            job = self._jobs[job_id]
            job.mark_canceled()
            
            # Process dependencies if needed
            if job_id in self._dependency_map:
                # For canceled jobs, we consider dependencies as failed
                for dep_job_id in self._dependency_map[job_id]:
                    dep_job = self._jobs.get(dep_job_id)
                    if dep_job and dep_job.status == JobStatus.WAITING:
                        dep_job.mark_failed(Exception(f"Dependency {job_id} was canceled"))
            
            return True
    
    def pause_job(self, job_id: str, checkpoint_data: Optional[Dict[str, Any]] = None) -> bool:
        """
        Pause a job.
        
        Args:
            job_id: ID of the job to pause
            checkpoint_data: Optional checkpoint data for resuming
            
        Returns:
            True if the job was paused successfully
        """
        with self._lock:
            if job_id not in self._jobs:
                return False
            
            job = self._jobs[job_id]
            job.mark_paused(checkpoint_data)
            return True
    
    def resume_job(self, job_id: str) -> bool:
        """
        Resume a paused job.
        
        Args:
            job_id: ID of the job to resume
            
        Returns:
            True if the job was resumed successfully
        """
        with self._lock:
            if job_id not in self._jobs:
                return False
            
            job = self._jobs[job_id]
            if job.status != JobStatus.PAUSED:
                return False
            
            # Check if the job has unresolved dependencies
            if self._has_unresolved_dependencies(job):
                job.mark_waiting()
            else:
                job.mark_queued()
                self._queue.put((job, time.time()))
                self._condition.notify_all()
            
            return True
    
    def retry_job(self, job_id: str) -> bool:
        """
        Retry a failed job.
        
        Args:
            job_id: ID of the job to retry
            
        Returns:
            True if the job was requeued for retry
        """
        with self._lock:
            if job_id not in self._jobs:
                return False
            
            job = self._jobs[job_id]
            if not job.can_retry():
                return False
            
            job.increment_retry()
            
            # Check if the job has unresolved dependencies
            if self._has_unresolved_dependencies(job):
                job.mark_waiting()
            else:
                job.mark_queued()
                self._queue.put((job, time.time()))
                self._condition.notify_all()
            
            return True
    
    def clear(self) -> None:
        """Clear all jobs from the queue."""
        with self._lock:
            self._jobs.clear()
            self._dependency_map.clear()
            
            # Clear the priority queue
            while not self._queue.empty():
                try:
                    self._queue.get(block=False)
                except Exception:
                    pass
    
    def size(self) -> int:
        """
        Get the total number of jobs in the queue.
        
        Returns:
            Number of jobs
        """
        with self._lock:
            return len(self._jobs)
    
    def active_queue_size(self) -> int:
        """
        Get the number of jobs actively queued (not waiting or paused).
        
        Returns:
            Number of actively queued jobs
        """
        with self._lock:
            return self._queue.qsize()
    
    def reprioritize_job(self, job_id: str, new_priority: JobPriority) -> bool:
        """
        Change the priority of a queued job.
        
        Args:
            job_id: ID of the job to reprioritize
            new_priority: New priority level
            
        Returns:
            True if the job priority was changed successfully
        """
        with self._lock:
            if job_id not in self._jobs:
                return False
            
            job = self._jobs[job_id]
            if job.status != JobStatus.QUEUED:
                # Can only reprioritize queued jobs
                return False
            
            # Update the priority
            job.priority = new_priority
            
            # For simplicity, we'll put the job back into the queue with the new priority
            # Note: In a production system, we might want a more efficient approach
            # since this could result in duplicate entries
            self._queue.put((job, time.time()))
            
            return True
    
    def _has_unresolved_dependencies(self, job: Job) -> bool:
        """
        Check if a job has unresolved dependencies.
        
        Args:
            job: Job to check
            
        Returns:
            True if the job has unresolved dependencies
        """
        for dep_id in job.dependencies:
            if dep_id not in self._jobs:
                logger.warning(f"Dependency {dep_id} not found for job {job.job_id}")
                return True
            
            dep_job = self._jobs[dep_id]
            if dep_job.status != JobStatus.COMPLETED:
                return True
        
        return False
    
    def _process_dependent_jobs(self, completed_job_id: str) -> None:
        """
        Process jobs that depend on a completed job.
        
        Args:
            completed_job_id: ID of the completed job
        """
        if completed_job_id not in self._dependency_map:
            return
        
        # Get jobs that depend on the completed job
        dependent_job_ids = self._dependency_map[completed_job_id]
        for dep_job_id in dependent_job_ids:
            if dep_job_id not in self._jobs:
                continue
            
            dep_job = self._jobs[dep_job_id]
            if dep_job.status == JobStatus.WAITING:
                # Check if all dependencies are resolved
                if not self._has_unresolved_dependencies(dep_job):
                    # All dependencies resolved, queue the job
                    dep_job.mark_queued()
                    self._queue.put((dep_job, time.time()))
                    self._condition.notify_all()
    
    def __iter__(self) -> Iterator[Job]:
        """
        Iterate over all jobs in the queue.
        
        Returns:
            Iterator over all jobs
        """
        with self._lock:
            return iter(list(self._jobs.values()))