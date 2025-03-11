"""
Advanced Audio Features Module for AI Document Organizer V2.

This module provides functions for extracting advanced audio features:
- Harmonic content analysis
- Musical key detection
- Genre classification (basic)
- Voice/instrumental detection
- Audio segmentation

These computationally intensive features are optimized for performance
and can be selectively enabled based on system resources.
"""

import os
import logging
import numpy as np
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger("AIDocumentOrganizerV2.AudioAnalyzer.AdvancedFeatures")

# Try importing required libraries
try:
    import librosa
    import librosa.feature
    import librosa.display
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False

# Musical key mapping
PITCH_CLASS_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

# Major and minor scales (1 = in scale, 0 = not in scale)
MAJOR_SCALE = [1, 0, 1, 0, 1, 1, 0, 1, 0, 1, 0, 1]  # W-W-H-W-W-W-H pattern
MINOR_SCALE = [1, 0, 1, 1, 0, 1, 0, 1, 1, 0, 1, 0]  # W-H-W-W-H-W-W pattern

def detect_musical_key(y: np.ndarray, sr: int) -> Dict[str, Any]:
    """
    Detect the musical key (tonal center) of an audio file.
    
    Args:
        y: Audio time series
        sr: Sample rate
        
    Returns:
        Dictionary with key detection results
    """
    if not LIBROSA_AVAILABLE:
        return {'error': "Librosa library not available"}
    
    try:
        # Compute chromagram (pitch class distribution)
        chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
        
        # Compute average chroma vector across entire song
        chroma_avg = np.mean(chroma, axis=1)
        
        # Calculate key detection
        major_corrs = []
        minor_corrs = []
        
        # Calculate correlation with major and minor scales in all keys
        for i in range(12):  # 12 possible keys
            # Rotate scale to match each possible key
            major_key = np.roll(MAJOR_SCALE, i)
            minor_key = np.roll(MINOR_SCALE, i)
            
            # Correlation with major key
            major_corr = np.corrcoef(chroma_avg, major_key)[0, 1]
            major_corrs.append(major_corr)
            
            # Correlation with minor key
            minor_corr = np.corrcoef(chroma_avg, minor_key)[0, 1]
            minor_corrs.append(minor_corr)
        
        # Find the highest correlation
        max_major_idx = np.argmax(major_corrs)
        max_minor_idx = np.argmax(minor_corrs)
        
        max_major_corr = major_corrs[max_major_idx]
        max_minor_corr = minor_corrs[max_minor_idx]
        
        # Determine overall key (major or minor)
        if max_major_corr > max_minor_corr:
            key_idx = max_major_idx
            is_major = True
            strength = max_major_corr
        else:
            key_idx = max_minor_idx
            is_major = False
            strength = max_minor_corr
        
        # Format the key name
        key_name = PITCH_CLASS_NAMES[key_idx]
        scale_type = "major" if is_major else "minor"
        
        # Calculate key strength (how confident we are in the key detection)
        key_strength = float(strength)
        
        # Compile key information
        key_info = {
            'key': f"{key_name} {scale_type}",
            'root_note': key_name,
            'scale': scale_type,
            'confidence': key_strength,
            'pitch_profile': chroma_avg.tolist()
        }
        
        # Add alternate interpretations
        alternates = []
        
        # Get relative major/minor
        if is_major:
            relative_minor_idx = (key_idx + 9) % 12  # Relative minor is 3 semitones down
            alternates.append({
                'key': f"{PITCH_CLASS_NAMES[relative_minor_idx]} minor",
                'confidence': max_minor_corr
            })
        else:
            relative_major_idx = (key_idx + 3) % 12  # Relative major is 3 semitones up
            alternates.append({
                'key': f"{PITCH_CLASS_NAMES[relative_major_idx]} major",
                'confidence': max_major_corr
            })
        
        # Add dominant key as alternate
        dominant_idx = (key_idx + 7) % 12  # Dominant is 7 semitones up
        dominant_corr = major_corrs[dominant_idx]
        alternates.append({
            'key': f"{PITCH_CLASS_NAMES[dominant_idx]} major",
            'confidence': dominant_corr
        })
        
        key_info['alternates'] = alternates
        
        return key_info
        
    except Exception as e:
        logger.error(f"Error in key detection: {e}")
        return {'error': str(e)}

def analyze_harmonic_content(y: np.ndarray, sr: int) -> Dict[str, Any]:
    """
    Analyze the harmonic content of an audio file.
    
    Args:
        y: Audio time series
        sr: Sample rate
        
    Returns:
        Dictionary with harmonic analysis results
    """
    if not LIBROSA_AVAILABLE:
        return {'error': "Librosa library not available"}
    
    try:
        # Calculate harmonic and percussive components
        y_harmonic, y_percussive = librosa.effects.hpss(y)
        
        # Calculate harmonic ratio (proportion of harmonic energy)
        harmonic_energy = np.sum(y_harmonic**2)
        percussive_energy = np.sum(y_percussive**2)
        total_energy = harmonic_energy + percussive_energy
        
        # Avoid division by zero
        if total_energy > 0:
            harmonic_ratio = harmonic_energy / total_energy
        else:
            harmonic_ratio = 0.5
        
        # Compute spectral features on harmonic component
        cent = librosa.feature.spectral_centroid(y=y_harmonic, sr=sr)[0]
        flatness = librosa.feature.spectral_flatness(y=y_harmonic)[0]
        
        # Calculate tonal vs. noise characteristics
        tonal_index = np.mean(flatness)  # Higher flatness = more noise-like
        
        # Calculate spectral contrast for each frame
        contrast = librosa.feature.spectral_contrast(y=y_harmonic, sr=sr)
        
        # Harmonic profile ratings
        harmonicity = 1.0 - tonal_index  # Higher value = more harmonic/tonal
        
        # Calculate energy distribution in frequency bands (simple)
        n_bands = 5
        fft_size = 2048
        S = np.abs(librosa.stft(y_harmonic, n_fft=fft_size))
        
        # Define frequency bands (rough approximation)
        band_edges = np.logspace(np.log10(20), np.log10(sr/2), n_bands+1)
        
        # Convert frequency to FFT bin indices
        bin_edges = np.round(band_edges / sr * fft_size).astype(int)
        bin_edges = np.minimum(bin_edges, S.shape[0])
        
        # Calculate energy in each band
        band_energies = []
        for i in range(n_bands):
            band_energy = np.mean(np.sum(S[bin_edges[i]:bin_edges[i+1], :], axis=0))
            band_energies.append(float(band_energy))
        
        # Normalize band energies
        if sum(band_energies) > 0:
            band_energies = [e / sum(band_energies) for e in band_energies]
        
        # Compile harmonic analysis results
        harmonic_info = {
            'harmonic_ratio': float(harmonic_ratio),
            'harmonicity': float(harmonicity),
            'spectral_centroid': float(np.mean(cent)),
            'spectral_flatness': float(np.mean(flatness)),
            'spectral_contrast': float(np.mean(np.mean(contrast, axis=1))),
            'frequency_band_distribution': band_energies
        }
        
        # Add interpretation
        if harmonicity > 0.8:
            harmonic_info['character'] = "Highly tonal/harmonic"
        elif harmonicity > 0.6:
            harmonic_info['character'] = "Moderately tonal/harmonic"
        elif harmonicity > 0.4:
            harmonic_info['character'] = "Balanced tonal and noise components"
        elif harmonicity > 0.2:
            harmonic_info['character'] = "Moderately noise-like/percussive"
        else:
            harmonic_info['character'] = "Highly noise-like/percussive"
            
        # Calculate spectral brightness
        if np.mean(cent) > 5000:
            harmonic_info['brightness'] = "Very bright"
        elif np.mean(cent) > 3000:
            harmonic_info['brightness'] = "Bright"
        elif np.mean(cent) > 1500:
            harmonic_info['brightness'] = "Medium"
        else:
            harmonic_info['brightness'] = "Dark"
            
        return harmonic_info
        
    except Exception as e:
        logger.error(f"Error in harmonic analysis: {e}")
        return {'error': str(e)}
        
def detect_voice_instrumental(y: np.ndarray, sr: int) -> Dict[str, Any]:
    """
    Detect if audio contains vocals or is instrumental.
    
    Args:
        y: Audio time series
        sr: Sample rate
        
    Returns:
        Dictionary with vocal detection results
    """
    if not LIBROSA_AVAILABLE:
        return {'error': "Librosa library not available"}
    
    try:
        # Extract MFCCs
        mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=20)
        
        # Compute spectral contrast
        contrast = librosa.feature.spectral_contrast(y=y, sr=sr)
        
        # Vocal detection features (simplified version)
        # Typically, vocals have higher spectral contrast in mid-frequencies
        mid_contrast = np.mean(contrast[1:3, :])
        
        # Vocal presence estimation based on MFCCs
        # This is a simplified approach - a real solution would use machine learning
        mfcc_variance = np.var(mfccs, axis=1)
        
        # Approximate vocal detection - higher values suggest vocal presence
        # Note: This is a simplified approach without ML
        vocal_indicators = [
            float(mid_contrast),  # Mid-frequency contrast
            float(np.mean(mfcc_variance[2:6])),  # Variance in specific MFCC coefficients
            float(np.max(contrast[2, :]) - np.min(contrast[2, :]))  # Dynamic range in mid-freq contrast
        ]
        
        # Combine indicators (simplified)
        # Weight the indicators (these weights are approximate)
        weights = [0.5, 0.3, 0.2]
        vocal_score = sum(i * w for i, w in zip(vocal_indicators, weights))
        
        # Normalize to 0-1 range
        vocal_score = min(max(vocal_score / 10.0, 0), 1)
        
        # Basic threshold-based classification
        if vocal_score > 0.6:
            classification = "Vocal"
            confidence = vocal_score
        elif vocal_score < 0.4:
            classification = "Instrumental"
            confidence = 1 - vocal_score
        else:
            classification = "Mixed"
            confidence = 0.5 + abs(vocal_score - 0.5)
            
        return {
            'classification': classification,
            'confidence': float(confidence),
            'vocal_score': float(vocal_score)
        }
        
    except Exception as e:
        logger.error(f"Error in voice/instrumental detection: {e}")
        return {'error': str(e)}
        
def segment_audio(y: np.ndarray, sr: int, min_segment_length: float = 5.0) -> Dict[str, Any]:
    """
    Segment audio into distinct sections.
    
    Args:
        y: Audio time series
        sr: Sample rate
        min_segment_length: Minimum segment length in seconds
        
    Returns:
        Dictionary with segmentation results
    """
    if not LIBROSA_AVAILABLE:
        return {'error': "Librosa library not available"}
    
    try:
        # Compute novelty curve for segmentation
        S = np.abs(librosa.stft(y))
        
        # Calculate MFCC similarity
        mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
        
        # Get structural boundaries (simplified)
        boundaries = librosa.segment.agglomerative(S, min_segment_length * sr // 512)
        
        # Convert frames to time
        boundaries_times = librosa.frames_to_time(boundaries, sr=sr)
        
        # Add beginning and end times
        all_boundaries = np.concatenate([[0], boundaries_times, [len(y) / sr]])
        
        # Create segments
        segments = []
        
        for i in range(len(all_boundaries) - 1):
            start_time = all_boundaries[i]
            end_time = all_boundaries[i+1]
            
            segment = {
                'start': float(start_time),
                'end': float(end_time),
                'duration': float(end_time - start_time)
            }
            
            # Only include segments longer than minimum length
            if segment['duration'] >= min_segment_length:
                segments.append(segment)
                
        # Calculate segment similarities (cross-correlation)
        if len(segments) > 1:
            similarities = np.zeros((len(segments), len(segments)))
            
            # For each segment pair, compute similarity
            for i in range(len(segments)):
                start_i = int(segments[i]['start'] * sr)
                end_i = int(segments[i]['end'] * sr)
                
                # Handle boundary conditions
                start_i = max(0, start_i)
                end_i = min(len(y), end_i)
                
                segment_i = y[start_i:end_i]
                
                for j in range(len(segments)):
                    start_j = int(segments[j]['start'] * sr)
                    end_j = int(segments[j]['end'] * sr)
                    
                    # Handle boundary conditions
                    start_j = max(0, start_j)
                    end_j = min(len(y), end_j)
                    
                    segment_j = y[start_j:end_j]
                    
                    # Use a simpler comparison for long segments
                    if len(segment_i) > sr * 10 or len(segment_j) > sr * 10:
                        # Use spectral features instead of raw audio
                        spec_i = np.mean(librosa.feature.melspectrogram(y=segment_i, sr=sr), axis=1)
                        spec_j = np.mean(librosa.feature.melspectrogram(y=segment_j, sr=sr), axis=1)
                        
                        # Calculate correlation
                        similarities[i, j] = np.corrcoef(spec_i, spec_j)[0, 1]
                    else:
                        # For shorter segments, use cross-correlation
                        # Resample both to same length for comparison
                        max_len = 30 * sr  # 30 seconds max
                        target_len = min(max_len, max(len(segment_i), len(segment_j)))
                        
                        if len(segment_i) > 0 and len(segment_j) > 0:
                            # Resample to common length
                            seg_i_resampled = librosa.resample(segment_i, 
                                              orig_sr=sr, 
                                              target_sr=int(sr * target_len / len(segment_i)))
                                              
                            seg_j_resampled = librosa.resample(segment_j, 
                                              orig_sr=sr, 
                                              target_sr=int(sr * target_len / len(segment_j)))
                            
                            # Calculate correlation
                            similarities[i, j] = np.corrcoef(seg_i_resampled, seg_j_resampled)[0, 1]
                        else:
                            similarities[i, j] = 0
            
            # Find similar segments
            threshold = 0.8  # Similarity threshold
            similar_pairs = []
            
            for i in range(len(segments)):
                for j in range(i+1, len(segments)):
                    if similarities[i, j] > threshold:
                        similar_pairs.append((i, j, similarities[i, j]))
            
            # Group similar segments
            segment_groups = []
            processed = set()
            
            for i in range(len(segments)):
                if i in processed:
                    continue
                    
                # Create a new group
                group = [i]
                processed.add(i)
                
                # Find all segments similar to this one
                for j in range(len(segments)):
                    if j in processed or j == i:
                        continue
                        
                    if similarities[i, j] > threshold:
                        group.append(j)
                        processed.add(j)
                
                if len(group) > 1:
                    segment_groups.append({
                        'segments': group,
                        'similarity': float(np.mean([similarities[i, j] for j in group]))
                    })
            
            # Add group information to segments
            for group_idx, group in enumerate(segment_groups):
                for seg_idx in group['segments']:
                    segments[seg_idx]['group'] = group_idx
        
        return {
            'segments': segments,
            'count': len(segments)
        }
        
    except Exception as e:
        logger.error(f"Error in audio segmentation: {e}")
        return {'error': str(e)}

def analyze_advanced_features(y: np.ndarray, sr: int) -> Dict[str, Any]:
    """
    Perform comprehensive advanced audio analysis.
    
    Args:
        y: Audio time series
        sr: Sample rate
        
    Returns:
        Dictionary with all advanced analysis results
    """
    if not LIBROSA_AVAILABLE:
        return {'error': "Librosa library not available"}
        
    try:
        # Initialize results
        result = {'success': True}
        
        # Get musical key
        key_info = detect_musical_key(y, sr)
        if 'error' not in key_info:
            result['key_info'] = key_info
        
        # Get harmonic content
        harmonic_info = analyze_harmonic_content(y, sr)
        if 'error' not in harmonic_info:
            result['harmonic_info'] = harmonic_info
        
        # Get voice/instrumental detection
        vocal_info = detect_voice_instrumental(y, sr)
        if 'error' not in vocal_info:
            result['vocal_info'] = vocal_info
        
        # Get audio segmentation (only for longer audio)
        if len(y) > 30 * sr:  # Only for audio > 30 seconds
            segment_info = segment_audio(y, sr)
            if 'error' not in segment_info:
                result['segment_info'] = segment_info
        
        return result
        
    except Exception as e:
        logger.error(f"Error in advanced audio analysis: {e}")
        return {'success': False, 'error': str(e)}