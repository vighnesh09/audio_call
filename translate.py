import logging
import os
import time
import threading
from datetime import datetime
from collections import deque
import io

# Get logger but don't configure it here
logger = logging.getLogger(__name__)  # This will be 'translate'

# Create a directory for saving audio files
os.makedirs("audio_recordings", exist_ok=True)

# Configurable audio duration in seconds
AUDIO_DURATION_SECONDS = 1.0  # You can adjust this value

# Audio buffer to collect chunks until we reach desired duration
class AudioCollector:
    def __init__(self, duration_seconds=AUDIO_DURATION_SECONDS):
        self.duration_seconds = duration_seconds
        self.buffer = bytearray()
        self.last_save_time = time.time()
        self.lock = threading.Lock()
        # Estimate bytes per second - will be adjusted dynamically
        self.bytes_per_second = 24000  # Initial estimate

    def add_chunk(self, audio_data):
        with self.lock:
            self.buffer.extend(audio_data)
            # Dynamically adjust bytes per second based on incoming data
            elapsed = time.time() - self.last_save_time
            if elapsed > 0.1:  # Only adjust if some time has passed
                current_rate = len(self.buffer) / elapsed
                # Smoothed average to prevent wild fluctuations
                self.bytes_per_second = (self.bytes_per_second * 0.8) + (current_rate * 0.2)
            
            # Check if we have enough data for our duration
            target_size = int(self.duration_seconds * self.bytes_per_second)
            if len(self.buffer) >= target_size:
                # Save the audio data in a separate thread to avoid blocking
                audio_to_save = bytes(self.buffer[:target_size])
                self.buffer = self.buffer[target_size:]
                self.last_save_time = time.time()
                threading.Thread(target=self._save_audio_file, args=(audio_to_save,)).start()

    def _save_audio_file(self, audio_data):
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"audio_recordings/audio_{self.duration_seconds}sec_{timestamp}.webm"
            
            with open(filename, "wb") as f:
                f.write(audio_data)
            
            logger.info(f"Saved {len(audio_data)} bytes ({self.duration_seconds}s) audio to {filename}")
        except Exception as e:
            logger.error(f"Failed to save audio file: {e}")

# Create the global audio collector
audio_collector = AudioCollector(AUDIO_DURATION_SECONDS)

def process_audio_for_translation(audio_data: bytes) -> bytes:
    """
    Receives audio data from the websocket, collects it into 1-second chunks,
    and saves them to files without interrupting the audio flow.
    
    Args:
        audio_data: Raw bytes from WebSocket
        
    Returns:
        The same audio data (unmodified)
    """
    # Log receiving the audio data
    logger.info(f"Received audio chunk: {len(audio_data)} bytes")
    
    # Add to audio collector without blocking
    audio_collector.add_chunk(audio_data)
    
    # Return the original data immediately to maintain real-time flow
    return audio_data

def set_audio_duration(seconds: float):
    """
    Change the duration of audio files being saved.
    
    Args:
        seconds: New duration in seconds
    """
    global audio_collector
    global AUDIO_DURATION_SECONDS
    
    AUDIO_DURATION_SECONDS = seconds
    audio_collector = AudioCollector(seconds)
    logger.info(f"Set audio recording duration to {seconds} seconds") 