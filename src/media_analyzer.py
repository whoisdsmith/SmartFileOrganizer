import os
import tempfile
import logging
from typing import Dict, Any, Optional, Tuple, List
from pathlib import Path

import moviepy.editor as mp
from pydub import AudioSegment
from PIL import Image
import ffmpeg

logger = logging.getLogger("AIDocumentOrganizer")


class MediaAnalyzer:
    """
    Class for analyzing audio and video files, extracting metadata,
    generating thumbnails, and preparing files for transcription.
    """

    def __init__(self):
        """Initialize the MediaAnalyzer with supported formats."""
        self.supported_audio_formats = {
            '.mp3': 'MP3 Audio',
            '.wav': 'WAV Audio',
            '.flac': 'FLAC Audio',
            '.aac': 'AAC Audio',
            '.ogg': 'OGG Audio',
            '.m4a': 'M4A Audio',
        }

        self.supported_video_formats = {
            '.mp4': 'MP4 Video',
            '.avi': 'AVI Video',
            '.mkv': 'MKV Video',
            '.mov': 'MOV Video',
            '.wmv': 'WMV Video',
            '.webm': 'WebM Video',
            '.flv': 'FLV Video',
        }

    def analyze_audio(self, file_path: str) -> Dict[str, Any]:
        """
        Analyze an audio file and extract metadata.

        Args:
            file_path: Path to the audio file

        Returns:
            Dictionary containing audio metadata
        """
        try:
            audio = AudioSegment.from_file(file_path)

            # Extract basic metadata
            metadata = {
                'duration_seconds': len(audio) / 1000,
                'channels': audio.channels,
                'sample_width_bytes': audio.sample_width,
                'frame_rate_hz': audio.frame_rate,
                'frame_width': audio.frame_width,
                'bitrate': self._calculate_bitrate(audio),
                'file_size_bytes': os.path.getsize(file_path),
            }

            # Try to extract ID3 tags for MP3 files
            file_ext = os.path.splitext(file_path)[1].lower()
            if file_ext == '.mp3':
                id3_tags = self._extract_id3_tags(file_path)
                metadata.update(id3_tags)

            return metadata

        except Exception as e:
            logger.error(f"Error analyzing audio file {file_path}: {str(e)}")
            return {'error': str(e)}

    def analyze_video(self, file_path: str) -> Dict[str, Any]:
        """
        Analyze a video file and extract metadata.

        Args:
            file_path: Path to the video file

        Returns:
            Dictionary containing video metadata
        """
        try:
            # Use ffmpeg to get video metadata
            probe = ffmpeg.probe(file_path)

            # Extract video stream info
            video_info = next((stream for stream in probe['streams']
                              if stream['codec_type'] == 'video'), None)

            # Extract audio stream info
            audio_info = next((stream for stream in probe['streams']
                              if stream['codec_type'] == 'audio'), None)

            # Extract format info
            format_info = probe['format']

            # Build metadata dictionary
            metadata = {
                'duration_seconds': float(format_info.get('duration', 0)),
                'file_size_bytes': os.path.getsize(file_path),
                'format_name': format_info.get('format_name', ''),
                'bitrate': int(format_info.get('bit_rate', 0)),
            }

            # Add video stream info if available
            if video_info:
                metadata.update({
                    'width': int(video_info.get('width', 0)),
                    'height': int(video_info.get('height', 0)),
                    'video_codec': video_info.get('codec_name', ''),
                    'video_codec_long': video_info.get('codec_long_name', ''),
                    'frame_rate': self._calculate_frame_rate(video_info),
                    'aspect_ratio': video_info.get('display_aspect_ratio', ''),
                })

            # Add audio stream info if available
            if audio_info:
                metadata.update({
                    'audio_codec': audio_info.get('codec_name', ''),
                    'audio_codec_long': audio_info.get('codec_long_name', ''),
                    'audio_channels': int(audio_info.get('channels', 0)),
                    'audio_sample_rate': int(audio_info.get('sample_rate', 0)),
                })

            return metadata

        except Exception as e:
            logger.error(f"Error analyzing video file {file_path}: {str(e)}")
            return {'error': str(e)}

    def generate_audio_waveform(self, file_path: str, output_path: Optional[str] = None) -> str:
        """
        Generate a waveform image from an audio file.

        Args:
            file_path: Path to the audio file
            output_path: Optional path to save the waveform image

        Returns:
            Path to the generated waveform image
        """
        try:
            # If no output path is provided, create a temporary file
            if not output_path:
                temp_dir = tempfile.gettempdir()
                file_name = os.path.basename(file_path)
                base_name = os.path.splitext(file_name)[0]
                output_path = os.path.join(
                    temp_dir, f"{base_name}_waveform.png")

            # Load audio file
            audio = AudioSegment.from_file(file_path)

            # TODO: Implement waveform generation using matplotlib or similar
            # This is a placeholder for now

            return output_path

        except Exception as e:
            logger.error(
                f"Error generating audio waveform for {file_path}: {str(e)}")
            return ""

    def generate_video_thumbnail(self, file_path: str, output_path: Optional[str] = None,
                                 time_offset: float = 5.0) -> str:
        """
        Generate a thumbnail image from a video file.

        Args:
            file_path: Path to the video file
            output_path: Optional path to save the thumbnail image
            time_offset: Time in seconds to extract the thumbnail from

        Returns:
            Path to the generated thumbnail image
        """
        try:
            # If no output path is provided, create a temporary file
            if not output_path:
                temp_dir = tempfile.gettempdir()
                file_name = os.path.basename(file_path)
                base_name = os.path.splitext(file_name)[0]
                output_path = os.path.join(
                    temp_dir, f"{base_name}_thumbnail.jpg")

            # Load video and extract frame
            video = mp.VideoFileClip(file_path)

            # Adjust time_offset if it exceeds video duration
            if time_offset > video.duration:
                time_offset = video.duration / 3  # Use 1/3 of the video duration

            # Extract the frame and save it
            video.save_frame(output_path, t=time_offset)

            return output_path

        except Exception as e:
            logger.error(
                f"Error generating video thumbnail for {file_path}: {str(e)}")
            return ""

    def extract_audio_from_video(self, video_path: str, output_path: Optional[str] = None) -> str:
        """
        Extract audio track from a video file.

        Args:
            video_path: Path to the video file
            output_path: Optional path to save the extracted audio

        Returns:
            Path to the extracted audio file
        """
        try:
            # If no output path is provided, create a temporary file
            if not output_path:
                temp_dir = tempfile.gettempdir()
                file_name = os.path.basename(video_path)
                base_name = os.path.splitext(file_name)[0]
                output_path = os.path.join(temp_dir, f"{base_name}_audio.mp3")

            # Load video and extract audio
            video = mp.VideoFileClip(video_path)
            audio = video.audio

            # Save audio to file
            audio.write_audiofile(output_path)

            return output_path

        except Exception as e:
            logger.error(
                f"Error extracting audio from video {video_path}: {str(e)}")
            return ""

    def _calculate_bitrate(self, audio: AudioSegment) -> int:
        """
        Calculate the bitrate of an audio file.

        Args:
            audio: AudioSegment object

        Returns:
            Bitrate in bits per second
        """
        return int((audio.frame_rate * audio.frame_width * audio.channels * 8))

    def _calculate_frame_rate(self, video_info: Dict) -> float:
        """
        Calculate the frame rate from ffmpeg video stream info.

        Args:
            video_info: Dictionary containing video stream information

        Returns:
            Frame rate as a float
        """
        # Try to get frame rate from avg_frame_rate
        if 'avg_frame_rate' in video_info:
            try:
                num, den = video_info['avg_frame_rate'].split('/')
                return float(num) / float(den)
            except (ValueError, ZeroDivisionError):
                pass

        # Try to get frame rate from r_frame_rate
        if 'r_frame_rate' in video_info:
            try:
                num, den = video_info['r_frame_rate'].split('/')
                return float(num) / float(den)
            except (ValueError, ZeroDivisionError):
                pass

        return 0.0

    def _extract_id3_tags(self, file_path: str) -> Dict[str, str]:
        """
        Extract ID3 tags from an MP3 file.

        Args:
            file_path: Path to the MP3 file

        Returns:
            Dictionary containing ID3 tag information
        """
        try:
            # This is a simplified implementation
            # In a real implementation, you would use a library like mutagen
            # to extract ID3 tags properly
            tags = {}

            # TODO: Implement proper ID3 tag extraction
            # This is a placeholder for now

            return tags

        except Exception as e:
            logger.error(
                f"Error extracting ID3 tags from {file_path}: {str(e)}")
            return {}
