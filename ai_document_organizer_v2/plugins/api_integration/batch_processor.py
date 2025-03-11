"""
Batch Processor for External API Integration Framework.

This module provides batch processing capabilities for API operations,
allowing for efficient execution of multiple operations in a single batch.
"""

import logging
import threading
import time
import uuid
import queue
from typing import Any, Dict, List, Optional, Union, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed


logger = logging.getLogger(__name__)


class BatchJob:
    """
    Represents a batch job configuration.
    
    A batch job contains multiple operations to be executed as a batch,
    with configurable concurrency, timeouts, and retry policies.
    """
    
    def __init__(self, 
                job_id: str,
                api_name: str,
                plugin_name: str,
                operations: List[Dict[str, Any]],
                max_concurrency: int = 5,
                timeout: Optional[int] = None,
                max_retries: int = 3,
                retry_delay: int = 5,
                description: Optional[str] = None):
        """
        Initialize a batch job.
        
        Args:
            job_id: Unique identifier for the job
            api_name: Name of the API for the batch job
            plugin_name: Name of the plugin to use for operations
            operations: List of operations to execute in the batch
            max_concurrency: Maximum number of concurrent operations
            timeout: Optional timeout in seconds for the entire batch
            max_retries: Maximum number of retries for failed operations
            retry_delay: Delay in seconds between retries
            description: Optional description of the job
        """
        self.job_id = job_id
        self.api_name = api_name
        self.plugin_name = plugin_name
        self.operations = operations
        self.max_concurrency = max_concurrency
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.description = description
        
        # Job state
        self.status = 'created'  # created, running, completed, failed, cancelled
        self.created_at = time.time()
        self.updated_at = time.time()
        self.start_time = None
        self.end_time = None
        self.results = []
        self.error = None
        self.progress = 0  # 0-100%
        self.completed_operations = 0
        self.failed_operations = 0
        
        # Internal state
        self._operation_results = {}  # type: Dict[str, Any]
        self._operation_status = {}  # type: Dict[str, str]
        self._operation_retries = {}  # type: Dict[str, int]
        self._operation_errors = {}  # type: Dict[str, str]
        
        # Initialize operation state
        for i, op in enumerate(operations):
            op_id = op.get('id') or f"{job_id}_op_{i}"
            self._operation_status[op_id] = 'pending'
            self._operation_retries[op_id] = 0
        
    def __str__(self):
        """Return a string representation of the job."""
        return f"BatchJob({self.job_id}, {self.api_name}, {len(self.operations)} operations, status={self.status})"


class BatchProcessor:
    """
    Processes batch operations for API requests.
    
    This class provides functionality to:
    - Create and manage batch jobs
    - Execute operations concurrently within batch limits
    - Handle retries for failed operations
    - Track and report batch job progress
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the Batch Processor.
        
        Args:
            config: Optional configuration dictionary for the processor
        """
        self.config = config or {}
        
        # Batch processor settings
        self.max_concurrent_jobs = self.config.get('max_concurrent_jobs', 5)
        self.max_operation_concurrency = self.config.get('max_operation_concurrency', 10)
        self.default_timeout = self.config.get('default_timeout', 3600)  # 1 hour
        self.default_max_retries = self.config.get('default_max_retries', 3)
        self.default_retry_delay = self.config.get('default_retry_delay', 5)
        
        # Job registry
        self.jobs = {}  # type: Dict[str, BatchJob]
        self.active_jobs = set()  # type: Set[str]
        self.job_queues = {}  # type: Dict[str, queue.Queue]
        self.job_threads = {}  # type: Dict[str, threading.Thread]
        self.handlers = {}  # type: Dict[str, List[Callable]]
        
        # Thread safety
        self._lock = threading.RLock()
        
        logger.info("Batch Processor initialized")
    
    def create_job(self, 
                  api_name: str,
                  plugin_name: str,
                  operations: List[Dict[str, Any]],
                  max_concurrency: Optional[int] = None,
                  timeout: Optional[int] = None,
                  max_retries: Optional[int] = None,
                  retry_delay: Optional[int] = None,
                  job_id: Optional[str] = None,
                  description: Optional[str] = None) -> str:
        """
        Create a new batch job.
        
        Args:
            api_name: Name of the API for the batch job
            plugin_name: Name of the plugin to use for operations
            operations: List of operations to execute in the batch
            max_concurrency: Maximum number of concurrent operations
            timeout: Optional timeout in seconds for the entire batch
            max_retries: Maximum number of retries for failed operations
            retry_delay: Delay in seconds between retries
            job_id: Optional unique identifier for the job
            description: Optional description of the job
            
        Returns:
            Job ID of the created job
        """
        # Validate operations
        if not operations:
            raise ValueError("Operations list cannot be empty")
            
        # Apply default values
        if max_concurrency is None:
            max_concurrency = min(self.max_operation_concurrency, len(operations))
            
        if timeout is None:
            timeout = self.default_timeout
            
        if max_retries is None:
            max_retries = self.default_max_retries
            
        if retry_delay is None:
            retry_delay = self.default_retry_delay
            
        # Generate job ID if not provided
        if not job_id:
            job_id = str(uuid.uuid4())
            
        # Create the job
        with self._lock:
            if job_id in self.jobs:
                logger.warning(f"Job ID {job_id} already exists, overwriting")
                
            job = BatchJob(
                job_id=job_id,
                api_name=api_name,
                plugin_name=plugin_name,
                operations=operations,
                max_concurrency=max_concurrency,
                timeout=timeout,
                max_retries=max_retries,
                retry_delay=retry_delay,
                description=description
            )
            
            self.jobs[job_id] = job
            
            # Create job queue
            self.job_queues[job_id] = queue.Queue()
            
            # Initialize handlers for this job
            if job_id not in self.handlers:
                self.handlers[job_id] = []
                
            logger.info(f"Created batch job {job_id} for {api_name} with {len(operations)} operations")
            return job_id
    
    def start_job(self, job_id: str) -> bool:
        """
        Start a batch job.
        
        Args:
            job_id: ID of the job to start
            
        Returns:
            True if the job was started successfully, False otherwise
        """
        with self._lock:
            if job_id not in self.jobs:
                logger.warning(f"Job {job_id} does not exist")
                return False
                
            job = self.jobs[job_id]
            
            # Check if already running
            if job.status == 'running':
                logger.warning(f"Job {job_id} is already running")
                return False
                
            # Check if completed
            if job.status in ['completed', 'failed', 'cancelled']:
                logger.warning(f"Job {job_id} has already {job.status}")
                return False
                
            # Check if too many active jobs
            if len(self.active_jobs) >= self.max_concurrent_jobs:
                logger.warning(f"Too many active jobs ({len(self.active_jobs)}), cannot start job {job_id}")
                return False
                
            # Update job state
            job.status = 'running'
            job.start_time = time.time()
            job.updated_at = time.time()
            
            # Add to active jobs
            self.active_jobs.add(job_id)
            
            # Start job thread
            thread = threading.Thread(target=self._execute_job, args=(job_id,))
            thread.daemon = True
            thread.start()
            
            self.job_threads[job_id] = thread
            
            logger.info(f"Started batch job {job_id}")
            return True
    
    def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a batch job.
        
        Args:
            job_id: ID of the job to cancel
            
        Returns:
            True if the job was cancelled successfully, False otherwise
        """
        with self._lock:
            if job_id not in self.jobs:
                logger.warning(f"Job {job_id} does not exist")
                return False
                
            job = self.jobs[job_id]
            
            # Check if already completed or cancelled
            if job.status in ['completed', 'failed', 'cancelled']:
                logger.warning(f"Job {job_id} has already {job.status}")
                return False
                
            # Update job state
            job.status = 'cancelled'
            job.end_time = time.time()
            job.updated_at = time.time()
            job.error = "Cancelled by user"
            
            # Remove from active jobs
            if job_id in self.active_jobs:
                self.active_jobs.remove(job_id)
                
            # Signal thread to stop
            if job_id in self.job_queues:
                try:
                    self.job_queues[job_id].put('CANCEL')
                except:
                    pass
                
            logger.info(f"Cancelled batch job {job_id}")
            return True
    
    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a batch job.
        
        Args:
            job_id: ID of the job
            
        Returns:
            Dictionary with job information or None if not found
        """
        if job_id not in self.jobs:
            return None
            
        job = self.jobs[job_id]
        
        # Create a dictionary representation of the job
        job_info = {
            'job_id': job.job_id,
            'api_name': job.api_name,
            'plugin_name': job.plugin_name,
            'status': job.status,
            'total_operations': len(job.operations),
            'completed_operations': job.completed_operations,
            'failed_operations': job.failed_operations,
            'progress': job.progress,
            'max_concurrency': job.max_concurrency,
            'timeout': job.timeout,
            'max_retries': job.max_retries,
            'retry_delay': job.retry_delay,
            'description': job.description,
            'created_at': job.created_at,
            'updated_at': job.updated_at,
            'duration': (job.end_time - job.start_time) if job.end_time and job.start_time else None
        }
        
        # Add timestamps
        if job.start_time:
            job_info['start_time'] = job.start_time
            
        if job.end_time:
            job_info['end_time'] = job.end_time
            
        # Add error if available
        if job.error:
            job_info['error'] = job.error
            
        # Add operation details if requested
        if self.config.get('include_operation_details', True):
            job_info['operations'] = []
            
            for i, op in enumerate(job.operations):
                op_id = op.get('id') or f"{job.job_id}_op_{i}"
                op_info = {
                    'id': op_id,
                    'status': job._operation_status.get(op_id, 'unknown'),
                    'retries': job._operation_retries.get(op_id, 0)
                }
                
                if op_id in job._operation_errors:
                    op_info['error'] = job._operation_errors[op_id]
                    
                if op_id in job._operation_results:
                    op_info['result'] = job._operation_results[op_id]
                    
                job_info['operations'].append(op_info)
            
        return job_info
    
    def get_all_jobs(self) -> List[Dict[str, Any]]:
        """
        Get information about all batch jobs.
        
        Returns:
            List of dictionaries with job information
        """
        return [self.get_job(job_id) for job_id in self.jobs]
    
    def register_job_handler(self, job_id: str, handler: Callable) -> bool:
        """
        Register a handler function for a batch job.
        
        The handler will be called when the job completes.
        
        Args:
            job_id: ID of the job
            handler: Function to call when the job completes
            
        Returns:
            True if registration was successful, False otherwise
        """
        if job_id not in self.jobs:
            logger.warning(f"Cannot register handler: Job {job_id} does not exist")
            return False
            
        # Register the handler
        with self._lock:
            if job_id not in self.handlers:
                self.handlers[job_id] = []
                
            self.handlers[job_id].append(handler)
            logger.info(f"Registered handler for job {job_id}")
            return True
    
    def unregister_job_handler(self, job_id: str, handler: Callable) -> bool:
        """
        Unregister a handler function for a batch job.
        
        Args:
            job_id: ID of the job
            handler: Handler function to unregister
            
        Returns:
            True if unregistration was successful, False otherwise
        """
        if job_id not in self.handlers:
            logger.warning(f"No handlers registered for job {job_id}")
            return False
            
        try:
            with self._lock:
                self.handlers[job_id].remove(handler)
                logger.info(f"Unregistered handler for job {job_id}")
                return True
        except ValueError:
            logger.warning(f"Handler not found for job {job_id}")
            return False
    
    def _execute_job(self, job_id: str):
        """
        Execute a batch job.
        
        Args:
            job_id: ID of the job to execute
        """
        job = self.jobs[job_id]
        job_queue = self.job_queues[job_id]
        api_gateway = self.config.get('api_gateway')
        
        if not api_gateway:
            self._handle_job_failure(job, "API Gateway not configured")
            return
            
        try:
            logger.info(f"Executing batch job {job_id} with {len(job.operations)} operations")
            
            # Track start time for timeout
            start_time = time.time()
            timeout_time = start_time + job.timeout if job.timeout else None
            
            # Create operation queues
            pending_ops = list(enumerate(job.operations))
            active_ops = set()
            completed_ops = []
            failed_ops = []
            
            # Create thread pool
            with ThreadPoolExecutor(max_workers=job.max_concurrency) as executor:
                futures = {}
                
                # Main processing loop
                while pending_ops or active_ops:
                    # Check for cancellation
                    try:
                        if not job_queue.empty() and job_queue.get_nowait() == 'CANCEL':
                            logger.info(f"Batch job {job_id} cancelled during execution")
                            executor.shutdown(wait=False)
                            self._handle_job_cancellation(job)
                            return
                    except queue.Empty:
                        pass
                        
                    # Check timeout
                    if timeout_time and time.time() > timeout_time:
                        logger.warning(f"Batch job {job_id} timed out after {job.timeout} seconds")
                        executor.shutdown(wait=False)
                        self._handle_job_failure(job, f"Timed out after {job.timeout} seconds")
                        return
                        
                    # Submit pending operations up to concurrency limit
                    while pending_ops and len(active_ops) < job.max_concurrency:
                        i, op = pending_ops.pop(0)
                        op_id = op.get('id') or f"{job_id}_op_{i}"
                        
                        # Submit operation
                        future = executor.submit(
                            self._execute_operation,
                            api_gateway=api_gateway,
                            plugin_name=job.plugin_name,
                            op_id=op_id,
                            operation=op
                        )
                        
                        futures[future] = (op_id, op)
                        active_ops.add(op_id)
                        
                        # Update operation status
                        job._operation_status[op_id] = 'running'
                        
                    # Check completed operations
                    done_futures = [f for f in futures if f.done()]
                    for future in done_futures:
                        op_id, op = futures[future]
                        active_ops.remove(op_id)
                        
                        try:
                            result = future.result()
                            
                            # Check if operation succeeded
                            if result.get('success', False):
                                # Operation succeeded
                                job._operation_status[op_id] = 'completed'
                                job._operation_results[op_id] = result
                                completed_ops.append((op_id, op))
                                job.completed_operations += 1
                            else:
                                # Operation failed
                                retries = job._operation_retries.get(op_id, 0)
                                
                                if retries < job.max_retries:
                                    # Retry the operation
                                    job._operation_retries[op_id] = retries + 1
                                    job._operation_status[op_id] = 'retrying'
                                    time.sleep(job.retry_delay)
                                    
                                    # Add back to pending ops
                                    pending_ops.append((i, op))
                                else:
                                    # Max retries reached, mark as failed
                                    error = result.get('error', 'Unknown error')
                                    job._operation_status[op_id] = 'failed'
                                    job._operation_errors[op_id] = error
                                    failed_ops.append((op_id, op))
                                    job.failed_operations += 1
                            
                        except Exception as e:
                            # Execution exception
                            error = str(e)
                            retries = job._operation_retries.get(op_id, 0)
                            
                            if retries < job.max_retries:
                                # Retry the operation
                                job._operation_retries[op_id] = retries + 1
                                job._operation_status[op_id] = 'retrying'
                                time.sleep(job.retry_delay)
                                
                                # Add back to pending ops
                                pending_ops.append((i, op))
                            else:
                                # Max retries reached, mark as failed
                                job._operation_status[op_id] = 'failed'
                                job._operation_errors[op_id] = error
                                failed_ops.append((op_id, op))
                                job.failed_operations += 1
                        
                        # Remove from futures
                        del futures[future]
                        
                    # Update job progress
                    total_ops = len(job.operations)
                    completed = job.completed_operations + job.failed_operations
                    job.progress = int((completed / total_ops) * 100) if total_ops > 0 else 0
                    job.updated_at = time.time()
                    
                    # Sleep briefly to avoid tight loop
                    time.sleep(0.1)
            
            # All operations completed
            job.end_time = time.time()
            job.updated_at = time.time()
            
            # Check if all operations succeeded
            if job.failed_operations == 0:
                job.status = 'completed'
                job.progress = 100
                logger.info(f"Batch job {job_id} completed successfully")
            else:
                # Some operations failed
                job.status = 'failed'
                job.error = f"{job.failed_operations} operations failed"
                logger.warning(f"Batch job {job_id} completed with {job.failed_operations} failed operations")
                
            # Collect all results
            job.results = []
            for i, op in enumerate(job.operations):
                op_id = op.get('id') or f"{job_id}_op_{i}"
                result = {
                    'id': op_id,
                    'status': job._operation_status.get(op_id, 'unknown')
                }
                
                if op_id in job._operation_results:
                    result['data'] = job._operation_results[op_id]
                    
                if op_id in job._operation_errors:
                    result['error'] = job._operation_errors[op_id]
                    
                job.results.append(result)
                
            # Remove from active jobs
            with self._lock:
                if job_id in self.active_jobs:
                    self.active_jobs.remove(job_id)
                    
            # Call handlers
            self._call_job_handlers(job)
            
        except Exception as e:
            logger.error(f"Error executing batch job {job_id}: {e}")
            self._handle_job_failure(job, str(e))
    
    def _execute_operation(self, api_gateway, plugin_name: str, op_id: str, operation: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a single operation in a batch.
        
        Args:
            api_gateway: API Gateway instance
            plugin_name: Name of the plugin to use
            op_id: Operation ID
            operation: Operation configuration dictionary
            
        Returns:
            Dictionary with operation results
        """
        try:
            # Extract operation details
            operation_name = operation.get('operation')
            parameters = operation.get('parameters', {})
            
            if not operation_name:
                raise ValueError("Operation name not specified")
                
            logger.info(f"Executing operation {op_id}: {plugin_name}/{operation_name}")
            
            # Execute the operation
            result = api_gateway.execute_operation(
                plugin_name=plugin_name,
                operation=operation_name,
                **parameters
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing operation {op_id}: {e}")
            return {
                'success': False,
                'error': str(e),
                'op_id': op_id
            }
    
    def _handle_job_failure(self, job: BatchJob, error: str):
        """
        Handle a batch job failure.
        
        Args:
            job: The job that failed
            error: Error message
        """
        # Update job state
        job.status = 'failed'
        job.end_time = time.time()
        job.updated_at = time.time()
        job.error = error
        
        # Remove from active jobs
        with self._lock:
            if job.job_id in self.active_jobs:
                self.active_jobs.remove(job.job_id)
                
        logger.error(f"Batch job {job.job_id} failed: {error}")
        
        # Call handlers
        self._call_job_handlers(job)
    
    def _handle_job_cancellation(self, job: BatchJob):
        """
        Handle a batch job cancellation.
        
        Args:
            job: The job that was cancelled
        """
        # Update job state
        job.status = 'cancelled'
        job.end_time = time.time()
        job.updated_at = time.time()
        
        # Remove from active jobs
        with self._lock:
            if job.job_id in self.active_jobs:
                self.active_jobs.remove(job.job_id)
                
        logger.info(f"Batch job {job.job_id} cancelled")
        
        # Call handlers
        self._call_job_handlers(job)
    
    def _call_job_handlers(self, job: BatchJob):
        """
        Call handlers for a job.
        
        Args:
            job: The job to call handlers for
        """
        if job.job_id in self.handlers:
            # Create job info for handlers
            job_info = self.get_job(job.job_id)
            
            for handler in self.handlers[job.job_id]:
                try:
                    handler(job_info)
                except Exception as e:
                    logger.error(f"Error in batch job handler: {e}")
                    
    def cleanup_completed_jobs(self, max_age: int = 86400) -> int:
        """
        Clean up completed jobs that are older than max_age.
        
        Args:
            max_age: Maximum age in seconds for completed jobs
            
        Returns:
            Number of jobs cleaned up
        """
        cleaned_up = 0
        current_time = time.time()
        
        with self._lock:
            jobs_to_remove = []
            
            for job_id, job in self.jobs.items():
                if job.status in ['completed', 'failed', 'cancelled']:
                    if job.end_time and (current_time - job.end_time) > max_age:
                        jobs_to_remove.append(job_id)
                        
            for job_id in jobs_to_remove:
                del self.jobs[job_id]
                
                if job_id in self.handlers:
                    del self.handlers[job_id]
                    
                if job_id in self.job_queues:
                    del self.job_queues[job_id]
                    
                cleaned_up += 1
                
        logger.info(f"Cleaned up {cleaned_up} completed jobs")
        return cleaned_up