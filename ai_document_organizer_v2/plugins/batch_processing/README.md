# Batch Processing Plugin

The Batch Processing Plugin provides asynchronous job execution capabilities for the AI Document Organizer V2.

## Features

- **Asynchronous Job Execution**: Run tasks in the background without blocking the main application.
- **Job Queue Management**: Prioritize and manage the execution of multiple jobs.
- **Job Groups**: Group related jobs and manage their execution together.
- **Retry Mechanism**: Automatically retry failed jobs with configurable retry policies.
- **Job Status Tracking**: Monitor the progress and status of submitted jobs.
- **Resource-Aware Execution**: Control the number of concurrent jobs to avoid overloading the system.

## Components

The plugin consists of the following main components:

### Core Classes

- **`Job`**: Represents a single unit of work to be executed asynchronously.
- **`JobGroup`**: Represents a group of related jobs that can be managed together.
- **`BatchProcessorPlugin`**: The main plugin class that manages the execution of jobs.

### Support Modules

- **`task_registry.py`**: Registry for task functions that can be executed by the plugin.
- **`demo.py`**: Demonstration script showing how to use the plugin.

## Job Lifecycle

1. **Creation**: Jobs are created with a task function and optional arguments.
2. **Submission**: Jobs are submitted to the queue for execution.
3. **Queuing**: Jobs wait in the queue until resources are available.
4. **Execution**: Jobs are executed by worker threads.
5. **Completion**: Jobs complete successfully or fail with an error.
6. **Retry**: Failed jobs may be retried based on their configuration.

## Job States

- **Created**: Job has been created but not submitted.
- **Queued**: Job is waiting in the queue to be executed.
- **Running**: Job is currently being executed.
- **Paused**: Job execution has been paused.
- **Waiting**: Job is waiting for its dependencies to complete.
- **Completed**: Job has completed successfully.
- **Failed**: Job has failed with an error.
- **Canceled**: Job has been canceled by the user.

## Usage Examples

### Basic Job Submission

```python
from ai_document_organizer_v2.plugins.batch_processing.batch_plugin import BatchProcessorPlugin
from ai_document_organizer_v2.plugins.batch_processing.models.job import JobPriority

# Initialize the plugin
plugin = BatchProcessorPlugin()
plugin.initialize()
plugin.activate()

# Define a task function
def my_task(param1, param2):
    # Do some work...
    return {"result": f"Processed {param1} and {param2}"}

# Create and submit a job
job_id = plugin.create_and_submit_job(
    task_name="my_task",
    task_func=my_task,
    task_args={"param1": "value1", "param2": "value2"},
    priority=JobPriority.NORMAL
)

# Wait for the job to complete
plugin.wait_for_job(job_id)

# Get the job result
result = plugin.get_job_result(job_id)
print(f"Job result: {result}")

# Shutdown the plugin
plugin.deactivate()
plugin.shutdown()
```

### Job Groups

```python
# Create a job group
group_id = plugin.create_job_group(
    name="My Job Group",
    sequential=True,  # Execute jobs sequentially
    cancel_on_failure=True  # Cancel remaining jobs if one fails
)

# Create jobs in the group
job_id1 = plugin.create_job(
    task_name="task1",
    task_func=task1_function,
    task_args={"param1": "value1"}
)
plugin.add_job_to_group(job_id1, group_id)

job_id2 = plugin.create_job(
    task_name="task2",
    task_func=task2_function,
    task_args={"param2": "value2"},
    dependencies=[job_id1]  # This job depends on job1
)
plugin.add_job_to_group(job_id2, group_id)

# Submit all jobs
plugin.submit_job(job_id1)
plugin.submit_job(job_id2)

# Wait for the group to complete
plugin.wait_for_job_group(group_id)
```

## Job Priority

Jobs can be assigned one of the following priority levels:

- **Low**: Jobs with lowest priority, executed when no higher priority jobs are available.
- **Normal**: Default priority level for most jobs.
- **High**: Higher priority jobs that are executed before normal and low priority jobs.
- **Critical**: Highest priority jobs, executed before all other jobs.

## Configuration Options

The plugin can be configured with the following options:

- **`data_dir`**: Directory for storing job data and state.
- **`max_workers`**: Maximum number of concurrent worker threads.
- **`max_queue_size`**: Maximum size of the job queue.
- **`poll_interval`**: Interval for checking job status in seconds.

## Demo

A comprehensive demonstration of the plugin's capabilities is provided in `demo.py`. Run this script to see the plugin in action.

## Integration with Other Plugins

The Batch Processing Plugin can be integrated with other plugins to enable asynchronous processing of various tasks, such as:

- Document analysis and categorization
- Media processing and transformation
- Data synchronization with cloud services
- Periodic maintenance tasks
- Long-running computations

## Error Handling

The plugin provides robust error handling capabilities:

- Jobs that fail can be automatically retried.
- Detailed error information is captured and stored.
- Dependencies between jobs ensure proper sequencing and error propagation.
- Job groups can be configured to cancel remaining jobs if one fails.

## Persistence

Job and job group state is persisted to disk to ensure that jobs are not lost in case of application restarts.