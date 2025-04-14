from lt_app.transcriber import LiveTranscriber

def start_transcriber():
    transcriber = LiveTranscriber(
        model_size='large-v3',  # Options: tiny, base, small, medium, large
        use_vad=True,
        correct_sentences=True,
        device='cuda'  # Use 'cpu' if CUDA is unavailable
    )

    for transcription in transcriber.listen():
        print(f"[Transcription] {transcription}")