import logging
import os
import time
from datetime import datetime

# Get logger but don't configure it here
logger = logging.getLogger(__name__)  # This will be 'translate'

# Create directory for audio files if it doesn't exist
AUDIO_DIR = "audio_files"
os.makedirs(AUDIO_DIR, exist_ok=True)

def process_audio_for_translation(audio_data: bytes) -> bytes:
    """
    Receives audio data from the websocket, logs it, and saves it as an audio file.
    
    Args:
        audio_data: Raw bytes from WebSocket
        
    Returns:
        The same audio data (unmodified for now)
    """
    # Log receiving the audio data
    logger.info(f"Received audio data for translation: {len(audio_data)} bytes")
    
    try:
        # Generate a unique filename using timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"{AUDIO_DIR}/audio_{timestamp}.webm"
        
        # Save the audio data to file
        with open(filename, "wb") as f:
            f.write(audio_data)
        
        logger.info(f"Saved audio data to {filename}")
    except Exception as e:
        logger.error(f"Error saving audio file: {e}")
    
    # Just return the same data for now
    return audio_data 