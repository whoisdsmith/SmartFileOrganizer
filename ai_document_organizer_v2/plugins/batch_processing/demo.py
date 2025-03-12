"""
Demonstration of the Batch Processing Plugin.

This script shows how to use the Batch Processing Plugin for
asynchronous job execution and job group management.
"""

import logging
import time
from typing import Dict, Any

from ai_document_organizer_v2.plugins.batch_processing.batch_plugin import BatchProcessorPlugin
from ai_document_organizer_v2.plugins.batch_processing.models.job import JobPriority
from ai_document_organizer_v2.plugins.batch_processing.task_registry import (
    register_with_plugin, get_all_tasks
)


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_simple_job_demo(plugin: BatchProcessorPlugin) -> None:
    """
    Demonstrate submitting and running a simple job.
    
    Args:
        plugin: BatchProcessorPlugin instance
    """
    logger.info("=== Simple Job Demo ===")
    
    # Get task functions
    tasks = get_all_tasks()
    
    # Create and submit a job
    job_id = plugin.create_and_submit_job(
        task_name="process_document",
        task_func=tasks["process_document"],
        task_args={
            "document_id": "DOC-001",
            "output_format": "json",
            "use_ocr": True
        },
        priority=JobPriority.HIGH
    )
    
    if job_id:
        logger.info(f"Submitted job {job_id}, waiting for completion...")
        
        # Wait for the job to complete
        if plugin.wait_for_job(job_id, timeout=10):
            # Get the job result
            result = plugin.get_job_result(job_id)
            logger.info(f"Job completed successfully with result: {result}")
        else:
            error = plugin.get_job_error(job_id)
            logger.error(f"Job failed or timed out: {error}")
    else:
        logger.error("Failed to submit job")


def run_multiple_jobs_demo(plugin: BatchProcessorPlugin) -> None:
    """
    Demonstrate submitting and running multiple jobs.
    
    Args:
        plugin: BatchProcessorPlugin instance
    """
    logger.info("=== Multiple Jobs Demo ===")
    
    # Get task functions
    tasks = get_all_tasks()
    
    # Create and submit multiple jobs
    job_ids = []
    
    # Job 1: Process document
    job_id1 = plugin.create_and_submit_job(
        task_name="process_document",
        task_func=tasks["process_document"],
        task_args={
            "document_id": "DOC-002",
            "output_format": "text",
            "use_ocr": False
        }
    )
    job_ids.append(job_id1)
    
    # Job 2: Analyze document
    job_id2 = plugin.create_and_submit_job(
        task_name="analyze_document",
        task_func=tasks["analyze_document"],
        task_args={
            "document_id": "DOC-003",
            "analysis_type": "detailed",
            "language": "en"
        }
    )
    job_ids.append(job_id2)
    
    # Job 3: Convert document
    job_id3 = plugin.create_and_submit_job(
        task_name="convert_document",
        task_func=tasks["convert_document"],
        task_args={
            "document_id": "DOC-004",
            "source_format": "docx",
            "target_format": "pdf"
        }
    )
    job_ids.append(job_id3)
    
    # Wait for all jobs to complete
    logger.info(f"Submitted {len(job_ids)} jobs, waiting for completion...")
    results = plugin.wait_for_jobs(job_ids, timeout=20)
    
    # Check results
    for job_id, success in results.items():
        if success:
            result = plugin.get_job_result(job_id)
            logger.info(f"Job {job_id} completed successfully with result: {result}")
        else:
            error = plugin.get_job_error(job_id)
            status = plugin.get_job_status(job_id)
            logger.error(f"Job {job_id} failed or timed out: {status} - {error}")


def run_job_group_demo(plugin: BatchProcessorPlugin) -> None:
    """
    Demonstrate creating and running a job group.
    
    Args:
        plugin: BatchProcessorPlugin instance
    """
    logger.info("=== Job Group Demo ===")
    
    # Get task functions
    tasks = get_all_tasks()
    
    # Create a job group
    group_id = plugin.create_job_group(
        name="Document Processing Group",
        description="A group of document processing jobs",
        sequential=True,  # Process jobs one after another
        cancel_on_failure=True  # Cancel remaining jobs if one fails
    )
    
    # Create jobs in the group
    job_ids = []
    
    # Job 1: Process document
    job_id1 = plugin.create_job(
        task_name="process_document",
        task_func=tasks["process_document"],
        task_args={
            "document_id": "DOC-005",
            "output_format": "json",
            "use_ocr": True
        }
    )
    plugin.add_job_to_group(job_id1, group_id)
    job_ids.append(job_id1)
    
    # Job 2: Analyze document (depends on Job 1)
    job_id2 = plugin.create_job(
        task_name="analyze_document",
        task_func=tasks["analyze_document"],
        task_args={
            "document_id": "DOC-005",  # Same document
            "analysis_type": "sentiment",
            "language": "en"
        },
        dependencies=[job_id1]  # This job depends on the first job
    )
    plugin.add_job_to_group(job_id2, group_id)
    job_ids.append(job_id2)
    
    # Job 3: Convert document (depends on Job 2)
    job_id3 = plugin.create_job(
        task_name="convert_document",
        task_func=tasks["convert_document"],
        task_args={
            "document_id": "DOC-005",  # Same document
            "source_format": "json",
            "target_format": "pdf"
        },
        dependencies=[job_id2]  # This job depends on the second job
    )
    plugin.add_job_to_group(job_id3, group_id)
    job_ids.append(job_id3)
    
    # Submit all jobs
    for job_id in job_ids:
        plugin.submit_job(job_id)
    
    # Wait for the group to complete
    logger.info(f"Submitted job group {group_id} with {len(job_ids)} jobs, waiting for completion...")
    success = plugin.wait_for_job_group(group_id, timeout=30)
    
    if success:
        logger.info(f"Job group completed successfully")
        # Get results for all jobs
        for job_id in job_ids:
            result = plugin.get_job_result(job_id)
            logger.info(f"Job {job_id} result: {result}")
    else:
        logger.error("Job group failed or timed out")
        # Get status for all jobs
        for job_id in job_ids:
            status = plugin.get_job_status(job_id)
            error = plugin.get_job_error(job_id)
            logger.info(f"Job {job_id} status: {status}, error: {error}")


def run_batch_categorization_demo(plugin: BatchProcessorPlugin) -> None:
    """
    Demonstrate batch document categorization.
    
    Args:
        plugin: BatchProcessorPlugin instance
    """
    logger.info("=== Batch Categorization Demo ===")
    
    # Get task functions
    tasks = get_all_tasks()
    
    # Create a batch categorization job
    job_id = plugin.create_and_submit_job(
        task_name="batch_categorize",
        task_func=tasks["batch_categorize"],
        task_args={
            "document_ids": [f"DOC-{i:03d}" for i in range(10, 20)],
            "taxonomy_id": "finance-taxonomy"
        },
        priority=JobPriority.NORMAL
    )
    
    if job_id:
        logger.info(f"Submitted batch categorization job {job_id}, waiting for completion...")
        
        # Wait for the job to complete
        if plugin.wait_for_job(job_id, timeout=15):
            # Get the job result
            result = plugin.get_job_result(job_id)
            logger.info(f"Batch categorization completed successfully")
            logger.info(f"Categorized {result['document_count']} documents using taxonomy {result['taxonomy_id']}")
            
            # Show first 3 results
            for i, (doc_id, cat_result) in enumerate(result['categorization_results'].items()):
                if i < 3:  # Only show first 3 for brevity
                    logger.info(f"Document {doc_id}: {cat_result}")
            
            if len(result['categorization_results']) > 3:
                logger.info(f"... and {len(result['categorization_results']) - 3} more results")
        else:
            error = plugin.get_job_error(job_id)
            logger.error(f"Batch categorization failed or timed out: {error}")
    else:
        logger.error("Failed to submit batch categorization job")


def run_long_running_task_demo(plugin: BatchProcessorPlugin) -> None:
    """
    Demonstrate handling a long-running task.
    
    Args:
        plugin: BatchProcessorPlugin instance
    """
    logger.info("=== Long Running Task Demo ===")
    
    # Get task functions
    tasks = get_all_tasks()
    
    # Create a long-running task
    job_id = plugin.create_and_submit_job(
        task_name="long_running_task",
        task_func=tasks["long_running_task"],
        task_args={
            "iterations": 5,
            "delay_per_iteration": 1.0
        },
        priority=JobPriority.LOW
    )
    
    if job_id:
        logger.info(f"Submitted long-running task {job_id}")
        
        # Show periodic status updates
        for i in range(3):
            time.sleep(2)
            status = plugin.get_job_status(job_id)
            job_info = plugin.get_job(job_id)
            logger.info(f"Job status after {(i+1)*2}s: {status}, progress: {job_info.get('progress', 0)}")
        
        # Wait for the job to complete
        if plugin.wait_for_job(job_id, timeout=10):
            # Get the job result
            result = plugin.get_job_result(job_id)
            logger.info(f"Long-running task completed successfully")
            logger.info(f"Completed {result['iterations_completed']} iterations in {result['total_time']}s")
        else:
            error = plugin.get_job_error(job_id)
            logger.error(f"Long-running task failed or timed out: {error}")
    else:
        logger.error("Failed to submit long-running task")


def run_job_cancellation_demo(plugin: BatchProcessorPlugin) -> None:
    """
    Demonstrate job cancellation.
    
    Args:
        plugin: BatchProcessorPlugin instance
    """
    logger.info("=== Job Cancellation Demo ===")
    
    # Get task functions
    tasks = get_all_tasks()
    
    # Create a job
    job_id = plugin.create_and_submit_job(
        task_name="long_running_task",
        task_func=tasks["long_running_task"],
        task_args={
            "iterations": 10,
            "delay_per_iteration": 1.0
        }
    )
    
    if job_id:
        logger.info(f"Submitted job {job_id} for cancellation demo")
        
        # Wait a bit for the job to start
        time.sleep(2)
        
        # Cancel the job
        if plugin.cancel_job(job_id):
            logger.info(f"Successfully cancelled job {job_id}")
            
            # Check the job status
            status = plugin.get_job_status(job_id)
            logger.info(f"Job status after cancellation: {status}")
        else:
            logger.error(f"Failed to cancel job {job_id}")
    else:
        logger.error("Failed to submit job for cancellation demo")


def run_job_statistics_demo(plugin: BatchProcessorPlugin) -> None:
    """
    Demonstrate job statistics.
    
    Args:
        plugin: BatchProcessorPlugin instance
    """
    logger.info("=== Job Statistics Demo ===")
    
    # Get job statistics
    stats = plugin.get_job_stats()
    
    # Display statistics
    logger.info("Batch Processing Plugin Statistics:")
    for key, value in stats.items():
        logger.info(f"  {key}: {value}")
    
    # Get plugin information
    info = plugin.get_info()
    logger.info("\nPlugin information:")
    for key, value in info.items():
        logger.info(f"  {key}: {value}")


def main():
    """Main function to run the batch processing demo."""
    logger.info("Starting Batch Processing Plugin Demo")
    
    # Create and initialize the plugin
    plugin = BatchProcessorPlugin({
        "data_dir": "data/batch_processor",
        "max_workers": 3  # Limit to 3 concurrent jobs
    })
    
    # Initialize and activate the plugin
    plugin.initialize()
    plugin.activate()
    
    # Register task functions with the plugin
    register_with_plugin(plugin)
    
    # Run demos
    try:
        run_simple_job_demo(plugin)
        time.sleep(1)  # Small delay between demos
        
        run_multiple_jobs_demo(plugin)
        time.sleep(1)
        
        run_job_group_demo(plugin)
        time.sleep(1)
        
        run_batch_categorization_demo(plugin)
        time.sleep(1)
        
        run_long_running_task_demo(plugin)
        time.sleep(1)
        
        run_job_cancellation_demo(plugin)
        time.sleep(1)
        
        run_job_statistics_demo(plugin)
    
    finally:
        # Shutdown the plugin
        plugin.deactivate()
        plugin.shutdown()
    
    logger.info("Batch Processing Plugin Demo Completed")


if __name__ == "__main__":
    main()