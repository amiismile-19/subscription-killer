import os

def transcribe_audio(file_path):
    """Optional local Whisper integration. Install openai-whisper and ffmpeg."""
    try:
        import whisper
    except ImportError as exc:
        raise RuntimeError("Whisper is optional. Install it with: pip install openai-whisper") from exc
    model = whisper.load_model(os.getenv("WHISPER_MODEL", "base"))
    result = model.transcribe(file_path)
    return {"text": result.get("text", "").strip(), "language": result.get("language")}
