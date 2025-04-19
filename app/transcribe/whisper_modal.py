import tempfile
import wave
import psutil
import GPUtil
import threading
import time
import gc
from faster_whisper import WhisperModel
from app.config import DUNGEON_ALIASES

# Globals
current_model = None
current_model_size = None
memory_watchdog_thread = None

# Model paths (cache)
model_paths = {
    "base.en": None,
    "small.en": None,
}

# Smoothing window (keep track of last N memory/load values)
gpu_mem_history = []
gpu_load_history = []
SMOOTH_WINDOW = 12  # 12 samples at 5s = 1 minute


def build_initial_prompt():
    dungeon_list = ", ".join(DUNGEON_ALIASES.keys())
    static_keywords = "Coords, Dungeon, Boss, Spawn, Ocean Boss, Red Alert, Jarvis, panic, stop panic, start event, stop event, announce event, cancel event"
    return f"Ultima Online dungeons: {dungeon_list}, {static_keywords}"


def load_model(model_size):
    try:
        print(f"[WhisperLoader] 🔥 Loading {model_size} model...")
        model = WhisperModel(
            model_size,
            compute_type="float16"
        )
        model_paths[model_size] = model
        print(f"[WhisperLoader] ✅ {model_size} loaded!")
        return model
    except Exception as e:
        print(f"[WhisperLoader] ❌ Failed to load {model_size}: {e}")
        return None


def unload_current_model():
    global current_model
    if current_model:
        print(f"[WhisperLoader] 🔥 Unloading {current_model_size} model...")
        del current_model
        current_model = None
        gc.collect()


def preload_base_model():
    global current_model, current_model_size
    current_model = load_model("base.en")
    if current_model:
        current_model_size = "base.en"
    else:
        print("[WhisperLoader] 🚨 FATAL: Could not preload base.en. Exiting.")


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


def get_gpu_load_percent():
    try:
        gpus = GPUtil.getGPUs()
        if not gpus:
            return 0
        gpu = gpus[0]
        return gpu.load * 100
    except Exception as e:
        print(f"[MemoryWatchdog] ⚠️ Failed to read GPU load: {e}")
        return 0


def memory_watchdog(threshold_high=85, threshold_low=50):
    global current_model, current_model_size
    global gpu_mem_history, gpu_load_history

    print("[MemoryWatchdog] 🚀 Watchdog started, monitoring GPU memory and load...")

    while True:
        gpu_mem = get_gpu_memory_percent()
        gpu_load = get_gpu_load_percent()

        gpu_mem_history.append(gpu_mem)
        gpu_load_history.append(gpu_load)

        if len(gpu_mem_history) > SMOOTH_WINDOW:
            gpu_mem_history.pop(0)
        if len(gpu_load_history) > SMOOTH_WINDOW:
            gpu_load_history.pop(0)

        avg_gpu_mem = sum(gpu_mem_history) / len(gpu_mem_history)
        avg_gpu_load = sum(gpu_load_history) / len(gpu_load_history)

        print(f"[MemoryWatchdog] 📊 GPU Mem: {avg_gpu_mem:.1f}%, GPU Load: {avg_gpu_load:.1f}% (avg {len(gpu_mem_history)} samples)")

        # Downgrade if high GPU load
        if (avg_gpu_load >= threshold_high):
            if current_model_size == "base.en":
                print("⚡ High GPU load detected, downgrading to small.en")
                unload_current_model()
                current_model = model_paths.get("small.en") or load_model("small.en")
                current_model_size = "small.en"

        # Upgrade if low
        if (avg_gpu_mem <= threshold_low and avg_gpu_load <= threshold_low):
            if current_model_size == "small.en":
                print("🚀 Upgrading back to base.en (GPU load normal)")
                unload_current_model()
                current_model = model_paths.get("base.en") or load_model("base.en")
                current_model_size = "base.en"

        time.sleep(5)


def start_memory_watchdog(threshold_high=85, threshold_low=50):
    global memory_watchdog_thread
    if memory_watchdog_thread is None:
        memory_watchdog_thread = threading.Thread(target=memory_watchdog, args=(threshold_high, threshold_low), daemon=True)
        memory_watchdog_thread.start()


# PCM to WAV

def save_pcm_to_wav(pcm_data: bytes, filename: str, rate: int = 48000):
    with wave.open(filename, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
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
            initial_prompt = build_initial_prompt()
            segments, _ = current_model.transcribe(temp_wav.name, initial_prompt=initial_prompt)
            transcript = " ".join(segment.text for segment in segments).strip()
            print(f"[Transcription:{current_model_size}] {transcript}")
            return transcript
        except Exception as e:
            print(f"❌ Whisper error while using {current_model_size}: {e}")
            # On error, fallback to smaller model
            if current_model_size == "base.en":
                print("⚡ Downgrading to small.en due to transcription error.")
                unload_current_model()
                current_model = model_paths.get("small.en") or load_model("small.en")
                current_model_size = "small.en"
                return await transcribe_audio_buffer(pcm_data)
            return ""


def force_use_base_model():
    global current_model, current_model_size
    unload_current_model()
    current_model = model_paths.get("base.en") or load_model("base.en")
    current_model_size = "base.en"
    print("🛠️ Manually switched to base.en")


def force_use_small_model():
    global current_model, current_model_size
    unload_current_model()
    current_model = model_paths.get("small.en") or load_model("small.en")
    current_model_size = "small.en"
    print("🛠️ Manually switched to small.en")


# --- Initialize everything at startup ---
preload_base_model()
start_memory_watchdog()
