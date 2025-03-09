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
            '.docx': 'Word'
        }
        
        # Default batch processing settings
        self.batch_size = 20  # Number of files per batch
        self.max_workers = min(32, (os.cpu_count() or 1) * 4)  # Thread pool size
        self.progress_callback = None  # Callback for progress updates
        
    def scan_directory(self, directory_path, batch_size=None, callback=None):
        """
        Scan a directory for supported files and analyze them
        
        Args:
            directory_path: Path to the directory to scan
            batch_size: Number of files to process in each batch
            callback: Function to call with progress updates
            
        Returns:
            List of dictionaries containing file information and analysis
        """
        if batch_size is not None:
            self.batch_size = batch_size
            
        if callback is not None:
            self.progress_callback = callback
            
        # Find all valid files first
        valid_files = []
        for root, dirs, files in os.walk(directory_path):
            for filename in files:
                file_path = os.path.join(root, filename)
                file_ext = os.path.splitext(filename)[1].lower()
                
                if file_ext in self.supported_extensions:
                    valid_files.append((file_path, file_ext))
        
        # Notify of total files to process
        total_files = len(valid_files)
        logger.info(f"Found {total_files} files to process")
        
        if self.progress_callback:
            self.progress_callback(0, total_files, "Starting batch processing")
        
        # Process files in batches using thread pool for I/O bound operations
        results = []
        processed_count = 0
        
        for i in range(0, len(valid_files), self.batch_size):
            batch = valid_files[i:i + self.batch_size]
            batch_results = self._process_batch(batch)
            results.extend(batch_results)
            
            processed_count += len(batch)
            if self.progress_callback:
                self.progress_callback(
                    processed_count, 
                    total_files, 
                    f"Processed batch {i//self.batch_size + 1}/{(total_files+self.batch_size-1)//self.batch_size}"
                )
                
            logger.info(f"Completed batch {i//self.batch_size + 1}, processed {processed_count}/{total_files} files")
        
        return results
        
    def _process_batch(self, file_batch):
        """Process a batch of files in parallel
        
        Args:
            file_batch: List of (file_path, file_ext) tuples
            
        Returns:
            List of processed file information dictionaries
        """
        batch_results = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all file processing tasks
            future_to_file = {
                executor.submit(self._process_single_file, file_path, file_ext): (file_path, file_ext)
                for file_path, file_ext in file_batch
            }
            
            # Process results as they complete
            for future in as_completed(future_to_file):
                try:
                    result = future.result()
                    if result:  # Filter out None results from failed processing
                        batch_results.append(result)
                except Exception as e:
                    file_path, _ = future_to_file[future]
                    logger.error(f"Error processing file {file_path}: {str(e)}")
        
        return batch_results
    
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
            analysis = self.ai_analyzer.analyze_content(file_content, self.supported_extensions[file_ext])
            
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
