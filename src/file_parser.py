import os
import pandas as pd
from bs4 import BeautifulSoup
import docx
import chardet

class FileParser:
    """
    Class for parsing different file types and extracting text content
    """
    
    def extract_text(self, file_path, file_ext):
        """
        Extract text content from various file types
        
        Args:
            file_path: Path to the file
            file_ext: File extension (including the dot)
            
        Returns:
            Extracted text content as a string
        """
        if file_ext == '.csv':
            return self._parse_csv(file_path)
        elif file_ext == '.xlsx':
            return self._parse_excel(file_path)
        elif file_ext == '.html':
            return self._parse_html(file_path)
        elif file_ext == '.md':
            return self._parse_markdown(file_path)
        elif file_ext == '.txt':
            return self._parse_text(file_path)
        elif file_ext == '.docx':
            return self._parse_docx(file_path)
        else:
            raise ValueError(f"Unsupported file extension: {file_ext}")
    
    def extract_metadata(self, file_path, file_ext):
        """
        Extract metadata from files
        
        Args:
            file_path: Path to the file
            file_ext: File extension (including the dot)
            
        Returns:
            Dictionary of metadata
        """
        metadata = {}
        
        # Add file specific metadata extraction based on file type
        if file_ext == '.docx':
            try:
                doc = docx.Document(file_path)
                core_properties = doc.core_properties
                
                # Extract available properties
                if core_properties.author:
                    metadata['author'] = core_properties.author
                if core_properties.title:
                    metadata['title'] = core_properties.title
                if core_properties.created:
                    metadata['created'] = str(core_properties.created)
                if core_properties.modified:
                    metadata['modified'] = str(core_properties.modified)
                if core_properties.subject:
                    metadata['subject'] = core_properties.subject
                if core_properties.keywords:
                    metadata['keywords'] = core_properties.keywords
                
                # Count paragraphs, tables, etc.
                metadata['paragraphs'] = len(doc.paragraphs)
                metadata['tables'] = len(doc.tables)
                metadata['sections'] = len(doc.sections)
            except:
                # Silently fail if there's an issue with metadata extraction
                pass
                
        elif file_ext == '.xlsx':
            try:
                # Get sheet names
                excel_file = pd.ExcelFile(file_path)
                metadata['sheets'] = excel_file.sheet_names
                metadata['num_sheets'] = len(excel_file.sheet_names)
                
                # Sample the first sheet
                df = pd.read_excel(file_path, sheet_name=0, nrows=0)
                metadata['columns'] = list(df.columns)
                metadata['num_columns'] = len(df.columns)
            except:
                pass
                
        elif file_ext == '.csv':
            try:
                # Get column names
                df = pd.read_csv(file_path, nrows=0)
                metadata['columns'] = list(df.columns)
                metadata['num_columns'] = len(df.columns)
                
                # Count rows (efficiently for large files)
                with open(file_path, 'rb') as f:
                    metadata['num_rows'] = sum(1 for _ in f) - 1  # Subtract header
            except:
                pass
                
        return metadata
    
    def _parse_csv(self, file_path):
        """Parse CSV file content"""
        try:
            # Try to detect encoding
            with open(file_path, 'rb') as f:
                result = chardet.detect(f.read(10000))
                encoding = result['encoding']
            
            # Read CSV file with pandas
            df = pd.read_csv(file_path, encoding=encoding)
            
            # Convert to string representation
            text = df.to_string(index=False, max_rows=100)
            
            # Indicate if truncated
            if len(df) > 100:
                text += f"\n\n[File contains {len(df)} rows, showing first 100 only]"
                
            return text
        except Exception as e:
            # Fallback to simple reading
            return self._parse_text(file_path)
    
    def _parse_excel(self, file_path):
        """Parse Excel file content"""
        try:
            # Get sheet names
            excel_file = pd.ExcelFile(file_path)
            sheet_names = excel_file.sheet_names
            
            text = ""
            
            # Read each sheet
            for sheet in sheet_names[:3]:  # Limit to first 3 sheets
                df = pd.read_excel(file_path, sheet_name=sheet)
                
                text += f"Sheet: {sheet}\n"
                text += df.to_string(index=False, max_rows=50)
                
                # Indicate if truncated
                if len(df) > 50:
                    text += f"\n[Sheet contains {len(df)} rows, showing first 50 only]\n"
                
                text += "\n\n"
            
            # Indicate if more sheets exist
            if len(sheet_names) > 3:
                text += f"[File contains {len(sheet_names)} sheets, showing first 3 only]"
                
            return text
        except Exception as e:
            return f"Error parsing Excel file: {str(e)}"
    
    def _parse_html(self, file_path):
        """Parse HTML file content"""
        try:
            # Detect encoding
            with open(file_path, 'rb') as f:
                result = chardet.detect(f.read(10000))
                encoding = result['encoding']
            
            # Read HTML file
            with open(file_path, 'r', encoding=encoding) as f:
                html_content = f.read()
            
            # Parse HTML and extract text
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.extract()
            
            # Get text
            text = soup.get_text(separator='\n')
            
            # Clean up multiple line breaks
            import re
            text = re.sub(r'\n+', '\n\n', text).strip()
            
            return text
        except Exception as e:
            # Fallback to simple reading
            return self._parse_text(file_path)
    
    def _parse_markdown(self, file_path):
        """Parse Markdown file content"""
        return self._parse_text(file_path)
    
    def _parse_text(self, file_path):
        """Parse plain text file content"""
        try:
            # Detect encoding
            with open(file_path, 'rb') as f:
                result = chardet.detect(f.read(10000))
                encoding = result['encoding'] or 'utf-8'
            
            # Read text file
            with open(file_path, 'r', encoding=encoding, errors='replace') as f:
                return f.read()
        except Exception as e:
            return f"Error parsing text file: {str(e)}"
    
    def _parse_docx(self, file_path):
        """Parse Word document content"""
        try:
            # Open the document
            doc = docx.Document(file_path)
            
            # Extract text from paragraphs
            full_text = []
            for para in doc.paragraphs:
                full_text.append(para.text)
            
            # Extract text from tables
            for table in doc.tables:
                for row in table.rows:
                    row_text = []
                    for cell in row.cells:
                        row_text.append(cell.text)
                    full_text.append(' | '.join(row_text))
            
            return '\n'.join(full_text)
        except Exception as e:
            return f"Error parsing Word document: {str(e)}"
