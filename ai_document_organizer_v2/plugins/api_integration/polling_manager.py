"""
Polling Manager for External API Integration Framework.

This module provides polling capabilities for services that don't support
webhooks, allowing for periodic checking of API resources for changes.
"""

import logging
import threading
import time
import uuid
import json
from typing import Any, Dict, List, Optional, Union, Callable
from datetime import datetime, timedelta
import queue


logger = logging.getLogger(__name__)


class PollingJob:
    """
    Represents a polling job configuration.
    
    A polling job periodically polls an API resource and invokes
    registered handlers when changes are detected.
    """
    
    def __init__(self, 
                job_id: str,
                api_name: str,
                plugin_name: str,
                operation: str,
                parameters: Dict[str, Any],
                interval: int,
                compare_func: Optional[Callable] = None,
                enabled: bool = True,
                description: Optional[str] = None):
        """
        Initialize a polling job.
        
        Args:
            job_id: Unique identifier for the job
            api_name: Name of the API to poll
            plugin_name: Name of the plugin to use for polling
            operation: Name of the operation to execute
            parameters: Parameters for the operation
            interval: Polling interval in seconds
            compare_func: Optional function to compare results and detect changes
            enabled: Whether the job is enabled
            description: Optional description of the job
        """
        self.job_id = job_id
        self.api_name = api_name
        self.plugin_name = plugin_name
        self.operation = operation
        self.parameters = parameters
        self.interval = interval
        self.compare_func = compare_func
        self.enabled = enabled
        self.description = description
        
        # Job state
        self.last_run = None
        self.last_result = None
        self.last_error = None
        self.next_run = time.time() + interval
        self.run_count = 0
        self.error_count = 0
        self.success_count = 0
        self.created_at = time.time()
        self.updated_at = time.time()
        
    def update_next_run(self):
        """Update the next run time based on the interval."""
        self.next_run = time.time() + self.interval
        
    def __str__(self):
        """Return a string representation of the job."""
        return f"PollingJob({self.job_id}, {self.api_name}, {self.operation}, interval={self.interval}s)"


class PollingManager:
    """
    Manages polling jobs for API resources.
    
    This class provides functionality to:
    - Create and manage polling jobs
    - Execute polling jobs on a schedule
    - Detect changes in API resources
    - Invoke handlers when changes are detected
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the Polling Manager.
        
        Args:
            config: Optional configuration dictionary for the manager
        """
        self.config = config or {}
        
        # Polling settings
        self.min_interval = self.config.get('min_interval', 60)  # Minimum allowed interval in seconds
        self.max_concurrent_jobs = self.config.get('max_concurrent_jobs', 10)
        
        # Job registry
        self.jobs = {}  # type: Dict[str, PollingJob]
        self.handlers = {}  # type: Dict[str, List[Callable]]
        
        # Event queue for asynchronous processing
        self.event_queue = queue.Queue()
        
        # Thread management
        self.poll_thread = None
        self.processing_thread = None
        self.is_running = False
        self.should_run = False
        
        # Thread synchronization
        self._lock = threading.RLock()
        
        logger.info("Polling Manager initialized")
    
    def start(self) -> bool:
        """
        Start the polling manager.
        
        Returns:
            True if the polling manager was started successfully, False otherwise
        """
        if self.is_running:
            logger.warning("Polling Manager is already running")
            return True
            
        try:
            # Start polling thread
            self.should_run = True
            self.poll_thread = threading.Thread(target=self._polling_loop)
            self.poll_thread.daemon = True
            self.poll_thread.start()
            
            # Start event processing thread
            self.processing_thread = threading.Thread(target=self._process_events)
            self.processing_thread.daemon = True
            self.processing_thread.start()
            
            self.is_running = True
            logger.info("Polling Manager started")
            return True
            
        except Exception as e:
            logger.error(f"Error starting Polling Manager: {e}")
            return False
    
    def stop(self) -> bool:
        """
        Stop the polling manager.
        
        Returns:
            True if the polling manager was stopped successfully, False otherwise
        """
        if not self.is_running:
            logger.warning("Polling Manager is not running")
            return True
            
        try:
            # Signal threads to stop
            self.should_run = False
            
            # Wait for threads to stop
            if self.poll_thread:
                self.poll_thread.join(timeout=2.0)
                
            if self.processing_thread:
                self.processing_thread.join(timeout=2.0)
                
            self.is_running = False
            logger.info("Polling Manager stopped")
            return True
            
        except Exception as e:
            logger.error(f"Error stopping Polling Manager: {e}")
            return False
    
    def create_job(self, 
                  api_name: str,
                  plugin_name: str,
                  operation: str,
                  parameters: Dict[str, Any],
                  interval: int,
                  compare_func: Optional[Callable] = None,
                  job_id: Optional[str] = None,
                  enabled: bool = True,
                  description: Optional[str] = None) -> str:
        """
        Create a new polling job.
        
        Args:
            api_name: Name of the API to poll
            plugin_name: Name of the plugin to use for polling
            operation: Name of the operation to execute
            parameters: Parameters for the operation
            interval: Polling interval in seconds
            compare_func: Optional function to compare results and detect changes
            job_id: Optional unique identifier for the job
            enabled: Whether the job should be enabled initially
            description: Optional description of the job
            
        Returns:
            Job ID of the created job
        """
        # Validate interval
        if interval < self.min_interval:
            logger.warning(f"Requested interval {interval}s is less than minimum {self.min_interval}s, using minimum")
            interval = self.min_interval
            
        # Generate job ID if not provided
        if not job_id:
            job_id = str(uuid.uuid4())
            
        # Create the job
        with self._lock:
            if job_id in self.jobs:
                logger.warning(f"Job ID {job_id} already exists, overwriting")
                
            job = PollingJob(
                job_id=job_id,
                api_name=api_name,
                plugin_name=plugin_name,
                operation=operation,
                parameters=parameters,
                interval=interval,
                compare_func=compare_func,
                enabled=enabled,
                description=description
            )
            
            self.jobs[job_id] = job
            
            # Initialize handlers for this job
            if job_id not in self.handlers:
                self.handlers[job_id] = []
                
            logger.info(f"Created polling job {job_id} for {api_name}/{operation} with interval {interval}s")
            return job_id
    
    def delete_job(self, job_id: str) -> bool:
        """
        Delete a polling job.
        
        Args:
            job_id: ID of the job to delete
            
        Returns:
            True if the job was deleted successfully, False otherwise
        """
        with self._lock:
            if job_id not in self.jobs:
                logger.warning(f"Job {job_id} does not exist")
                return False
                
            # Delete the job
            del self.jobs[job_id]
            
            # Delete handlers for this job
            if job_id in self.handlers:
                del self.handlers[job_id]
                
            logger.info(f"Deleted polling job {job_id}")
            return True
    
    def update_job(self, 
                  job_id: str,
                  parameters: Optional[Dict[str, Any]] = None,
                  interval: Optional[int] = None,
                  enabled: Optional[bool] = None,
                  description: Optional[str] = None) -> bool:
        """
        Update a polling job.
        
        Args:
            job_id: ID of the job to update
            parameters: Optional updated parameters for the operation
            interval: Optional updated polling interval
            enabled: Optional updated enabled status
            description: Optional updated description
            
        Returns:
            True if the job was updated successfully, False otherwise
        """
        with self._lock:
            if job_id not in self.jobs:
                logger.warning(f"Job {job_id} does not exist")
                return False
                
            job = self.jobs[job_id]
            
            # Update parameters
            if parameters is not None:
                job.parameters = parameters
                
            # Update interval
            if interval is not None:
                if interval < self.min_interval:
                    logger.warning(f"Requested interval {interval}s is less than minimum {self.min_interval}s, using minimum")
                    interval = self.min_interval
                job.interval = interval
                job.update_next_run()
                
            # Update enabled status
            if enabled is not None:
                job.enabled = enabled
                
            # Update description
            if description is not None:
                job.description = description
                
            # Update timestamp
            job.updated_at = time.time()
            
            logger.info(f"Updated polling job {job_id}")
            return True
    
    def register_job_handler(self, job_id: str, handler: Callable) -> bool:
        """
        Register a handler function for a polling job.
        
        The handler will be called with event data when changes are detected.
        
        Args:
            job_id: ID of the job
            handler: Function to call when changes are detected
            
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
        Unregister a handler function for a polling job.
        
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
    
    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a polling job.
        
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
            'operation': job.operation,
            'parameters': job.parameters,
            'interval': job.interval,
            'enabled': job.enabled,
            'description': job.description,
            'last_run': job.last_run,
            'next_run': job.next_run,
            'run_count': job.run_count,
            'error_count': job.error_count,
            'success_count': job.success_count,
            'handler_count': len(self.handlers.get(job_id, [])),
            'created_at': job.created_at,
            'updated_at': job.updated_at
        }
        
        # Add human-readable times
        if job.last_run:
            job_info['last_run_time'] = datetime.fromtimestamp(job.last_run).strftime('%Y-%m-%d %H:%M:%S')
            
        if job.next_run:
            job_info['next_run_time'] = datetime.fromtimestamp(job.next_run).strftime('%Y-%m-%d %H:%M:%S')
            
        # Add last error if available
        if job.last_error:
            job_info['last_error'] = job.last_error
            
        return job_info
    
    def get_all_jobs(self) -> List[Dict[str, Any]]:
        """
        Get information about all polling jobs.
        
        Returns:
            List of dictionaries with job information
        """
        return [self.get_job(job_id) for job_id in self.jobs]
    
    def _polling_loop(self):
        """Main polling loop to execute jobs on schedule."""
        while self.should_run:
            try:
                # Sleep for a short time to avoid tight loop
                time.sleep(1.0)
                
                # Get current time
                current_time = time.time()
                
                # Find jobs that are due to run
                jobs_to_run = []
                with self._lock:
                    for job_id, job in self.jobs.items():
                        if job.enabled and job.next_run <= current_time:
                            jobs_to_run.append(job)
                            
                            # Update next run time
                            job.update_next_run()
                
                # Limit concurrent jobs
                if len(jobs_to_run) > self.max_concurrent_jobs:
                    logger.warning(f"Limiting concurrent jobs to {self.max_concurrent_jobs}")
                    jobs_to_run = jobs_to_run[:self.max_concurrent_jobs]
                
                # Execute jobs
                for job in jobs_to_run:
                    self._execute_job(job)
                    
            except Exception as e:
                logger.error(f"Error in polling loop: {e}")
                time.sleep(5.0)  # Longer sleep on error to avoid tight loop
    
    def _execute_job(self, job: PollingJob):
        """
        Execute a polling job.
        
        Args:
            job: Job to execute
        """
        # Create event ID for this execution
        event_id = str(uuid.uuid4())
        
        try:
            # Update job state
            job.last_run = time.time()
            job.run_count += 1
            
            # Get API gateway
            api_gateway = self.config.get('api_gateway')
            if not api_gateway:
                raise ValueError("API Gateway not configured")
                
            # Execute operation
            logger.info(f"Executing polling job {job.job_id}: {job.plugin_name}/{job.operation}")
            result = api_gateway.execute_operation(
                plugin_name=job.plugin_name,
                operation=job.operation,
                **job.parameters
            )
            
            # Check for success
            if not result.get('success', False):
                error_msg = result.get('error', 'Unknown error')
                logger.warning(f"Polling job {job.job_id} failed: {error_msg}")
                job.error_count += 1
                job.last_error = error_msg
                return
                
            # Update success count
            job.success_count += 1
            
            # Check for changes
            has_changed = False
            change_details = None
            
            if job.last_result is None:
                # First run, always consider it a change
                has_changed = True
                change_details = "Initial poll"
            elif job.compare_func:
                # Use custom comparison function
                try:
                    comparison_result = job.compare_func(job.last_result, result)
                    if isinstance(comparison_result, tuple) and len(comparison_result) == 2:
                        has_changed, change_details = comparison_result
                    else:
                        has_changed = bool(comparison_result)
                        change_details = "Custom comparison detected change"
                except Exception as e:
                    logger.error(f"Error in custom comparison function for job {job.job_id}: {e}")
                    has_changed = True  # Assume change on error
                    change_details = f"Error in comparison: {str(e)}"
            else:
                # Use default comparison (simple equality)
                prev_data = job.last_result.get('data') if job.last_result else None
                curr_data = result.get('data')
                
                if prev_data != curr_data:
                    has_changed = True
                    change_details = "Data changed"
            
            # Store this result for future comparisons
            job.last_result = result
            
            # Process changes if detected
            if has_changed:
                logger.info(f"Change detected in polling job {job.job_id}: {change_details}")
                
                # Create event data
                event_data = {
                    'event_id': event_id,
                    'job_id': job.job_id,
                    'api_name': job.api_name,
                    'plugin_name': job.plugin_name,
                    'operation': job.operation,
                    'parameters': job.parameters,
                    'timestamp': time.time(),
                    'result': result,
                    'change_details': change_details
                }
                
                # Queue event for processing
                self.event_queue.put(event_data)
                
        except Exception as e:
            logger.error(f"Error executing polling job {job.job_id}: {e}")
            job.error_count += 1
            job.last_error = str(e)
    
    def _process_events(self):
        """Process polling events from the queue."""
        while self.should_run:
            try:
                # Get event from queue with timeout to allow thread to exit
                try:
                    event = self.event_queue.get(timeout=1.0)
                except queue.Empty:
                    continue
                    
                # Get job ID from event
                job_id = event.get('job_id')
                if not job_id or job_id not in self.jobs:
                    logger.warning(f"Invalid job ID in event: {job_id}")
                    continue
                    
                # Process the event with registered handlers
                if job_id in self.handlers:
                    for handler in self.handlers[job_id]:
                        try:
                            handler(event)
                        except Exception as e:
                            logger.error(f"Error in polling job handler: {e}")
                            
                # Mark event as processed
                self.event_queue.task_done()
                
            except Exception as e:
                logger.error(f"Error processing polling events: {e}")
                time.sleep(1.0)  # Avoid tight loop in case of errors
    
    def force_execute_job(self, job_id: str) -> Dict[str, Any]:
        """
        Force immediate execution of a polling job.
        
        Args:
            job_id: ID of the job to execute
            
        Returns:
            Dictionary with execution results
        """
        if job_id not in self.jobs:
            return {
                'success': False,
                'error': f"Job {job_id} does not exist"
            }
            
        job = self.jobs[job_id]
        
        try:
            # Update job state
            job.last_run = time.time()
            job.run_count += 1
            
            # Get API gateway
            api_gateway = self.config.get('api_gateway')
            if not api_gateway:
                raise ValueError("API Gateway not configured")
                
            # Execute operation
            logger.info(f"Force executing polling job {job.job_id}: {job.plugin_name}/{job.operation}")
            result = api_gateway.execute_operation(
                plugin_name=job.plugin_name,
                operation=job.operation,
                **job.parameters
            )
            
            # Check for success
            if not result.get('success', False):
                error_msg = result.get('error', 'Unknown error')
                logger.warning(f"Polling job {job.job_id} failed: {error_msg}")
                job.error_count += 1
                job.last_error = error_msg
                return {
                    'success': False,
                    'error': error_msg,
                    'job_id': job_id
                }
                
            # Update success count
            job.success_count += 1
            
            # Store this result for future comparisons
            previous_result = job.last_result
            job.last_result = result
            
            return {
                'success': True,
                'job_id': job_id,
                'result': result,
                'previous_result': previous_result
            }
            
        except Exception as e:
            logger.error(f"Error force executing polling job {job.job_id}: {e}")
            job.error_count += 1
            job.last_error = str(e)
            return {
                'success': False,
                'error': str(e),
                'job_id': job_id
            }