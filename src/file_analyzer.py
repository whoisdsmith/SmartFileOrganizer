import os
import time
from pathlib import Path
import traceback
import multiprocessing
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

from .file_parser import FileParser
from .ai_analyzer import AIAnalyzer

logger = logging.getLogger("AIDocumentOrganizer")


class FileAnalyzer:
    """
    Class responsible for analyzing files in a directory
    """

    def __init__(self):
        self.parser = FileParser()
        self.ai_analyzer = AIAnalyzer()

        # Supported file extensions
        self.supported_extensions = {
            '.csv': 'CSV',
            '.xlsx': 'Excel',
            '.html': 'HTML',
            '.md': 'Markdown',
            '.txt': 'Text',
            '.docx': 'Word',
            '.pdf': 'PDF'
        }

        # Default batch processing settings
        self.batch_size = 5  # Reduced from 10 to 5 to be more conservative
        # Further reduced thread pool size
        self.max_workers = min(4, (os.cpu_count() or 1))
        self.batch_delay = 10.0  # Increased from 5 to 10 seconds to wait between batches
        self.progress_callback = None  # Callback for progress updates

    def scan_directory(self, directory_path, batch_size=None, batch_delay=None, callback=None):
        """
        Scan a directory for supported files and analyze them

        Args:
            directory_path: Path to the directory to scan
            batch_size: Number of files to process in each batch
            batch_delay: Delay in seconds between processing batches
            callback: Function to call with progress updates

        Returns:
            List of dictionaries with file information
        """
        # Use provided values or defaults
        self.batch_size = batch_size or self.batch_size
        self.batch_delay = batch_delay or self.batch_delay
        self.progress_callback = callback

        logger.info(
            f"Starting directory scan of {directory_path} with batch_size={self.batch_size}, batch_delay={self.batch_delay}")

        # Get all files in the directory and subdirectories
        all_files = []
        total_files = 0
        processed_files = 0
        cancelled = False

        # Walk through the directory
        for root, _, files in os.walk(directory_path):
            for file in files:
                file_path = os.path.join(root, file)
                file_ext = os.path.splitext(file_path)[1].lower()

                # Only include supported file types
                if file_ext in self.supported_extensions:
                    all_files.append((file_path, file_ext))
                    total_files += 1

        logger.info(f"Found {total_files} supported files to process")

        # Process files in batches
        results = []
        batches = [all_files[i:i + self.batch_size]
                   for i in range(0, len(all_files), self.batch_size)]

        for batch_index, batch in enumerate(batches):
            # Check if we should continue or if cancellation was requested
            if self.progress_callback:
                status_message = f"Processing batch {batch_index + 1}/{len(batches)}"
                should_continue = self.progress_callback(
                    processed_files, total_files, status_message)
                if should_continue is False:
                    logger.info("Scan cancelled by user")
                    cancelled = True
                    break

            logger.info(
                f"Processing batch {batch_index + 1}/{len(batches)} ({len(batch)} files)")

            # Process the batch
            batch_results = self._process_batch(batch)
            results.extend(batch_results)
            processed_files += len(batch)

            # Update progress
            if self.progress_callback:
                status_message = f"Completed batch {batch_index + 1}/{len(batches)}"
                should_continue = self.progress_callback(
                    processed_files, total_files, status_message)
                if should_continue is False:
                    logger.info("Scan cancelled by user")
                    cancelled = True
                    break

            # Delay between batches (except for the last batch)
            if batch_index < len(batches) - 1 and not cancelled:
                logger.info(
                    f"Waiting {self.batch_delay} seconds before next batch")
                time.sleep(self.batch_delay)

        logger.info(
            f"Scan completed. Processed {len(results)}/{total_files} files")
        return results

    def _process_batch(self, file_batch):
        """
        Process a batch of files using a thread pool

        Args:
            file_batch: List of (file_path, file_ext) tuples to process

        Returns:
            List of file information dictionaries
        """
        results = []
        cancelled = False

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all files for processing
            future_to_file = {
                executor.submit(self._process_single_file, file_path, file_ext): (file_path, file_ext)
                for file_path, file_ext in file_batch
            }

            # Process results as they complete
            for i, future in enumerate(as_completed(future_to_file)):
                file_path, file_ext = future_to_file[future]
                try:
                    file_info = future.result()
                    if file_info:
                        results.append(file_info)

                    # Update progress after each file
                    if self.progress_callback:
                        status_message = f"Processed: {os.path.basename(file_path)}"
                        should_continue = self.progress_callback(
                            i + 1, len(file_batch), status_message)
                        if should_continue is False:
                            logger.info("Batch processing cancelled by user")
                            cancelled = True
                            break

                except Exception as e:
                    logger.error(
                        f"Error processing file {file_path}: {str(e)}")
                    logger.error(traceback.format_exc())

        return results

    def _process_single_file(self, file_path, file_ext):
        """Process a single file

        Args:
            file_path: Path to the file
            file_ext: File extension

        Returns:
            File information dictionary or None if processing failed
        """
        try:
            # Get file details
            file_info = self._get_file_info(file_path, file_ext)

            # Analyze file content
            file_content = self.parser.extract_text(file_path, file_ext)

            # Skip empty files
            if not file_content.strip():
                return None

            # Get AI analysis
            analysis = self.ai_analyzer.analyze_content(
                file_content, self.supported_extensions[file_ext])

            # Combine file info and analysis
            file_info.update(analysis)

            return file_info
        except Exception as e:
            logger.error(f"Error analyzing file {file_path}: {str(e)}")
            traceback.print_exc()
            return None

    def _get_file_info(self, file_path, file_ext):
        """
        Get basic file information

        Args:
            file_path: Path to the file
            file_ext: File extension

        Returns:
            Dictionary with file information
        """
        file_stat = os.stat(file_path)

        return {
            "path": file_path,
            "filename": os.path.basename(file_path),
            "file_type": self.supported_extensions[file_ext],
            "size": file_stat.st_size,
            "created": time.ctime(file_stat.st_ctime),
            "modified": time.ctime(file_stat.st_mtime),
            "extension": file_ext
        }
