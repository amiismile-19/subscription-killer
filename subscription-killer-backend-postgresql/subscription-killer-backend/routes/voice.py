import os
import tempfile
from flask import Blueprint, jsonify, request, current_app
from integrations.whisper_adapter import transcribe_audio
from integrations.bhashini_adapter import text_to_speech

bp = Blueprint("voice", __name__)

@bp.post("/transcribe")
def transcribe():
    uploaded = request.files.get("audio")
    if not uploaded or not uploaded.filename:
        return jsonify(error="Upload an audio file in multipart field 'audio'"), 400
    suffix = os.path.splitext(uploaded.filename)[1][:10] or ".audio"
    path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp:
            path = temp.name
            uploaded.save(path)
        result = transcribe_audio(path)
        return jsonify(result)
    except RuntimeError as exc:
        return jsonify(error=str(exc)), 501
    finally:
        if path and os.path.exists(path):
            os.remove(path)

@bp.post("/speak")
def speak():
    data = request.get_json(silent=True) or {}
    text = str(data.get("text", "")).strip()
    language = str(data.get("language", "hi"))
    if not text:
        return jsonify(error="text is required"), 400
    try:
        result = text_to_speech(text, language)
        return jsonify(result)
    except (RuntimeError, NotImplementedError) as exc:
        return jsonify(error=str(exc)), 501
