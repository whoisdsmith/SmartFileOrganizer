"""
Batch Processing Plugin for AI Document Organizer V2.
"""

from .batch_plugin import BatchProcessorPlugin
from .models.job import Job, JobStatus, JobPriority
from .models.job_group import JobGroup

__all__ = [
    "BatchProcessorPlugin",
    "Job",
    "JobStatus",
    "JobPriority",
    "JobGroup"
]