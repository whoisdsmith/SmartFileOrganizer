"""
Image Analyzer Plugin implementation.
Provides image analysis capabilities including:
- Metadata extraction
- Feature detection
- Color analysis
- Thumbnail generation
- OCR integration
"""

import os
import logging
import tempfile
import time
from typing import Dict, List, Tuple, Any, Optional
from PIL import Image, ImageOps, UnidentifiedImageError
from io import BytesIO

from ...core.plugin_base import AIAnalyzerPlugin

logger = logging.getLogger('AIDocumentOrganizerV2.ImageAnalyzer')


class ImageAnalyzerPlugin(AIAnalyzerPlugin):
    """
    Plugin for analyzing image files and extracting features and metadata.
    Provides capabilities for image processing, feature extraction, and thumbnail generation.
    """
    
    # Plugin metadata
    plugin_type = "ai_analyzer"  # Explicitly set the plugin type
    name = "Image Analyzer"
    version = "1.0.0"
    description = "Analyzes image files and extracts features and metadata"
    
    def __init__(self, plugin_id=None, name=None, version=None, description=None):
        """Initialize the image analyzer plugin."""
        super().__init__(
            plugin_id=plugin_id or "analyzer.image_analyzer",
            name=name or "Image Analyzer",
            version=version or "1.0.0",
            description=description or "Analyzes image files and extracts features and metadata"
        )
        
        self._supported_formats = [
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif', '.webp'
        ]
        
        # Initialize PIL availability flag
        self.pil_available = self._check_pil_availability()
        
        # Set default settings
        self._default_settings = {
            'thumbnail_size': (128, 128),
            'extract_dominant_colors': True,
            'max_dominant_colors': 5,
            'generate_thumbnails': True,
            'detect_faces': False,  # Requires additional dependencies
            'ocr_enabled': False,   # OCR is handled separately
            'thumbnail_directory': os.path.join(tempfile.gettempdir(), 'image_analyzer_thumbnails')
        }
        
    def _check_pil_availability(self) -> bool:
        """Check if PIL/Pillow is available and working properly."""
        try:
            # Create a simple test image to verify PIL is working
            test_image = Image.new('RGB', (10, 10), color='red')
            test_buffer = BytesIO()
            test_image.save(test_buffer, format='PNG')
            return True
        except Exception as e:
            logger.warning(f"PIL/Pillow not available or not working properly: {e}")
            return False
    
    def initialize(self) -> bool:
        """
        Initialize the image analyzer plugin.
            
        Returns:
            True if initialization was successful, False otherwise
        """
        result = super().initialize()
        if not result:
            return False
        
        # Register default settings
        if self.settings_manager:
            for key, value in self._default_settings.items():
                setting_name = f"image_analyzer.{key}"
                if hasattr(self.settings_manager, 'has_setting') and not self.settings_manager.has_setting(setting_name):
                    if hasattr(self.settings_manager, 'register_setting'):
                        self.settings_manager.register_setting(setting_name, value)
                    else:
                        self.settings_manager.set_setting(setting_name, value)
        
        # Create thumbnail directory if it doesn't exist
        thumbnail_dir = self.get_setting('thumbnail_directory')
        if self.get_setting('generate_thumbnails') and not os.path.exists(thumbnail_dir):
            try:
                os.makedirs(thumbnail_dir, exist_ok=True)
                logger.info(f"Created thumbnail directory: {thumbnail_dir}")
            except Exception as e:
                logger.warning(f"Failed to create thumbnail directory: {e}")
        
        logger.info("Image analyzer settings initialized")
        return True
    
    def get_supported_formats(self) -> List[str]:
        """Get the list of supported image formats."""
        return self._supported_formats
    
    def analyze_image(self, image_path: str) -> Dict[str, Any]:
        """
        Analyze an image file and extract metadata and features.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Dictionary with analysis results
        """
        if not self.pil_available:
            return {
                'error': "PIL/Pillow library is not available",
                'success': False
            }
        
        if not os.path.exists(image_path):
            return {
                'error': f"Image file not found: {image_path}",
                'success': False
            }
        
        try:
            # Open the image
            img = Image.open(image_path)
            
            # Get basic image info
            file_info = self._get_file_info(image_path)
            
            # Extract image metadata
            metadata = self._extract_metadata(img, image_path)
            
            # Analyze image features
            features = self._analyze_features(img)
            
            # Generate thumbnail if enabled
            thumbnail_path = None
            if self.get_setting('generate_thumbnails'):
                thumbnail_path = self._generate_thumbnail(img, image_path)
            
            # Combine all results
            result = {
                'success': True,
                'file_info': file_info,
                'metadata': metadata,
                'features': features
            }
            
            if thumbnail_path:
                result['thumbnail_path'] = thumbnail_path
            
            return result
            
        except UnidentifiedImageError:
            return {
                'error': f"Unidentified image format for file: {image_path}",
                'success': False
            }
        except Exception as e:
            logger.error(f"Error analyzing image {image_path}: {str(e)}")
            return {
                'error': f"Failed to analyze image: {str(e)}",
                'success': False
            }
    
    def _get_file_info(self, image_path: str) -> Dict[str, Any]:
        """Get basic file information."""
        file_stat = os.stat(image_path)
        filename = os.path.basename(image_path)
        file_ext = os.path.splitext(filename)[1].lower()
        
        return {
            'filename': filename,
            'filepath': image_path,
            'file_size': file_stat.st_size,
            'created_time': time.ctime(file_stat.st_ctime),
            'modified_time': time.ctime(file_stat.st_mtime),
            'file_type': file_ext[1:] if file_ext.startswith('.') else file_ext
        }
    
    def _extract_metadata(self, img: Image.Image, image_path: str) -> Dict[str, Any]:
        """Extract metadata from the image."""
        metadata = {
            'format': img.format,
            'mode': img.mode,
            'width': img.width,
            'height': img.height,
            'aspect_ratio': img.width / img.height if img.height > 0 else 0
        }
        
        # Check if image has transparency
        if self._has_transparency(img):
            metadata['has_transparency'] = True
        
        # Check if image is animated (GIF)
        if self._is_animated(img):
            metadata['animated'] = True
            try:
                metadata['frame_count'] = getattr(img, 'n_frames', 1)
            except Exception:
                metadata['frame_count'] = 1
        
        # Extract EXIF data if available
        exif_data = self._extract_exif_data(img)
        if exif_data:
            metadata['exif'] = exif_data
        
        return metadata
    
    def _analyze_features(self, img: Image.Image) -> Dict[str, Any]:
        """Analyze image features."""
        features = {}
        
        # Extract dominant colors if enabled
        if self.get_setting('extract_dominant_colors'):
            try:
                dominant_colors = self._extract_dominant_colors(
                    img, 
                    self.get_setting('max_dominant_colors')
                )
                features['dominant_colors'] = dominant_colors
            except Exception as e:
                logger.warning(f"Failed to extract dominant colors: {e}")
        
        return features
    
    def _has_transparency(self, img: Image.Image) -> bool:
        """Check if the image has transparency."""
        if img.mode == 'RGBA' or img.mode == 'LA' or (img.mode == 'P' and 'transparency' in img.info):
            return True
        return False
    
    def _is_animated(self, img: Image.Image) -> bool:
        """Check if the image is animated (GIF)."""
        try:
            return hasattr(img, 'is_animated') and img.is_animated
        except Exception:
            return False
    
    def _extract_dominant_colors(self, img: Image.Image, max_colors: int = 5) -> List[Dict[str, Any]]:
        """
        Extract dominant colors from the image.
        
        Args:
            img: PIL Image object
            max_colors: Maximum number of dominant colors to extract
            
        Returns:
            List of dominant color information
        """
        # Resize image to speed up processing
        img_resized = img.copy()
        img_resized.thumbnail((100, 100))
        
        # Convert to RGB mode if needed
        if img_resized.mode != 'RGB':
            img_resized = img_resized.convert('RGB')
        
        # Get color histogram
        colors = img_resized.getcolors(maxcolors=10000)
        if not colors:
            return []
        
        # Sort colors by count (most frequent first)
        colors.sort(reverse=True)
        
        # Get the top N colors
        result = []
        for i, (count, color) in enumerate(colors[:max_colors]):
            # Skip near-black and near-white colors
            r, g, b = color
            if (r < 10 and g < 10 and b < 10) or \
               (r > 245 and g > 245 and b > 245):
                continue
                
            hex_color = '#{:02x}{:02x}{:02x}'.format(r, g, b)
            
            result.append({
                'rgb': color,
                'hex': hex_color,
                'frequency': count / sum(c[0] for c in colors) if colors else 0
            })
            
            if len(result) >= max_colors:
                break
                
        return result
    
    def _extract_exif_data(self, img: Image.Image) -> Dict[str, Any]:
        """Extract EXIF data from the image."""
        exif_data = {}
        try:
            # Use standard PIL/Pillow API for getting EXIF data
            if hasattr(img, 'getexif'):
                exif = img.getexif()  # Modern method
            elif hasattr(img, '_getexif'):
                exif = img._getexif()  # Legacy method
            else:
                exif = None
                
            if not exif:
                return {}
                
            # Map EXIF tags to human-readable names
            exif_tags = {
                0x010F: 'camera_make',
                0x0110: 'camera_model',
                0x8827: 'iso_speed',
                0x829A: 'exposure_time',
                0x829D: 'f_number',
                0x9003: 'date_taken',
                0x9286: 'user_comment',
                0x8822: 'exposure_program',
                0xA002: 'image_width',
                0xA003: 'image_height',
                0xA404: 'digital_zoom_ratio',
                0xA406: 'scene_type',
                0xA408: 'contrast',
                0xA409: 'saturation',
                0xA40A: 'sharpness'
            }
            
            for tag, value in exif.items():
                if tag in exif_tags:
                    exif_data[exif_tags[tag]] = str(value)
            
            # Extract GPS data if available
            gps_info = self._extract_gps_info(exif)
            if gps_info:
                exif_data['gps'] = gps_info
                
        except Exception as e:
            logger.debug(f"Failed to extract EXIF data: {e}")
            
        return exif_data
    
    def _extract_gps_info(self, exif) -> Dict[str, Any]:
        """Extract GPS information from EXIF data."""
        gps_info = {}
        
        try:
            # Check if GPS info exists
            if 0x8825 not in exif:
                return {}
                
            gps_data = exif[0x8825]
            
            # GPS latitude
            if 2 in gps_data:
                latitude = self._convert_to_degrees(gps_data[2])
                latitude_ref = gps_data.get(1, 'N')
                
                if latitude_ref == 'S':
                    latitude = -latitude
                    
                gps_info['latitude'] = latitude
            
            # GPS longitude
            if 4 in gps_data:
                longitude = self._convert_to_degrees(gps_data[4])
                longitude_ref = gps_data.get(3, 'E')
                
                if longitude_ref == 'W':
                    longitude = -longitude
                    
                gps_info['longitude'] = longitude
            
            # GPS altitude
            if 6 in gps_data:
                altitude = float(gps_data[6][0]) / float(gps_data[6][1])
                altitude_ref = gps_data.get(5, 0)
                
                if altitude_ref == 1:
                    altitude = -altitude
                    
                gps_info['altitude'] = altitude
                
        except Exception as e:
            logger.debug(f"Failed to extract GPS info: {e}")
            
        return gps_info
    
    def _convert_to_degrees(self, value) -> float:
        """Convert GPS coordinates to decimal degrees."""
        d = float(value[0][0]) / float(value[0][1])
        m = float(value[1][0]) / float(value[1][1])
        s = float(value[2][0]) / float(value[2][1])
        
        return d + (m / 60.0) + (s / 3600.0)
    
    def _generate_thumbnail(self, img: Image.Image, image_path: str) -> Optional[str]:
        """
        Generate a thumbnail for the image.
        
        Args:
            img: PIL Image object
            image_path: Path to the original image
            
        Returns:
            Path to the generated thumbnail or None if failed
        """
        if not self.get_setting('generate_thumbnails'):
            return None
            
        try:
            # Get thumbnail size from settings
            thumbnail_size = self.get_setting('thumbnail_size')
            
            # Create a copy of the image to avoid modifying the original
            img_copy = img.copy()
            
            # Convert to RGB mode if needed
            if img_copy.mode not in ('RGB', 'RGBA'):
                img_copy = img_copy.convert('RGB')
            
            # Resize the image to create thumbnail
            img_copy.thumbnail(thumbnail_size, Image.LANCZOS)
            
            # Create thumbnail filename
            filename = os.path.basename(image_path)
            base_name = os.path.splitext(filename)[0]
            thumbnail_dir = self.get_setting('thumbnail_directory')
            thumbnail_path = os.path.join(thumbnail_dir, f"{base_name}_thumb.png")
            
            # Save the thumbnail
            img_copy.save(thumbnail_path, format='PNG')
            
            return thumbnail_path
            
        except Exception as e:
            logger.warning(f"Failed to generate thumbnail: {e}")
            return None
    
    def analyze_content(self, text: str, file_type: str) -> Dict[str, Any]:
        """
        Analyze document content using AI.
        
        This method is required by the AIAnalyzerPlugin base class, but for 
        image analysis, we use the analyze_image method instead.
        
        Args:
            text: Document text content
            file_type: Type of document (e.g., 'txt', 'pdf', 'docx')
            
        Returns:
            Dictionary with analysis results
        """
        return {
            'success': False,
            'error': "This plugin analyzes images, not text content. Use analyze_image() instead.",
            'message': "For image analysis, please use the analyze_image() method with a path to an image file."
        }

    def get_available_models(self) -> List[str]:
        """
        Get list of available AI models.
        
        Returns:
            List of model names
        """
        # Image analyzer doesn't use AI models in the same way as text analyzers
        return ["basic_image_analysis"]
        
    def set_model(self, model_name: str) -> bool:
        """
        Set the AI model to use.
        
        Args:
            model_name: Name of the model to use
            
        Returns:
            True if successful, False otherwise
        """
        # Image analyzer doesn't use AI models in the same way as text analyzers
        return True

    def shutdown(self) -> bool:
        """Shut down the image analyzer plugin."""
        logger.info("Shutting down image analyzer plugin")
        return True