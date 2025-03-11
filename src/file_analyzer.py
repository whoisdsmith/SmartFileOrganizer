import os
import time
import psutil
from pathlib import Path
import traceback
import multiprocessing
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
import logging
import threading
import queue
import json
import uuid
from typing import Dict, List, Tuple, Optional, Union, Callable

from .file_parser import FileParser
from .ai_analyzer import AIAnalyzer
from .image_analyzer import ImageAnalyzer

logger = logging.getLogger("AIDocumentOrganizer")


class FileAnalyzer:
    """
    Class responsible for analyzing files in a directory
    """

    def __init__(self):
        self.parser = FileParser()
        self.ai_analyzer = AIAnalyzer()
        self.image_analyzer = ImageAnalyzer()

        # Supported file extensions
        self.supported_extensions = {
            '.csv': 'CSV',
            '.xlsx': 'Excel',
            '.html': 'HTML',
            '.md': 'Markdown',
            '.txt': 'Text',
            '.docx': 'Word',
            '.pdf': 'PDF',
            '.jpg': 'Image',
            '.jpeg': 'Image',
            '.png': 'Image',
            '.gif': 'Image',
            '.bmp': 'Image',
            '.tiff': 'Image',
            '.webp': 'Image'
        }

        # Default batch processing settings
        self.batch_size = 5  # Reduced from 10 to 5 to be more conservative
        # Further reduced thread pool size
        self.max_workers = min(4, (os.cpu_count() or 1))
        self.batch_delay = 10.0  # Increased from 5 to 10 seconds to wait between batches
        self.progress_callback = None  # Callback for progress updates

        # Batch processing state
        self.is_paused = False
        self.is_cancelled = False
        self.current_job_id = None
        self.job_state = {}

        # Resource monitoring
        self.resource_monitor = ResourceMonitor()

    def scan_directory(self, directory_path, batch_size=None, batch_delay=None, callback=None,
                      use_processes=True, adaptive_workers=True, job_id=None, resume=False):
        """
        Scan a directory for supported files and analyze them

        Args:
            directory_path: Path to the directory to scan
            batch_size: Number of files to process in each batch
            batch_delay: Delay in seconds between processing batches
            callback: Function to call with progress updates
            use_processes: Whether to use process pools instead of thread pools
            adaptive_workers: Whether to adapt worker count based on system resources
            job_id: Optional job ID for resuming operations
            resume: Whether to resume a previous operation

        Returns:
            List of dictionaries with file information and analysis
        """
        # Reset state for new job
        if not resume:
            self.is_paused = False
            self.is_cancelled = False

        # Generate or use job ID
        if job_id and resume and job_id in self.job_state:
            self.current_job_id = job_id
            job_data = self.job_state[job_id]
            logger.info(f"Resuming job {job_id} with {len(job_data['pending_files'])} files remaining")
        else:
            self.current_job_id = str(uuid.uuid4())
            # Initialize job state
            self.job_state[self.current_job_id] = {
                'directory': directory_path,
                'processed_files': [],
                'pending_files': [],
                'total_files': 0,
                'start_time': time.time(),
                'elapsed_time': 0,
                'completed': False
            }
            job_id = self.current_job_id

        # Set batch processing parameters
        if batch_size is not None:
            self.batch_size = batch_size
        if batch_delay is not None:
            self.batch_delay = batch_delay
        self.progress_callback = callback

        # Start resource monitoring
        self.resource_monitor.start()

        try:
            # Get all files in the directory and subdirectories
            if not resume or not self.job_state[job_id]['pending_files']:
                all_files = []
                for root, _, files in os.walk(directory_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        file_ext = os.path.splitext(file_path)[1].lower()
                        if file_ext in self.supported_extensions:
                            all_files.append((file_path, file_ext))

                self.job_state[job_id]['pending_files'] = all_files
                self.job_state[job_id]['total_files'] = len(all_files)

            # Get pending files from job state
            all_files = self.job_state[job_id]['pending_files']
            total_files = self.job_state[job_id]['total_files']
            processed_files = self.job_state[job_id]['processed_files']

            if not all_files:
                logger.info("No supported files found in the directory")
                if callback:
                    callback(0, 0, "No supported files found")
                return []

            logger.info(f"Found {len(all_files)} supported files in {directory_path}")
            if callback:
                callback(len(processed_files), total_files, f"Found {len(all_files)} files to process")

            # Process files in batches
            results = []
            processed_count = len(processed_files)

            # Add already processed files to results
            results.extend(processed_files)

            # Process remaining files in batches
            for i in range(0, len(all_files), self.batch_size):
                # Check if paused or cancelled
                if self.is_cancelled:
                    logger.info("Operation cancelled")
                    if callback:
                        callback(processed_count, total_files, "Operation cancelled")
                    break

                if self.is_paused:
                    logger.info("Operation paused")
                    if callback:
                        callback(processed_count, total_files, "Operation paused")

                    # Update job state
                    self.job_state[job_id]['pending_files'] = all_files[i:]
                    self.job_state[job_id]['processed_files'] = results
                    self.job_state[job_id]['elapsed_time'] += time.time() - self.job_state[job_id]['start_time']
                    self.job_state[job_id]['start_time'] = time.time()

                    # Stop resource monitoring
                    self.resource_monitor.stop()
                    return results

                # Get batch of files
                batch = all_files[i:i+self.batch_size]

                # Adjust worker count based on system resources if adaptive
                if adaptive_workers:
                    self.max_workers = self._get_adaptive_worker_count()

                # Process batch
                if callback:
                    callback(processed_count, total_files, f"Processing batch {i//self.batch_size + 1}/{(len(all_files)-1)//self.batch_size + 1}")

                # Use process pool or thread pool based on configuration
                if use_processes:
                    batch_results = self._process_batch_with_processes(batch)
                else:
                    batch_results = self._process_batch(batch)

                # Update results and processed count
                results.extend(batch_results)
                processed_count += len(batch_results)

                # Update job state
                self.job_state[job_id]['pending_files'] = all_files[i+self.batch_size:]
                self.job_state[job_id]['processed_files'] = results

                # Update progress
                if callback:
                    callback(processed_count, total_files, f"Processed {processed_count}/{total_files} files")

                # Delay between batches if not the last batch
                if i + self.batch_size < len(all_files) and not self.is_cancelled and not self.is_paused:
                    time.sleep(self.batch_delay)

            # Mark job as completed if not cancelled or paused
            if not self.is_cancelled and not self.is_paused:
                self.job_state[job_id]['completed'] = True
                self.job_state[job_id]['elapsed_time'] += time.time() - self.job_state[job_id]['start_time']

                # Calculate processing statistics
                elapsed_time = self.job_state[job_id]['elapsed_time']
                files_per_second = total_files / elapsed_time if elapsed_time > 0 else 0

                logger.info(f"Completed processing {total_files} files in {elapsed_time:.2f} seconds ({files_per_second:.2f} files/sec)")
                if callback:
                    callback(total_files, total_files, f"Completed processing {total_files} files")

            return results

        except Exception as e:
            logger.error(f"Error scanning directory: {str(e)}")
            logger.error(traceback.format_exc())
            if callback:
                callback(0, total_files, f"Error: {str(e)}")
            return []
        finally:
            # Stop resource monitoring
            self.resource_monitor.stop()

    def _process_batch(self, file_batch):
        """
        Process a batch of files using ThreadPoolExecutor

        Args:
            file_batch: List of (file_path, file_ext) tuples

        Returns:
            List of dictionaries with file information and analysis
        """
        results = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_file = {
                executor.submit(self._process_single_file, file_path, file_ext): (file_path, file_ext)
                for file_path, file_ext in file_batch
            }

            for future in as_completed(future_to_file):
                file_path, _ = future_to_file[future]
                try:
                    result = future.result()
                    if result:
                        results.append(result)
                except Exception as e:
                    logger.error(f"Error processing file {file_path}: {str(e)}")
                    logger.error(traceback.format_exc())

        return results

    def _process_batch_with_processes(self, file_batch):
        """
        Process a batch of files using ProcessPoolExecutor for better performance

        Args:
            file_batch: List of (file_path, file_ext) tuples

        Returns:
            List of dictionaries with file information and analysis
        """
        results = []

        # Create a queue for IPC
        result_queue = multiprocessing.Queue()

        # Define a worker function that can be pickled
        def worker_func(file_path, file_ext, queue):
            try:
                # Create new instances for each process
                parser = FileParser()
                ai_analyzer = AIAnalyzer()
                image_analyzer = ImageAnalyzer()

                # Get basic file info
                file_info = self._get_file_info(file_path, file_ext)

                # Extract text content
                try:
                    text_content = parser.extract_text(file_path, file_ext)
                    file_info['text_content'] = text_content
                except Exception as e:
                    logger.error(f"Error extracting text from {file_path}: {str(e)}")
                    file_info['text_content'] = f"Error extracting text: {str(e)}"

                # Extract metadata
                try:
                    metadata = parser.extract_metadata(file_path, file_ext)
                    file_info['metadata'] = metadata
                except Exception as e:
                    logger.error(f"Error extracting metadata from {file_path}: {str(e)}")
                    file_info['metadata'] = {'error': str(e)}

                # Analyze with AI for document files
                if file_ext.lower() not in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp']:
                    try:
                        ai_result = ai_analyzer.analyze_text(text_content)
                        file_info['ai_analysis'] = ai_result
                    except Exception as e:
                        logger.error(f"Error analyzing {file_path} with AI: {str(e)}")
                        file_info['ai_analysis'] = {'error': str(e)}
                # Analyze with image analyzer for image files
                else:
                    try:
                        image_result = image_analyzer.analyze_image(file_path)
                        file_info['image_analysis'] = image_result
                    except Exception as e:
                        logger.error(f"Error analyzing image {file_path}: {str(e)}")
                        file_info['image_analysis'] = {'error': str(e)}

                # Put result in queue
                queue.put(file_info)
                return True
            except Exception as e:
                logger.error(f"Worker error processing {file_path}: {str(e)}")
                queue.put(None)
                return False

        # Start processes
        processes = []
        for file_path, file_ext in file_batch:
            p = multiprocessing.Process(
                target=worker_func,
                args=(file_path, file_ext, result_queue)
            )
            processes.append(p)
            p.start()

        # Collect results
        for _ in range(len(file_batch)):
            result = result_queue.get()
            if result:
                results.append(result)

        # Wait for all processes to finish
        for p in processes:
            p.join()

        return results

    def _process_single_file(self, file_path, file_ext):
        """
        Process a single file

        Args:
            file_path: Path to the file
            file_ext: File extension

        Returns:
            Dictionary with file information and analysis
        """
        try:
            # Get basic file info
            file_info = self._get_file_info(file_path, file_ext)

            # Extract text content
            try:
                text_content = self.parser.extract_text(file_path, file_ext)
                file_info['text_content'] = text_content
            except Exception as e:
                logger.error(f"Error extracting text from {file_path}: {str(e)}")
                file_info['text_content'] = f"Error extracting text: {str(e)}"

            # Extract metadata
            try:
                metadata = self.parser.extract_metadata(file_path, file_ext)
                file_info['metadata'] = metadata
            except Exception as e:
                logger.error(f"Error extracting metadata from {file_path}: {str(e)}")
                file_info['metadata'] = {'error': str(e)}

            # Analyze with AI for document files
            if file_ext.lower() not in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp']:
                try:
                    ai_result = self.ai_analyzer.analyze_text(text_content)
                    file_info['ai_analysis'] = ai_result
                except Exception as e:
                    logger.error(f"Error analyzing {file_path} with AI: {str(e)}")
                    file_info['ai_analysis'] = {'error': str(e)}
            # Analyze with image analyzer for image files
            else:
                try:
                    image_result = self.image_analyzer.analyze_image(file_path)
                    file_info['image_analysis'] = image_result
                except Exception as e:
                    logger.error(f"Error analyzing image {file_path}: {str(e)}")
                    file_info['image_analysis'] = {'error': str(e)}

            return file_info
        except Exception as e:
            logger.error(f"Error processing file {file_path}: {str(e)}")
            logger.error(traceback.format_exc())
            return None

    def _get_file_info(self, file_path, file_ext):
        """
        Get basic file information

        Args:
            file_path: Path to the file
            file_ext: File extension

        Returns:
            Dictionary with basic file information
        """
        file_stat = os.stat(file_path)
        return {
            'file_path': file_path,
            'file_name': os.path.basename(file_path),
            'file_ext': file_ext,
            'file_type': self.supported_extensions.get(file_ext.lower(), 'Unknown'),
            'file_size': file_stat.st_size,
            'created_time': file_stat.st_ctime,
            'modified_time': file_stat.st_mtime,
            'is_image': file_ext.lower() in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp']
        }

    def _get_adaptive_worker_count(self):
        """
        Calculate adaptive worker count based on system resources

        Returns:
            Optimal number of workers
        """
        # Get current CPU and memory usage
        cpu_percent = self.resource_monitor.get_cpu_percent()
        memory_percent = self.resource_monitor.get_memory_percent()

        # Base worker count on CPU cores
        cpu_count = os.cpu_count() or 4

        # Adjust based on current resource usage
        if cpu_percent > 80 or memory_percent > 80:
            # High load, reduce workers
            return max(1, cpu_count // 4)
        elif cpu_percent > 60 or memory_percent > 60:
            # Medium load
            return max(2, cpu_count // 2)
        else:
            # Low load
            return max(2, min(cpu_count - 1, 8))  # Cap at 8 workers

    def pause_operation(self):
        """
        Pause the current operation
        """
        self.is_paused = True
        logger.info("Operation pause requested")

    def resume_operation(self):
        """
        Resume the paused operation
        """
        self.is_paused = False
        logger.info("Operation resume requested")

    def cancel_operation(self):
        """
        Cancel the current operation
        """
        self.is_cancelled = True
        logger.info("Operation cancel requested")

    def get_job_state(self, job_id=None):
        """
        Get the state of a job

        Args:
            job_id: Optional job ID, defaults to current job

        Returns:
            Dictionary with job state
        """
        if job_id is None:
            job_id = self.current_job_id

        if job_id in self.job_state:
            return self.job_state[job_id]
        return None

    def get_job_progress(self, job_id=None):
        """
        Get the progress of a job

        Args:
            job_id: Optional job ID, defaults to current job

        Returns:
            Dictionary with job progress information
        """
        if job_id is None:
            job_id = self.current_job_id

        if job_id in self.job_state:
            job_data = self.job_state[job_id]
            total_files = job_data['total_files']
            processed_files = len(job_data['processed_files'])

            # Calculate progress percentage
            progress_percent = (processed_files / total_files * 100) if total_files > 0 else 0

            # Calculate estimated time remaining
            elapsed_time = job_data['elapsed_time']
            if job_data['start_time'] > 0:
                elapsed_time += time.time() - job_data['start_time']

            if processed_files > 0:
                time_per_file = elapsed_time / processed_files
                remaining_files = total_files - processed_files
                estimated_time_remaining = time_per_file * remaining_files
            else:
                estimated_time_remaining = 0

            return {
                'job_id': job_id,
                'total_files': total_files,
                'processed_files': processed_files,
                'progress_percent': progress_percent,
                'elapsed_time': elapsed_time,
                'estimated_time_remaining': estimated_time_remaining,
                'is_paused': self.is_paused,
                'is_cancelled': self.is_cancelled,
                'is_completed': job_data['completed']
            }
        return None

    def save_job_state(self, file_path):
        """
        Save the current job state to a file

        Args:
            file_path: Path to save the job state

        Returns:
            True if successful, False otherwise
        """
        try:
            # Create a serializable version of the job state
            serializable_state = {}
            for job_id, job_data in self.job_state.items():
                serializable_state[job_id] = {
                    'directory': job_data['directory'],
                    'pending_files': job_data['pending_files'],
                    'total_files': job_data['total_files'],
                    'start_time': job_data['start_time'],
                    'elapsed_time': job_data['elapsed_time'],
                    'completed': job_data['completed']
                }

                # Convert processed files to a serializable format
                processed_files = []
                for file_info in job_data['processed_files']:
                    # Remove non-serializable data
                    serializable_file_info = {k: v for k, v in file_info.items()
                                             if k not in ['text_content']}
                    processed_files.append(serializable_file_info)

                serializable_state[job_id]['processed_files'] = processed_files

            # Save to file
            with open(file_path, 'w') as f:
                json.dump(serializable_state, f)

            return True
        except Exception as e:
            logger.error(f"Error saving job state: {str(e)}")
            return False

    def load_job_state(self, file_path):
        """
        Load job state from a file

        Args:
            file_path: Path to the job state file

        Returns:
            True if successful, False otherwise
        """
        try:
            with open(file_path, 'r') as f:
                self.job_state = json.load(f)
            return True
        except Exception as e:
            logger.error(f"Error loading job state: {str(e)}")
            return False


class ResourceMonitor:
    """
    Class for monitoring system resources during batch processing
    """

    def __init__(self, interval=1.0):
        """
        Initialize the resource monitor

        Args:
            interval: Monitoring interval in seconds
        """
        self.interval = interval
        self.running = False
        self.thread = None
        self.cpu_percent = 0
        self.memory_percent = 0
        self.lock = threading.Lock()

    def start(self):
        """
        Start resource monitoring
        """
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._monitor_resources)
            self.thread.daemon = True
            self.thread.start()

    def stop(self):
        """
        Stop resource monitoring
        """
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)

    def _monitor_resources(self):
        """
        Monitor system resources
        """
        while self.running:
            try:
                # Get CPU and memory usage
                cpu = psutil.cpu_percent(interval=self.interval)
                memory = psutil.virtual_memory().percent

                # Update values with lock
                with self.lock:
                    self.cpu_percent = cpu
                    self.memory_percent = memory
            except:
                # Ignore errors
                pass

    def get_cpu_percent(self):
        """
        Get current CPU usage percentage

        Returns:
            CPU usage percentage
        """
        with self.lock:
            return self.cpu_percent

    def get_memory_percent(self):
        """
        Get current memory usage percentage

        Returns:
            Memory usage percentage
        """
        with self.lock:
            return self.memory_percent

    def get_resource_usage(self):
        """
        Get current resource usage

        Returns:
            Dictionary with resource usage information
        """
        with self.lock:
            return {
                'cpu_percent': self.cpu_percent,
                'memory_percent': self.memory_percent
            }
