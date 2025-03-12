"""
Task Registry for the Batch Processing Plugin.

This module defines the available task functions that can be used with the
batch processing plugin. Each task is registered with a unique name.
"""

import logging
import time
from typing import Any, Dict, List, Callable, Optional


logger = logging.getLogger(__name__)


# Dictionary to store registered tasks
_task_registry = {}


def register_task(name: str) -> Callable:
    """
    Decorator to register a task function.
    
    Args:
        name: Unique name for the task
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        if name in _task_registry:
            logger.warning(f"Task '{name}' is already registered. Overwriting.")
        _task_registry[name] = func
        return func
    return decorator


def get_task(name: str) -> Optional[Callable]:
    """
    Get a task function by name.
    
    Args:
        name: Name of the task
        
    Returns:
        Task function or None if not found
    """
    return _task_registry.get(name)


def get_all_tasks() -> Dict[str, Callable]:
    """
    Get all registered tasks.
    
    Returns:
        Dictionary mapping task names to functions
    """
    return _task_registry.copy()


def clear_tasks() -> None:
    """Clear all registered tasks."""
    _task_registry.clear()


# Example task functions

@register_task("process_document")
def process_document(document_id: str, 
                    output_format: str = "json", 
                    use_ocr: bool = False) -> Dict[str, Any]:
    """
    Process a document and extract its content.
    
    Args:
        document_id: ID of the document to process
        output_format: Format for the output (json, text, html)
        use_ocr: Whether to use OCR for image-based content
        
    Returns:
        Dictionary with processing results
    """
    # Simulate processing time
    time.sleep(2)
    
    logger.info(f"Processing document {document_id} with format {output_format} (OCR: {use_ocr})")
    
    # Simulate document processing
    return {
        "document_id": document_id,
        "format": output_format,
        "ocr_used": use_ocr,
        "word_count": 1250,
        "pages": 5,
        "title": f"Document {document_id}",
        "summary": f"This is a summary of document {document_id}"
    }


@register_task("analyze_document")
def analyze_document(document_id: str, 
                    analysis_type: str = "basic",
                    language: str = "en") -> Dict[str, Any]:
    """
    Analyze a document and extract insights.
    
    Args:
        document_id: ID of the document to analyze
        analysis_type: Type of analysis (basic, detailed, sentiment)
        language: Document language code
        
    Returns:
        Dictionary with analysis results
    """
    # Simulate analysis time
    time.sleep(3)
    
    logger.info(f"Analyzing document {document_id} with {analysis_type} analysis ({language})")
    
    # Simulate document analysis
    return {
        "document_id": document_id,
        "analysis_type": analysis_type,
        "language": language,
        "sentiment": 0.75,
        "topics": ["business", "technology", "finance"],
        "entities": ["Google", "Microsoft", "Apple"],
        "summary": f"Analysis summary for document {document_id}"
    }


@register_task("convert_document")
def convert_document(document_id: str, 
                    source_format: str,
                    target_format: str) -> Dict[str, Any]:
    """
    Convert a document from one format to another.
    
    Args:
        document_id: ID of the document to convert
        source_format: Source document format
        target_format: Target document format
        
    Returns:
        Dictionary with conversion results
    """
    # Simulate conversion time
    time.sleep(2.5)
    
    logger.info(f"Converting document {document_id} from {source_format} to {target_format}")
    
    # Simulate document conversion
    return {
        "document_id": document_id,
        "source_format": source_format,
        "target_format": target_format,
        "success": True,
        "conversion_time": 2.5,
        "output_path": f"/converted/{document_id}.{target_format}"
    }


@register_task("batch_categorize")
def batch_categorize(document_ids: List[str], 
                    taxonomy_id: str = "default") -> Dict[str, Any]:
    """
    Categorize a batch of documents.
    
    Args:
        document_ids: List of document IDs to categorize
        taxonomy_id: ID of the taxonomy to use
        
    Returns:
        Dictionary with categorization results
    """
    # Simulate categorization time (0.5 seconds per document)
    time.sleep(0.5 * len(document_ids))
    
    logger.info(f"Categorizing {len(document_ids)} documents with taxonomy {taxonomy_id}")
    
    # Simulate document categorization
    results = {}
    for doc_id in document_ids:
        results[doc_id] = {
            "categories": ["finance", "reports", "quarterly"],
            "confidence": 0.85,
            "taxonomy_id": taxonomy_id
        }
    
    return {
        "document_count": len(document_ids),
        "taxonomy_id": taxonomy_id,
        "categorization_results": results
    }


@register_task("cleanup_temporary_files")
def cleanup_temporary_files(older_than_days: int = 7, 
                          directory: str = "/tmp") -> Dict[str, Any]:
    """
    Clean up temporary files.
    
    Args:
        older_than_days: Delete files older than this many days
        directory: Directory to clean up
        
    Returns:
        Dictionary with cleanup results
    """
    # Simulate cleanup time
    time.sleep(1)
    
    logger.info(f"Cleaning up files older than {older_than_days} days in {directory}")
    
    # Simulate file cleanup
    files_count = 15
    deleted_count = 8
    
    return {
        "directory": directory,
        "older_than_days": older_than_days,
        "files_found": files_count,
        "files_deleted": deleted_count,
        "files_skipped": files_count - deleted_count,
        "total_space_freed": "15.7 MB"
    }


@register_task("long_running_task")
def long_running_task(iterations: int = 10, 
                     delay_per_iteration: float = 1.0) -> Dict[str, Any]:
    """
    A long-running task for testing timeout and cancellation.
    
    Args:
        iterations: Number of iterations to run
        delay_per_iteration: Delay in seconds between iterations
        
    Returns:
        Dictionary with task results
    """
    results = []
    
    for i in range(iterations):
        # Simulate work
        logger.info(f"Long-running task iteration {i+1}/{iterations}")
        time.sleep(delay_per_iteration)
        results.append(f"Result from iteration {i+1}")
    
    return {
        "iterations_completed": iterations,
        "total_time": iterations * delay_per_iteration,
        "results": results
    }


# Add a method to update the _get_task_functions method of the BatchProcessorPlugin
def register_with_plugin(plugin):
    """
    Register all tasks with the plugin.
    
    Args:
        plugin: BatchProcessorPlugin instance
    """
    # Monkey patch the plugin's _get_task_functions method
    original_get_task_functions = plugin._get_task_functions
    
    def patched_get_task_functions(*args, **kwargs):
        # Get any tasks defined in the original method
        tasks = original_get_task_functions(*args, **kwargs)
        # Add our registered tasks
        tasks.update(_task_registry)
        return tasks
    
    plugin._get_task_functions = patched_get_task_functions
    
    logger.info(f"Registered {len(_task_registry)} tasks with the batch processing plugin")