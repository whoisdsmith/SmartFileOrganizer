"""
Tests for the Batch Processing Plugin.

This module tests the batch processing plugin functionality, including
job submission, scheduling, execution, and resource monitoring.
"""

import os
import time
import unittest
import logging
from typing import Dict, List, Any

from ai_document_organizer_v2.core.plugin_manager import PluginManager
from ai_document_organizer_v2.plugins.batch_processing import BatchProcessingPlugin
from ai_document_organizer_v2.plugins.batch_processing.models import JobStatus, JobPriority

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def example_job(x, y, sleep_time=0):
    """Example job function for testing."""
    time.sleep(sleep_time)
    return x + y

def error_job():
    """Example job that raises an error."""
    raise ValueError("Test error in job")

class TestBatchProcessingPlugin(unittest.TestCase):
    """Test cases for the Batch Processing Plugin."""
    
    def setUp(self):
        """Set up test environment."""
        self.plugin_manager = PluginManager()
        self.plugin_manager.discover_plugins()
        
        # Configure plugin with test settings
        config = {
            "use_process_pool": False,  # Use thread pool for testing
            "max_workers": 2,
            "adaptive_scaling": False,
            "monitor_resources": True,
            "scheduling_policy": "priority",
            "job_cache_dir": "tests/cache/jobs"
        }
        
        # Try to load the plugin
        self.plugin = self.plugin_manager.load_plugin("batch_processing", config)
        
        # If plugin not found through plugin manager, create directly
        if not self.plugin:
            self.plugin = BatchProcessingPlugin(config)
            self.plugin.initialize()
        
        # Start the batch processing
        self.plugin.start()
    
    def tearDown(self):
        """Clean up after tests."""
        if self.plugin:
            self.plugin.stop()
            self.plugin.shutdown()
    
    def test_plugin_initialization(self):
        """Test that the plugin initializes correctly."""
        self.assertIsNotNone(self.plugin)
        self.assertTrue(self.plugin.initialize())
    
    def test_job_submission_and_execution(self):
        """Test submitting and executing a job."""
        # Submit a simple job
        job_id = self.plugin.submit_job("test_job", example_job, 1, 2)
        self.assertIsNotNone(job_id)
        
        # Wait for job to complete
        result = self.plugin.wait_for_job(job_id, timeout=5.0)
        self.assertTrue(result)
        
        # Check job result
        job_result = self.plugin.get_job_result(job_id)
        self.assertEqual(job_result, 3)
    
    def test_job_error_handling(self):
        """Test error handling in jobs."""
        # Submit a job that will fail
        job_id = self.plugin.submit_job("error_job", error_job)
        self.assertIsNotNone(job_id)
        
        # Wait for job to complete (it will fail)
        result = self.plugin.wait_for_job(job_id, timeout=5.0)
        self.assertFalse(result)
        
        # Check job status
        status = self.plugin.get_job_status(job_id)
        self.assertEqual(status, JobStatus.FAILED.name)
        
        # Check error
        error = self.plugin.get_job_error(job_id)
        self.assertIsNotNone(error)
        self.assertIsInstance(error, ValueError)
    
    def test_job_cancellation(self):
        """Test canceling a job."""
        # Submit a job that sleeps
        job_id = self.plugin.submit_job("sleep_job", example_job, 1, 2, sleep_time=10)
        self.assertIsNotNone(job_id)
        
        # Wait a short time for job to start
        time.sleep(0.5)
        
        # Cancel the job
        result = self.plugin.cancel_job(job_id)
        self.assertTrue(result)
        
        # Check job status
        status = self.plugin.get_job_status(job_id)
        self.assertEqual(status, JobStatus.CANCELED.name)
    
    def test_job_priorities(self):
        """Test job priority scheduling."""
        # Submit a low priority job that sleeps
        job1_id = self.plugin.submit_job(
            "low_priority_job", 
            example_job, 1, 2, 
            sleep_time=0.5, 
            priority=JobPriority.LOW
        )
        
        # Submit a high priority job
        job2_id = self.plugin.submit_job(
            "high_priority_job", 
            example_job, 3, 4,
            priority=JobPriority.HIGH
        )
        
        # Wait for jobs to complete
        self.plugin.wait_for_jobs([job1_id, job2_id], timeout=5.0)
        
        # Get job info
        job1 = self.plugin.get_job(job1_id)
        job2 = self.plugin.get_job(job2_id)
        
        # Both should be completed
        self.assertEqual(job1["status"], JobStatus.COMPLETED.name)
        self.assertEqual(job2["status"], JobStatus.COMPLETED.name)
    
    def test_job_dependencies(self):
        """Test job dependencies."""
        # Submit first job
        job1_id = self.plugin.submit_job("first_job", example_job, 1, 2)
        
        # Submit second job that depends on first
        job2_id = self.plugin.submit_job(
            "dependent_job", 
            example_job, 3, 4,
            dependencies=[job1_id]
        )
        
        # Wait for jobs to complete
        self.plugin.wait_for_jobs([job1_id, job2_id], timeout=5.0)
        
        # Both should be completed
        self.assertEqual(self.plugin.get_job_status(job1_id), JobStatus.COMPLETED.name)
        self.assertEqual(self.plugin.get_job_status(job2_id), JobStatus.COMPLETED.name)
    
    def test_job_group(self):
        """Test creating a group of jobs."""
        # Create a group of jobs
        jobs = [
            (example_job, [1, 2], {}),
            (example_job, [3, 4], {}),
            (example_job, [5, 6], {})
        ]
        
        job_ids = self.plugin.create_job_group("test_group", jobs)
        self.assertEqual(len(job_ids), 3)
        
        # Wait for all jobs to complete
        result = self.plugin.wait_for_jobs(job_ids, timeout=5.0)
        self.assertTrue(result)
        
        # Check results
        results = [self.plugin.get_job_result(job_id) for job_id in job_ids]
        self.assertEqual(results, [3, 7, 11])
    
    def test_get_job_stats(self):
        """Test getting job statistics."""
        # Submit a few jobs
        job1_id = self.plugin.submit_job("stat_job1", example_job, 1, 2)
        job2_id = self.plugin.submit_job("stat_job2", example_job, 3, 4)
        
        # Wait for jobs to complete
        self.plugin.wait_for_jobs([job1_id, job2_id], timeout=5.0)
        
        # Get job stats
        stats = self.plugin.get_job_stats()
        
        # Check stats
        self.assertIn("total_jobs", stats)
        self.assertIn("completed_jobs", stats)
        self.assertGreaterEqual(stats["total_jobs"], 2)
        self.assertGreaterEqual(stats["completed_jobs"], 2)


if __name__ == '__main__':
    unittest.main()