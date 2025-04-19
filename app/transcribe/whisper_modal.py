import tempfile
import wave
import psutil
import GPUtil
import threading
import time
from faster_whisper import WhisperModel
from app.config import DUNGEON_ALIASES

# Globals
current_model = None
current_model_size = None
model_small = None
model_tiny = None
memory_watchdog_thread = None

def build_initial_prompt():
    dungeon_list = ", ".join(DUNGEON_ALIASES.keys())
    static_keywords = "Coords, Dungeon, Boss, Spawn, Ocean Boss, Red Alert"
    prompt = f"Ultima Online dungeons: {dungeon_list}, {static_keywords}"
    return prompt

def preload_whisper_models():
    global model_small, model_tiny, current_model, current_model_size

    initial_prompt = build_initial_prompt()

    try:
        print(f"[WhisperLoader] 🔥 Loading small.en model...")
        model_small = WhisperModel(
            "small.en",
            compute_type="float16",
            initial_prompt=initial_prompt
        )
        print(f"[WhisperLoader] ✅ small.en loaded!")

    except Exception as e:
        print(f"[WhisperLoader] ❌ Failed to load small.en: {e}")
        model_small = None

    try:
        print(f"[WhisperLoader] 🔥 Loading tiny.en model...")
        model_tiny = WhisperModel(
            "tiny.en",
            compute_type="float16",
            initial_prompt=initial_prompt
        )
        print(f"[WhisperLoader] ✅ tiny.en loaded!")

    except Exception as e:
        print(f"[WhisperLoader] ❌ Failed to load tiny.en: {e}")
        model_tiny = None

    # Default start with small if available
    if model_small:
        current_model = model_small
        current_model_size = "small.en"
    elif model_tiny:
        current_model = model_tiny
        current_model_size = "tiny.en"
    else:
        print("[WhisperLoader] 🚨 FATAL: No whisper models could be loaded.")
        current_model = None

def get_gpu_memory_percent():
    try:
        gpus = GPUtil.getGPUs()
        if not gpus:
            return 0
        gpu = gpus[0]
        return (gpu.memoryUsed / gpu.memoryTotal) * 100
    except Exception as e:
        print(f"[MemoryWatchdog] ⚠️ Failed to read GPU memory: {e}")
        return 0

def memory_watchdog(threshold_high=85, threshold_low=60):
    global current_model, current_model_size

    print("[MemoryWatchdog] 🚀 Watchdog started, monitoring CPU/GPU memory...")

    while True:
        mem = psutil.virtual_memory()
        cpu_mem_percent = mem.percent
        gpu_mem_percent = get_gpu_memory_percent()

        print(f"[MemoryWatchdog] 📊 CPU: {cpu_mem_percent:.1f}%, GPU: {gpu_mem_percent:.1f}%")

        # Downgrade if high
        if (cpu_mem_percent >= threshold_high or gpu_mem_percent >= threshold_high) and current_model_size == "small.en":
            print(f"[MemoryWatchdog] ⚠️ High memory detected. Downgrading to tiny.en...")
            if model_tiny:
                current_model = model_tiny
                current_model_size = "tiny.en"
                print("[MemoryWatchdog] ✅ Instantly switched to tiny.en!")
            else:
                print("[MemoryWatchdog] ❌ tiny.en not available!")

        # Upgrade if low
        if (cpu_mem_percent <= threshold_low and gpu_mem_percent <= threshold_low) and current_model_size == "tiny.en":
            print(f"[MemoryWatchdog] 🚀 Low memory detected. Upgrading to small.en...")
            if model_small:
                current_model = model_small
                current_model_size = "small.en"
                print("[MemoryWatchdog] ✅ Instantly switched to small.en!")
            else:
                print("[MemoryWatchdog] ❌ small.en not available!")

        time.sleep(5)

def start_memory_watchdog(threshold_high=85, threshold_low=60):
    global memory_watchdog_thread
    if memory_watchdog_thread is None:
        memory_watchdog_thread = threading.Thread(target=memory_watchdog, args=(threshold_high, threshold_low), daemon=True)
        memory_watchdog_thread.start()

# PCM to WAV
def save_pcm_to_wav(pcm_data: bytes, filename: str, rate: int = 48000):
    with wave.open(filename, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(rate)
        wf.writeframes(pcm_data)

# Transcription
async def transcribe_audio_buffer(pcm_data: bytes) -> str:
    global current_model, current_model_size
    if current_model is None:
        print("❌ No Whisper model loaded.")
        return ""

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_wav:
        save_pcm_to_wav(pcm_data, temp_wav.name)
        try:
            segments, _ = current_model.transcribe(temp_wav.name)
            transcript = " ".join(segment.text for segment in segments).strip()

            # ✨ NEW ✨ Debug log showing which model was used
            print(f"[Transcription:{current_model_size}] {transcript}")

            return transcript
        except Exception as e:
            print(f"❌ Whisper error: {e}")
            return ""

# --- Initialize everything at startup ---
preload_whisper_models()
start_memory_watchdog()
