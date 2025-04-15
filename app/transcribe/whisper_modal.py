import tempfile
import wave
from faster_whisper import WhisperModel

# Load model once
model = WhisperModel("base", compute_type="float16")

def save_pcm_to_wav(pcm_data: bytes, filename: str, rate: int = 48000):
    """Convert raw PCM bytes to a WAV file."""
    with wave.open(filename, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(rate)
        wf.writeframes(pcm_data)

async def transcribe_audio_buffer(pcm_data: bytes) -> str:
    """Save buffer to a temp WAV and run Whisper transcription."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_wav:
        save_pcm_to_wav(pcm_data, temp_wav.name)
        try:
            segments, _ = model.transcribe(temp_wav.name)
            return " ".join(segment.text for segment in segments).strip()
        except Exception as e:
            print(f"❌ Whisper error: {e}")
            return ""