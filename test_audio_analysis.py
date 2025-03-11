"""
Simple direct test of audio analysis using librosa
"""

import os
import sys
import logging
import numpy as np
import librosa
import matplotlib.pyplot as plt
from pprint import pprint

# Set up logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("AudioAnalysisTest")

def analyze_audio(audio_path):
    """Test the audio analysis features directly using librosa"""
    logger.info(f"Analyzing audio file: {audio_path}")
    
    if not os.path.exists(audio_path):
        logger.error(f"Audio file not found: {audio_path}")
        return False
    
    try:
        # Load the audio file with librosa
        y, sr = librosa.load(audio_path, sr=None)
        logger.info(f"Loaded audio file: sample rate = {sr}, duration = {librosa.get_duration(y=y, sr=sr):.2f}s")
        
        # Extract tempo and beat information
        onset_env = librosa.onset.onset_strength(y=y, sr=sr)
        tempo = librosa.beat.tempo(onset_envelope=onset_env, sr=sr)[0]
        logger.info(f"Detected tempo: {tempo:.2f} BPM")
        
        # Beat tracking
        _, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
        beat_times = librosa.frames_to_time(beat_frames, sr=sr)
        logger.info(f"Detected {len(beat_times)} beats")
        
        # Spectral features
        spectral_centroid = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
        spectral_bandwidth = librosa.feature.spectral_bandwidth(y=y, sr=sr)[0]
        
        logger.info(f"Average spectral centroid: {np.mean(spectral_centroid):.2f}")
        logger.info(f"Average spectral bandwidth: {np.mean(spectral_bandwidth):.2f}")
        
        # Generate a simple waveform visualization
        plt.figure(figsize=(10, 4))
        plt.plot(librosa.times_like(y), y)
        plt.title(f"Waveform - Tempo: {tempo:.2f} BPM")
        plt.xlabel("Time (s)")
        plt.ylabel("Amplitude")
        
        # Save the waveform
        output_path = os.path.splitext(audio_path)[0] + "_waveform.png"
        plt.savefig(output_path)
        plt.close()
        
        logger.info(f"Saved waveform to: {output_path}")
        
        # Calculate chromagram (tonal content)
        chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
        
        # Average values for each pitch class
        avg_chroma = [float(np.mean(pitch)) for pitch in chroma]
        
        # Get the dominant pitch class (0=C, 1=C#, ..., 11=B)
        dominant_pitch_idx = int(np.argmax(avg_chroma))
        pitch_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        dominant_pitch = pitch_names[dominant_pitch_idx]
        
        logger.info(f"Dominant pitch: {dominant_pitch}")
        
        # Return an analysis results dictionary
        results = {
            'tempo': float(tempo),
            'beat_count': len(beat_times),
            'beat_times': beat_times.tolist(),
            'spectral_centroid': float(np.mean(spectral_centroid)),
            'spectral_bandwidth': float(np.mean(spectral_bandwidth)),
            'dominant_pitch': dominant_pitch,
            'sample_rate': sr,
            'duration': float(librosa.get_duration(y=y, sr=sr)),
            'waveform_path': output_path
        }
        
        logger.info("Audio analysis completed successfully")
        return results
    
    except Exception as e:
        logger.error(f"Error analyzing audio: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    """Main test function"""
    
    # Check for command line arguments
    if len(sys.argv) > 1:
        audio_path = sys.argv[1]
    else:
        audio_path = "test_files/test_audio.wav"
        
    if not os.path.exists(audio_path):
        logger.error(f"Audio file not found: {audio_path}")
        return False
    
    logger.info(f"Testing audio analysis with file: {audio_path}")
    results = analyze_audio(audio_path)
    
    if results:
        logger.info("Analysis results:")
        pprint(results)
        return True
    else:
        logger.error("Audio analysis failed")
        return False

if __name__ == "__main__":
    main()