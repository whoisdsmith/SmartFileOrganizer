import os
import pandas as pd
from bs4 import BeautifulSoup
import docx
import chardet
import PyPDF2
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
import io
import datetime


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
        elif file_ext.lower() in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp']:
            return self._parse_image(file_path)
        else:
            raise ValueError(f"Unsupported file extension: {file_ext}")

    def extract_metadata(self, file_path, file_ext):
        """
        Extract metadata from files

        Args:
            file_path: Path to the file
            file_ext: File extension (including the dot)

        Returns:
            Dictionary with metadata
        """
        # Basic metadata for all files
        file_stat = os.stat(file_path)
        metadata = {
            'filename': os.path.basename(file_path),
            'file_size': file_stat.st_size,
            'created_time': datetime.datetime.fromtimestamp(file_stat.st_ctime).isoformat(),
            'modified_time': datetime.datetime.fromtimestamp(file_stat.st_mtime).isoformat(),
            'file_extension': file_ext,
        }

        # File type specific metadata
        if file_ext == '.pdf':
            try:
                with open(file_path, 'rb') as file:
                    reader = PyPDF2.PdfReader(file)
                    if reader.metadata:
                        for key, value in reader.metadata.items():
                            if key.startswith('/'):
                                clean_key = key[1:].lower()
                                metadata[clean_key] = value
                    metadata['page_count'] = len(reader.pages)
            except Exception as e:
                metadata['extraction_error'] = str(e)

        elif file_ext == '.docx':
            try:
                doc = docx.Document(file_path)
                metadata['page_count'] = len(doc.sections)
                metadata['paragraph_count'] = len(doc.paragraphs)

                # Try to extract core properties
                try:
                    core_props = doc.core_properties
                    if hasattr(core_props, 'author') and core_props.author:
                        metadata['author'] = core_props.author
                    if hasattr(core_props, 'title') and core_props.title:
                        metadata['title'] = core_props.title
                    if hasattr(core_props, 'created') and core_props.created:
                        metadata['doc_created'] = core_props.created.isoformat()
                    if hasattr(core_props, 'modified') and core_props.modified:
                        metadata['doc_modified'] = core_props.modified.isoformat()
                except:
                    pass
            except Exception as e:
                metadata['extraction_error'] = str(e)

        elif file_ext.lower() in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp']:
            try:
                image_metadata = self._extract_image_metadata(file_path)
                metadata.update(image_metadata)
            except Exception as e:
                metadata['extraction_error'] = str(e)

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

                # Check if PDF is encrypted
                if reader.is_encrypted:
                    try:
                        # Try with empty password first
                        reader.decrypt('')
                    except:
                        return "Error: This PDF is password-protected and cannot be read."

                # Extract text from each page
                for page_num in range(len(reader.pages)):
                    page = reader.pages[page_num]
                    try:
                        page_text = page.extract_text()
                        if page_text:
                            text_content += f"--- Page {page_num + 1} ---\n{page_text}\n\n"
                        else:
                            text_content += f"--- Page {page_num + 1} ---\n[No extractable text on this page - may contain images only]\n\n"
                    except Exception as e:
                        text_content += f"--- Page {page_num + 1} ---\n[Error extracting text: {str(e)}]\n\n"

            if not text_content.strip():
                return "This PDF does not contain extractable text. It may be scanned or image-based."

            return text_content.strip()
        except Exception as e:
            # Handle potential errors (corrupted PDF, password-protected, etc.)
            return f"Error extracting text from PDF: {str(e)}"

    def _parse_image(self, file_path):
        """
        Extract any text content from image (placeholder for OCR integration)

        Args:
            file_path: Path to the image file

        Returns:
            String with basic image information (no OCR yet)
        """
        try:
            with Image.open(file_path) as img:
                # Basic image information
                width, height = img.size
                format_name = img.format
                mode = img.mode

                # Create a basic text representation
                text = f"Image: {os.path.basename(file_path)}\n"
                text += f"Dimensions: {width}x{height} pixels\n"
                text += f"Format: {format_name}\n"
                text += f"Color Mode: {mode}\n"

                # Add EXIF data summary if available
                exif_data = self._extract_image_metadata(file_path)
                if exif_data:
                    text += "\nImage Metadata:\n"
                    for key, value in exif_data.items():
                        if key not in ['filename', 'file_size', 'created_time', 'modified_time', 'file_extension']:
                            text += f"{key}: {value}\n"

                return text
        except Exception as e:
            return f"Error parsing image: {str(e)}"

    def _extract_image_metadata(self, file_path):
        """
        Extract metadata from image files including EXIF data

        Args:
            file_path: Path to the image file

        Returns:
            Dictionary with image metadata
        """
        metadata = {}

        try:
            with Image.open(file_path) as img:
                # Basic image properties
                metadata['image_width'], metadata['image_height'] = img.size
                metadata['image_format'] = img.format
                metadata['image_mode'] = img.mode

                # Extract EXIF data if available
                if hasattr(img, '_getexif') and img._getexif():
                    exif = img._getexif()
                    if exif:
                        # Process standard EXIF tags
                        for tag_id, value in exif.items():
                            tag = TAGS.get(tag_id, tag_id)

                            # Handle special cases
                            if tag == 'GPSInfo':
                                gps_data = {}
                                for gps_tag_id, gps_value in value.items():
                                    gps_tag = GPSTAGS.get(gps_tag_id, gps_tag_id)
                                    gps_data[gps_tag] = gps_value

                                # Calculate latitude and longitude if available
                                if 'GPSLatitude' in gps_data and 'GPSLatitudeRef' in gps_data:
                                    lat = self._convert_to_degrees(gps_data['GPSLatitude'])
                                    if gps_data['GPSLatitudeRef'] == 'S':
                                        lat = -lat
                                    metadata['gps_latitude'] = lat

                                if 'GPSLongitude' in gps_data and 'GPSLongitudeRef' in gps_data:
                                    lon = self._convert_to_degrees(gps_data['GPSLongitude'])
                                    if gps_data['GPSLongitudeRef'] == 'W':
                                        lon = -lon
                                    metadata['gps_longitude'] = lon

                                if 'GPSAltitude' in gps_data:
                                    metadata['gps_altitude'] = float(gps_data['GPSAltitude'])

                                metadata['gps_data'] = gps_data
                            elif tag == 'DateTime':
                                metadata['date_time'] = value
                            elif tag == 'DateTimeOriginal':
                                metadata['date_time_original'] = value
                            elif tag == 'DateTimeDigitized':
                                metadata['date_time_digitized'] = value
                            elif tag == 'Make':
                                metadata['camera_make'] = value
                            elif tag == 'Model':
                                metadata['camera_model'] = value
                            elif tag == 'XResolution':
                                metadata['x_resolution'] = float(value)
                            elif tag == 'YResolution':
                                metadata['y_resolution'] = float(value)
                            elif tag == 'ExposureTime':
                                metadata['exposure_time'] = str(value)
                            elif tag == 'FNumber':
                                metadata['f_number'] = float(value)
                            elif tag == 'ISOSpeedRatings':
                                metadata['iso_speed'] = value
                            elif tag == 'FocalLength':
                                metadata['focal_length'] = float(value)
                            else:
                                # Store other tags with proper formatting
                                if isinstance(value, bytes):
                                    try:
                                        value = value.decode('utf-8')
                                    except:
                                        value = str(value)
                                metadata[f'exif_{tag.lower()}'] = value
        except Exception as e:
            metadata['exif_error'] = str(e)

        return metadata

    def _convert_to_degrees(self, value):
        """
        Helper method to convert GPS coordinates from EXIF format to decimal degrees

        Args:
            value: EXIF GPS coordinate value (degrees, minutes, seconds)

        Returns:
            Decimal degrees
        """
        degrees = float(value[0])
        minutes = float(value[1])
        seconds = float(value[2])

        return degrees + (minutes / 60.0) + (seconds / 3600.0)
