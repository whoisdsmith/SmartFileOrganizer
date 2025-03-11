import os
import pandas as pd
from bs4 import BeautifulSoup
import docx
import chardet
import PyPDF2

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
        elif file_ext == '.pdf':
            return self._parse_pdf(file_path)
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

        # Basic file metadata
        file_stat = os.stat(file_path)
        metadata['file_size'] = file_stat.st_size
        metadata['created_time'] = file_stat.st_ctime
        metadata['modified_time'] = file_stat.st_mtime
        metadata['accessed_time'] = file_stat.st_atime

        # File type specific metadata
        if file_ext == '.csv':
            try:
                df = pd.read_csv(file_path)
                metadata['row_count'] = len(df)
                metadata['column_count'] = len(df.columns)
                metadata['columns'] = list(df.columns)
            except Exception as e:
                metadata['error'] = str(e)

        elif file_ext == '.xlsx':
            try:
                xl = pd.ExcelFile(file_path)
                metadata['sheet_names'] = xl.sheet_names
                metadata['sheet_count'] = len(xl.sheet_names)

                # Get row and column counts for the first sheet
                df = pd.read_excel(file_path, sheet_name=0)
                metadata['row_count'] = len(df)
                metadata['column_count'] = len(df.columns)
            except Exception as e:
                metadata['error'] = str(e)

        elif file_ext == '.docx':
            try:
                doc = docx.Document(file_path)
                metadata['paragraph_count'] = len(doc.paragraphs)
                metadata['section_count'] = len(doc.sections)

                # Try to extract core properties
                try:
                    core_props = doc.core_properties
                    metadata['author'] = core_props.author
                    metadata['created'] = core_props.created
                    metadata['last_modified_by'] = core_props.last_modified_by
                    metadata['modified'] = core_props.modified
                    metadata['title'] = core_props.title
                    metadata['subject'] = core_props.subject
                except:
                    pass
            except Exception as e:
                metadata['error'] = str(e)

        elif file_ext == '.pdf':
            try:
                with open(file_path, 'rb') as file:
                    reader = PyPDF2.PdfReader(file)
                    metadata['page_count'] = len(reader.pages)

                    # Extract document info if available
                    if reader.metadata:
                        info = reader.metadata
                        for key in info:
                            if info[key] and str(info[key]).strip():
                                metadata[key.lower()] = str(info[key])
            except Exception as e:
                metadata['error'] = str(e)

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

    def _parse_pdf(self, file_path):
        """
        Parse PDF file and extract text content

        Args:
            file_path: Path to the PDF file

        Returns:
            Extracted text content as a string
        """
        try:
            text_content = ""
            with open(file_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)

                # Extract text from each page
                for page_num in range(len(reader.pages)):
                    page = reader.pages[page_num]
                    text_content += page.extract_text() + "\n\n"

            return text_content.strip()
        except Exception as e:
            # Handle potential errors (corrupted PDF, password-protected, etc.)
            return f"Error extracting text from PDF: {str(e)}"
