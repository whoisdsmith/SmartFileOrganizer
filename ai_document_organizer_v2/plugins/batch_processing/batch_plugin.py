"""
Batch Processing Plugin for AI Document Organizer V2.
"""

import json
import logging
import os
import threading
import time
import queue
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional, Set, Tuple, Union, Callable

from ai_document_organizer_v2.core.plugin_base import PluginBase
from ai_document_organizer_v2.plugins.batch_processing.models.job import Job, JobStatus, JobPriority
from ai_document_organizer_v2.plugins.batch_processing.models.job_group import JobGroup


logger = logging.getLogger(__name__)


class BatchProcessorPlugin(PluginBase):
    """
    Batch Processing Plugin for AI Document Organizer V2.
    
    This plugin provides:
    - Asynchronous job execution
    - Job queue management
    - Job groups for related tasks
    - Retry mechanisms for failed jobs
    - Job status tracking and reporting
    """
    
    plugin_name = "batch_processor"
    plugin_version = "1.0.0"
    plugin_description = "Batch processing and asynchronous job execution management"
    plugin_author = "AI Document Organizer Team"
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the batch processor plugin.
        
        Args:
            config: Optional configuration dictionary
        """
        super().__init__(config)
        
        # Configuration
        self.config = config or {}
        self.data_dir = self.config.get("data_dir", "data/batch_processor")
        
        # Job execution settings
        self.max_workers = self.config.get("max_workers", 4)
        self.max_queue_size = self.config.get("max_queue_size", 1000)
        self.poll_interval = self.config.get("poll_interval", 0.5)  # seconds
        
        # Job state
        self.jobs = {}  # job_id -> Job
        self.job_groups = {}  # group_id -> JobGroup
        
        # Job queue
        self.job_queue = queue.PriorityQueue(maxsize=self.max_queue_size)
        
        # Execution state
        self.running = False
        self.worker_thread = None
        self.executor = None
        self.job_futures = {}  # job_id -> Future
        
        # Statistics
        self.stats = {
            "jobs_submitted": 0,
            "jobs_completed": 0,
            "jobs_failed": 0,
            "jobs_canceled": 0,
            "total_execution_time": 0.0,
            "average_execution_time": 0.0,
            "average_wait_time": 0.0
        }
    
    def initialize(self) -> bool:
        """
        Initialize the plugin.
        
        Returns:
            True if initialization was successful, False otherwise
        """
        logger.info("Initializing BatchProcessorPlugin")
        
        # Create data directory if it doesn't exist
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Load jobs and job groups
        self._load_jobs()
        self._load_job_groups()
        
        # Reset running job states since we're just starting
        for job in self.jobs.values():
            if job.status in [JobStatus.RUNNING, JobStatus.QUEUED]:
                job.status = JobStatus.CREATED
        
        return True
    
    def activate(self) -> bool:
        """
        Activate the plugin.
        
        Returns:
            True if activation was successful, False otherwise
        """
        logger.info("Activating BatchProcessorPlugin")
        
        # Start worker thread
        self.start()
        
        return True
    
    def deactivate(self) -> bool:
        """
        Deactivate the plugin.
        
        Returns:
            True if deactivation was successful, False otherwise
        """
        logger.info("Deactivating BatchProcessorPlugin")
        
        # Stop worker thread
        self.stop()
        
        return True
    
    def shutdown(self) -> bool:
        """
        Shutdown the plugin and clean up resources.
        
        Returns:
            True if shutdown was successful, False otherwise
        """
        logger.info("Shutting down BatchProcessorPlugin")
        
        # Stop worker thread
        self.stop()
        
        # Save jobs and job groups
        self._save_jobs()
        self._save_job_groups()
        
        return True
    
    def get_info(self) -> Dict[str, Any]:
        """
        Get information about the plugin.
        
        Returns:
            Dictionary with plugin information
        """
        info = super().get_info()
        info.update({
            "jobs_count": len(self.jobs),
            "job_groups_count": len(self.job_groups),
            "jobs_in_queue": self.job_queue.qsize(),
            "max_workers": self.max_workers,
            "is_running": self.running,
            "jobs_submitted": self.stats["jobs_submitted"],
            "jobs_completed": self.stats["jobs_completed"],
            "jobs_failed": self.stats["jobs_failed"]
        })
        return info
    
    def get_type(self) -> str:
        """
        Get the plugin type.
        
        Returns:
            Plugin type
        """
        return "batch_processor"
    
    def get_capabilities(self) -> List[str]:
        """
        Get the plugin capabilities.
        
        Returns:
            List of capabilities
        """
        return [
            "async_job_execution",
            "job_queue_management",
            "job_grouping",
            "job_retry",
            "job_status_tracking"
        ]
    
    def _load_jobs(self) -> None:
        """Load jobs from file."""
        jobs_file = os.path.join(self.data_dir, 'jobs.json')
        if os.path.exists(jobs_file):
            try:
                with open(jobs_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                self.jobs = {}
                
                # Create a registry of task functions
                task_funcs = self._get_task_functions()
                
                for job_data in data.get('jobs', []):
                    # For each job, we need to get its task function from the task name
                    task_name = job_data.get("task_name", "")
                    task_func = task_funcs.get(task_name)
                    
                    if task_func:
                        job = Job.from_dict(job_data, task_func)
                        self.jobs[job.job_id] = job
                    else:
                        logger.warning(f"Unable to load job with unknown task name: {task_name}")
                
                logger.info(f"Loaded {len(self.jobs)} jobs")
                
                # Update stats
                self.stats["jobs_submitted"] = data.get("jobs_submitted", 0)
                self.stats["jobs_completed"] = data.get("jobs_completed", 0)
                self.stats["jobs_failed"] = data.get("jobs_failed", 0)
                self.stats["jobs_canceled"] = data.get("jobs_canceled", 0)
                self.stats["total_execution_time"] = data.get("total_execution_time", 0.0)
                self.stats["average_execution_time"] = data.get("average_execution_time", 0.0)
                self.stats["average_wait_time"] = data.get("average_wait_time", 0.0)
                
            except Exception as e:
                logger.error(f"Error loading jobs: {e}")
                self.jobs = {}
        else:
            logger.info("No jobs file found, starting with empty jobs")
            self.jobs = {}
    
    def _save_jobs(self) -> None:
        """Save jobs to file."""
        os.makedirs(self.data_dir, exist_ok=True)
        
        jobs_file = os.path.join(self.data_dir, 'jobs.json')
        try:
            job_dicts = []
            for job in self.jobs.values():
                job_dict = job.to_dict()
                # Skip result if too large or complex
                if 'result' in job_dict and (
                    not isinstance(job_dict['result'], (str, int, float, bool, list, dict)) or
                    (isinstance(job_dict['result'], (list, dict)) and len(str(job_dict['result'])) > 10000)
                ):
                    job_dict['result'] = f"[Complex result, size: {len(str(job_dict['result']))} bytes]"
                job_dicts.append(job_dict)
            
            data = {
                'jobs': job_dicts,
                'jobs_submitted': self.stats["jobs_submitted"],
                'jobs_completed': self.stats["jobs_completed"],
                'jobs_failed': self.stats["jobs_failed"],
                'jobs_canceled': self.stats["jobs_canceled"],
                'total_execution_time': self.stats["total_execution_time"],
                'average_execution_time': self.stats["average_execution_time"],
                'average_wait_time': self.stats["average_wait_time"]
            }
            
            with open(jobs_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved {len(self.jobs)} jobs")
        except Exception as e:
            logger.error(f"Error saving jobs: {e}")
    
    def _load_job_groups(self) -> None:
        """Load job groups from file."""
        groups_file = os.path.join(self.data_dir, 'job_groups.json')
        if os.path.exists(groups_file):
            try:
                with open(groups_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                self.job_groups = {}
                for group_data in data.get('job_groups', []):
                    group = JobGroup.from_dict(group_data)
                    self.job_groups[group.group_id] = group
                
                logger.info(f"Loaded {len(self.job_groups)} job groups")
            except Exception as e:
                logger.error(f"Error loading job groups: {e}")
                self.job_groups = {}
        else:
            logger.info("No job groups file found, starting with empty job groups")
            self.job_groups = {}
    
    def _save_job_groups(self) -> None:
        """Save job groups to file."""
        os.makedirs(self.data_dir, exist_ok=True)
        
        groups_file = os.path.join(self.data_dir, 'job_groups.json')
        try:
            data = {
                'job_groups': [group.to_dict() for group in self.job_groups.values()]
            }
            
            with open(groups_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved {len(self.job_groups)} job groups")
        except Exception as e:
            logger.error(f"Error saving job groups: {e}")
    
    def _get_task_functions(self) -> Dict[str, Callable]:
        """
        Get a dictionary of task name to task function mappings.
        
        Returns:
            Dictionary mapping task names to callable functions
        """
        # This needs to be implemented based on specific task names
        # For now, we'll return an empty dictionary
        return {}
    
    def start(self) -> bool:
        """
        Start the job processing.
        
        Returns:
            True if started successfully, False otherwise
        """
        if self.running:
            logger.warning("BatchProcessorPlugin is already running")
            return False
        
        logger.info("Starting BatchProcessorPlugin")
        self.running = True
        self.executor = ThreadPoolExecutor(max_workers=self.max_workers)
        self.worker_thread = threading.Thread(target=self._process_jobs)
        self.worker_thread.daemon = True
        self.worker_thread.start()
        
        return True
    
    def stop(self) -> bool:
        """
        Stop the job processing.
        
        Returns:
            True if stopped successfully, False otherwise
        """
        if not self.running:
            logger.warning("BatchProcessorPlugin is not running")
            return False
        
        logger.info("Stopping BatchProcessorPlugin")
        self.running = False
        
        # Wait for worker thread to finish
        if self.worker_thread and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=5.0)
        
        # Shutdown executor
        if self.executor:
            self.executor.shutdown(wait=False)
            self.executor = None
        
        return True
    
    def create_job(self,
                 task_name: str,
                 task_func: Callable,
                 task_args: Optional[Dict[str, Any]] = None,
                 priority: JobPriority = JobPriority.NORMAL,
                 max_retries: int = 0,
                 retry_delay: int = 60,
                 timeout: Optional[int] = None,
                 dependencies: Optional[List[str]] = None,
                 metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Create a new job.
        
        Args:
            task_name: Name of the task
            task_func: Function to execute for this job
            task_args: Arguments to pass to the task function
            priority: Job priority
            max_retries: Maximum number of retries for failed jobs
            retry_delay: Delay in seconds between retries
            timeout: Timeout in seconds for the job execution
            dependencies: List of job IDs that must complete before this job
            metadata: Optional metadata dictionary
            
        Returns:
            Job ID
        """
        job = Job(
            task_name=task_name,
            task_func=task_func,
            task_args=task_args,
            priority=priority,
            max_retries=max_retries,
            retry_delay=retry_delay,
            timeout=timeout,
            dependencies=dependencies,
            metadata=metadata
        )
        
        self.jobs[job.job_id] = job
        
        # Save
        self._save_jobs()
        
        return job.job_id
    
    def submit_job(self, job_id: str) -> bool:
        """
        Submit a job for execution.
        
        Args:
            job_id: ID of the job to submit
            
        Returns:
            True if job was submitted, False otherwise
        """
        if job_id not in self.jobs:
            logger.error(f"Job {job_id} not found")
            return False
        
        job = self.jobs[job_id]
        
        # Check if job is already running or completed
        if job.status not in [JobStatus.CREATED, JobStatus.FAILED]:
            logger.warning(f"Job {job_id} is already in state {job.status.value}")
            return False
        
        # Queue the job
        job.mark_queued()
        
        # Add to queue with priority
        priority_value = {
            JobPriority.LOW: 30,
            JobPriority.NORMAL: 20,
            JobPriority.HIGH: 10,
            JobPriority.CRITICAL: 0
        }[job.priority]
        
        try:
            self.job_queue.put((priority_value, job.job_id))
            self.stats["jobs_submitted"] += 1
            
            # Save
            self._save_jobs()
            
            return True
        except queue.Full:
            logger.error(f"Job queue is full, cannot submit job {job_id}")
            return False
    
    def create_and_submit_job(self,
                            task_name: str,
                            task_func: Callable,
                            task_args: Optional[Dict[str, Any]] = None,
                            priority: JobPriority = JobPriority.NORMAL,
                            max_retries: int = 0,
                            retry_delay: int = 60,
                            timeout: Optional[int] = None,
                            dependencies: Optional[List[str]] = None,
                            metadata: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        Create and submit a job for execution.
        
        Args:
            task_name: Name of the task
            task_func: Function to execute for this job
            task_args: Arguments to pass to the task function
            priority: Job priority
            max_retries: Maximum number of retries for failed jobs
            retry_delay: Delay in seconds between retries
            timeout: Timeout in seconds for the job execution
            dependencies: List of job IDs that must complete before this job
            metadata: Optional metadata dictionary
            
        Returns:
            Job ID if successful, None otherwise
        """
        job_id = self.create_job(
            task_name=task_name,
            task_func=task_func,
            task_args=task_args,
            priority=priority,
            max_retries=max_retries,
            retry_delay=retry_delay,
            timeout=timeout,
            dependencies=dependencies,
            metadata=metadata
        )
        
        if self.submit_job(job_id):
            return job_id
        return None
    
    def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a job.
        
        Args:
            job_id: ID of the job to cancel
            
        Returns:
            True if job was canceled, False otherwise
        """
        if job_id not in self.jobs:
            logger.error(f"Job {job_id} not found")
            return False
        
        job = self.jobs[job_id]
        
        # Check if job is already completed or canceled
        if job.is_terminal_state():
            logger.warning(f"Job {job_id} is already in terminal state {job.status.value}")
            return False
        
        # If job is running, cancel the future
        if job.status == JobStatus.RUNNING and job_id in self.job_futures:
            self.job_futures[job_id].cancel()
        
        # Mark as canceled
        job.mark_canceled()
        self.stats["jobs_canceled"] += 1
        
        # Update job group if any
        if job.group_id and job.group_id in self.job_groups:
            self.job_groups[job.group_id].mark_job_canceled(job_id)
        
        # Save
        self._save_jobs()
        self._save_job_groups()
        
        return True
    
    def create_job_group(self,
                       name: str,
                       job_ids: Optional[List[str]] = None,
                       description: Optional[str] = None,
                       sequential: bool = False,
                       cancel_on_failure: bool = False,
                       metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Create a job group.
        
        Args:
            name: Group name
            job_ids: Optional list of job IDs to add to the group
            description: Optional group description
            sequential: Whether to process jobs sequentially
            cancel_on_failure: Whether to cancel remaining jobs on failure
            metadata: Optional metadata dictionary
            
        Returns:
            Group ID
        """
        group = JobGroup(
            name=name,
            job_ids=job_ids,
            description=description,
            sequential=sequential,
            cancel_on_failure=cancel_on_failure,
            metadata=metadata
        )
        
        self.job_groups[group.group_id] = group
        
        # Update job references
        if job_ids:
            for job_id in job_ids:
                if job_id in self.jobs:
                    self.jobs[job_id].group_id = group.group_id
        
        # Save
        self._save_job_groups()
        self._save_jobs()
        
        return group.group_id
    
    def add_job_to_group(self, job_id: str, group_id: str) -> bool:
        """
        Add a job to a group.
        
        Args:
            job_id: ID of the job to add
            group_id: ID of the group to add the job to
            
        Returns:
            True if successful, False otherwise
        """
        if job_id not in self.jobs:
            logger.error(f"Job {job_id} not found")
            return False
        
        if group_id not in self.job_groups:
            logger.error(f"Group {group_id} not found")
            return False
        
        # Add job to group
        self.job_groups[group_id].add_job(job_id)
        
        # Update job reference
        self.jobs[job_id].group_id = group_id
        
        # Save
        self._save_job_groups()
        self._save_jobs()
        
        return True
    
    def remove_job_from_group(self, job_id: str, group_id: str) -> bool:
        """
        Remove a job from a group.
        
        Args:
            job_id: ID of the job to remove
            group_id: ID of the group to remove the job from
            
        Returns:
            True if successful, False otherwise
        """
        if job_id not in self.jobs:
            logger.error(f"Job {job_id} not found")
            return False
        
        if group_id not in self.job_groups:
            logger.error(f"Group {group_id} not found")
            return False
        
        # Remove job from group
        if not self.job_groups[group_id].remove_job(job_id):
            return False
        
        # Update job reference
        if self.jobs[job_id].group_id == group_id:
            self.jobs[job_id].group_id = None
        
        # Save
        self._save_job_groups()
        self._save_jobs()
        
        return True
    
    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a job by ID.
        
        Args:
            job_id: ID of the job to get
            
        Returns:
            Job dictionary or None if not found
        """
        if job_id not in self.jobs:
            return None
        
        return self.jobs[job_id].to_dict()
    
    def get_job_status(self, job_id: str) -> Optional[str]:
        """
        Get the status of a job.
        
        Args:
            job_id: ID of the job to get status for
            
        Returns:
            Job status string or None if job not found
        """
        if job_id not in self.jobs:
            return None
        
        return self.jobs[job_id].status.value
    
    def get_job_result(self, job_id: str) -> Optional[Any]:
        """
        Get the result of a completed job.
        
        Args:
            job_id: ID of the job to get result for
            
        Returns:
            Job result or None if job not found or not completed
        """
        if job_id not in self.jobs:
            return None
        
        job = self.jobs[job_id]
        if job.status != JobStatus.COMPLETED:
            return None
        
        return job.result
    
    def get_job_error(self, job_id: str) -> Optional[str]:
        """
        Get the error of a failed job.
        
        Args:
            job_id: ID of the job to get error for
            
        Returns:
            Job error or None if job not found or not failed
        """
        if job_id not in self.jobs:
            return None
        
        job = self.jobs[job_id]
        if job.status != JobStatus.FAILED:
            return None
        
        return job.error
    
    def get_job_group(self, group_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a job group by ID.
        
        Args:
            group_id: ID of the group to get
            
        Returns:
            Job group dictionary or None if not found
        """
        if group_id not in self.job_groups:
            return None
        
        return self.job_groups[group_id].to_dict()
    
    def get_job_group_status(self, group_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the status of a job group.
        
        Args:
            group_id: ID of the group to get status for
            
        Returns:
            Job group status dictionary or None if group not found
        """
        if group_id not in self.job_groups:
            return None
        
        return self.job_groups[group_id].get_status()
    
    def wait_for_job(self, job_id: str, timeout: Optional[float] = None) -> bool:
        """
        Wait for a job to complete.
        
        Args:
            job_id: ID of the job to wait for
            timeout: Maximum time to wait in seconds
            
        Returns:
            True if job completed successfully, False otherwise
        """
        if job_id not in self.jobs:
            logger.error(f"Job {job_id} not found")
            return False
        
        start_time = time.time()
        job = self.jobs[job_id]
        
        while not job.is_terminal_state():
            if timeout and time.time() - start_time > timeout:
                logger.warning(f"Timeout waiting for job {job_id}")
                return False
            
            time.sleep(self.poll_interval)
        
        return job.status == JobStatus.COMPLETED
    
    def wait_for_jobs(self, job_ids: List[str], timeout: Optional[float] = None) -> Dict[str, bool]:
        """
        Wait for multiple jobs to complete.
        
        Args:
            job_ids: List of job IDs to wait for
            timeout: Maximum time to wait in seconds
            
        Returns:
            Dictionary mapping job IDs to completion status
        """
        start_time = time.time()
        results = {}
        pending = set(job_id for job_id in job_ids if job_id in self.jobs)
        
        while pending:
            if timeout and time.time() - start_time > timeout:
                # Mark remaining jobs as timed out
                for job_id in pending:
                    results[job_id] = False
                logger.warning(f"Timeout waiting for jobs: {pending}")
                break
            
            # Check each pending job
            for job_id in list(pending):
                if job_id in self.jobs and self.jobs[job_id].is_terminal_state():
                    results[job_id] = self.jobs[job_id].status == JobStatus.COMPLETED
                    pending.remove(job_id)
            
            if pending:
                time.sleep(self.poll_interval)
        
        # Add any missing job IDs
        for job_id in job_ids:
            if job_id not in results:
                results[job_id] = False
        
        return results
    
    def wait_for_job_group(self, group_id: str, timeout: Optional[float] = None) -> bool:
        """
        Wait for all jobs in a group to complete.
        
        Args:
            group_id: ID of the group to wait for
            timeout: Maximum time to wait in seconds
            
        Returns:
            True if all jobs completed successfully, False otherwise
        """
        if group_id not in self.job_groups:
            logger.error(f"Group {group_id} not found")
            return False
        
        group = self.job_groups[group_id]
        job_ids = group.job_ids
        
        results = self.wait_for_jobs(job_ids, timeout)
        
        # Check if all jobs completed successfully
        return all(results.values())
    
    def get_job_stats(self) -> Dict[str, Any]:
        """
        Get job statistics.
        
        Returns:
            Dictionary with job statistics
        """
        return {
            "jobs_total": len(self.jobs),
            "jobs_submitted": self.stats["jobs_submitted"],
            "jobs_completed": self.stats["jobs_completed"],
            "jobs_failed": self.stats["jobs_failed"],
            "jobs_canceled": self.stats["jobs_canceled"],
            "average_execution_time": self.stats["average_execution_time"],
            "average_wait_time": self.stats["average_wait_time"],
            "job_groups_total": len(self.job_groups)
        }
    
    def _process_jobs(self) -> None:
        """Process jobs in the queue."""
        logger.info("Job processing thread started")
        
        while self.running:
            try:
                # Check if we can execute more jobs
                if len(self.job_futures) < self.max_workers:
                    try:
                        # Get a job from the queue (non-blocking)
                        priority, job_id = self.job_queue.get(block=False)
                        
                        # Process the job
                        self._execute_job(job_id)
                        
                        # Mark the task as done
                        self.job_queue.task_done()
                    except queue.Empty:
                        # No jobs in the queue, check if we can schedule jobs from groups
                        self._schedule_group_jobs()
                
                # Check for completed futures
                self._check_futures()
                
                # Small delay to avoid busy waiting
                time.sleep(self.poll_interval)
            
            except Exception as e:
                logger.error(f"Error in job processing thread: {e}")
                time.sleep(1.0)  # Longer delay on error
        
        logger.info("Job processing thread stopped")
    
    def _execute_job(self, job_id: str) -> None:
        """
        Execute a job.
        
        Args:
            job_id: ID of the job to execute
        """
        if job_id not in self.jobs:
            logger.error(f"Job {job_id} not found")
            return
        
        job = self.jobs[job_id]
        
        # Check for dependencies
        if job.dependencies:
            for dep_id in job.dependencies:
                if dep_id in self.jobs:
                    dep_job = self.jobs[dep_id]
                    if not dep_job.is_terminal_state():
                        # Dependency not completed, put back in queue with original priority
                        job.mark_waiting()
                        priority_value = {
                            JobPriority.LOW: 30,
                            JobPriority.NORMAL: 20,
                            JobPriority.HIGH: 10,
                            JobPriority.CRITICAL: 0
                        }[job.priority]
                        self.job_queue.put((priority_value, job_id))
                        return
                    elif dep_job.status != JobStatus.COMPLETED:
                        # Dependency failed or canceled
                        job.mark_failed(f"Dependency {dep_id} failed or was canceled")
                        self.stats["jobs_failed"] += 1
                        return
        
        # Mark as running
        job.mark_running()
        
        # Submit to executor
        self.job_futures[job_id] = self.executor.submit(self._run_job, job_id)
    
    def _run_job(self, job_id: str) -> None:
        """
        Run a job in a worker thread.
        
        Args:
            job_id: ID of the job to run
        """
        if job_id not in self.jobs:
            return
        
        job = self.jobs[job_id]
        
        try:
            # Execute the task function
            if job.timeout:
                # Not implemented: timeout handling would be more complex
                result = job.task_func(**job.task_args)
            else:
                result = job.task_func(**job.task_args)
            
            # Mark as completed
            job.mark_completed(result)
            self.stats["jobs_completed"] += 1
            
            # Update job group if any
            if job.group_id and job.group_id in self.job_groups:
                self.job_groups[job.group_id].mark_job_completed(job_id)
            
            # Update statistics
            execution_time = job.get_execution_time() or 0.0
            self.stats["total_execution_time"] += execution_time
            
            if self.stats["jobs_completed"] > 0:
                self.stats["average_execution_time"] = self.stats["total_execution_time"] / self.stats["jobs_completed"]
            
        except Exception as e:
            # Mark as failed
            error_msg = str(e)
            job.mark_failed(error_msg)
            self.stats["jobs_failed"] += 1
            
            # Update job group if any
            if job.group_id and job.group_id in self.job_groups:
                self.job_groups[job.group_id].mark_job_failed(job_id)
            
            logger.error(f"Job {job_id} failed: {error_msg}")
        
        finally:
            # Save state
            self._save_jobs()
            self._save_job_groups()
    
    def _check_futures(self) -> None:
        """Check for completed futures and remove them."""
        # Check each future
        for job_id in list(self.job_futures.keys()):
            future = self.job_futures[job_id]
            
            if future.done():
                # Remove from futures
                del self.job_futures[job_id]
                
                # Handle retry if job failed
                if job_id in self.jobs and self.jobs[job_id].status == JobStatus.FAILED:
                    job = self.jobs[job_id]
                    if job.can_retry():
                        # Increment retry count
                        job.increment_retry()
                        
                        # Re-queue the job
                        job.mark_queued()
                        
                        # Add to queue with priority
                        priority_value = {
                            JobPriority.LOW: 30,
                            JobPriority.NORMAL: 20,
                            JobPriority.HIGH: 10,
                            JobPriority.CRITICAL: 0
                        }[job.priority]
                        
                        # Wait for retry delay
                        time.sleep(job.retry_delay)
                        
                        try:
                            self.job_queue.put((priority_value, job_id))
                        except queue.Full:
                            logger.error(f"Job queue is full, cannot retry job {job_id}")
    
    def _schedule_group_jobs(self) -> None:
        """Schedule jobs from groups."""
        for group_id, group in self.job_groups.items():
            if group.is_complete():
                continue
            
            # Get next jobs to run
            next_jobs = group.get_next_jobs_to_run(max_jobs=self.max_workers - len(self.job_futures))
            
            for job_id in next_jobs:
                if job_id in self.jobs and self.jobs[job_id].status == JobStatus.CREATED:
                    # Submit the job
                    self.submit_job(job_id)