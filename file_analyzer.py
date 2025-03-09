import os
import time
from pathlib import Path
import traceback

from file_parser import FileParser
from ai_analyzer import AIAnalyzer

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
    
    def scan_directory(self, directory_path):
        """
        Scan a directory for supported files and analyze them
        
        Args:
            directory_path: Path to the directory to scan
            
        Returns:
            List of dictionaries containing file information and analysis
        """
        results = []
        
        # Walk through the directory
        for root, dirs, files in os.walk(directory_path):
            for filename in files:
                file_path = os.path.join(root, filename)
                file_ext = os.path.splitext(filename)[1].lower()
                
                # Check if the file extension is supported
                if file_ext in self.supported_extensions:
                    try:
                        # Get file details
                        file_info = self._get_file_info(file_path, file_ext)
                        
                        # Analyze file content
                        file_content = self.parser.extract_text(file_path, file_ext)
                        
                        # Skip empty files
                        if not file_content.strip():
                            continue
                        
                        # Get AI analysis
                        analysis = self.ai_analyzer.analyze_content(file_content, self.supported_extensions[file_ext])
                        
                        # Combine file info and analysis
                        file_info.update(analysis)
                        
                        results.append(file_info)
                    except Exception as e:
                        print(f"Error analyzing file {file_path}: {str(e)}")
                        traceback.print_exc()
        
        return results
    
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
