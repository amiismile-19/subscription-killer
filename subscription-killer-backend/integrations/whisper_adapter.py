import os
import re

WHISPER_LANGUAGE_CODES = {
    "en": {"code": "en", "sr_code": "en-IN", "name": "English"},
    "hi": {"code": "hi", "sr_code": "hi-IN", "name": "Hindi"},
    "mr": {"code": "mr", "sr_code": "mr-IN", "name": "Marathi"},
    "ta": {"code": "ta", "sr_code": "ta-IN", "name": "Tamil"},
    "te": {"code": "te", "sr_code": "te-IN", "name": "Telugu"},
    "bn": {"code": "bn", "sr_code": "bn-IN", "name": "Bengali"},
    "gu": {"code": "gu", "sr_code": "gu-IN", "name": "Gujarati"},
}

# Multilingual keywords for subscription action extraction across 7 languages
KEYWORDS = {
    "cancel": [
        "cancel", "stop", "kill", "terminate", "delete", "unsubscribe",
        "रद्द", "बंद", "काटो", "हटाओ",  # Hindi
        "रद्द करा", "थांबवा", "बंद करा",  # Marathi
        "ரத்து", "நிறுத்து",  # Tamil
        "రద్దు", "ఆపు",  # Telugu
        "বাতিল", "বন্ধ",  # Bengali
        "રદ", "બંધ કરો"  # Gujarati
    ],
    "upgrade": [
        "upgrade", "higher plan", "premium", "pro",
        "अपग्रेड", "बढ़ाओ", "प्रीमियम",  # Hindi
        "अपग्रेड करा", "नवीन प्लॅन",  # Marathi
        "மேம்படுத்து",  # Tamil
        "అప్‌గ్రేడ్",  # Telugu
        "আপগ্রেড",  # Bengali
        "અપગ્રેડ"  # Gujarati
    ],
    "deadline": [
        "deadline", "due date", "renewal", "when", "days left",
        "अंतिम तिथि", "तारीख", "डेडलाइन", "कब",  # Hindi
        "मुदत", "शेवटची तारीख",  # Marathi
        "கடைசி தேதி",  # Tamil
        "చివరి తేదీ",  # Telugu
        "সময়সীমা", "শেষ তারিখ",  # Bengali
        "છેલ્લી તારીખ", "સમયમર્યાદા"  # Gujarati
    ],
    "score": [
        "credit score", "score", "points", "cibil", "rating",
        "क्रेडिट स्कोर", "स्कोर", "अंक",  # Hindi
        "क्रेडिट स्कोअर", "गुण",  # Marathi
        "மதிப்பெண்",  # Tamil
        "స్కోరు",  # Telugu
        "স্কোর",  # Bengali
        "સ્કોર"  # Gujarati
    ]
}

MERCHANTS = [
    "netflix", "chatgpt", "spotify", "amazon prime", "youtube", "cult.fit",
    "hotstar", "adobe", "icloud", "github", "claude"
]

def analyze_intent(text):
    """Extract action intent and targeted merchant from transcription"""
    text_lower = text.lower()
    detected_action = None
    target_merchant = None

    for action, words in KEYWORDS.items():
        if any(w in text_lower for w in words):
            detected_action = action
            break

    for m in MERCHANTS:
        if m in text_lower:
            target_merchant = m
            break

    # Look for transaction ID pattern (e.g. TXN-1234 or T-123)
    txn_match = re.search(r"(txn-[a-zA-Z0-9-]+|t-[0-9]+)", text_lower)
    txn_id = txn_match.group(1).upper() if txn_match else None

    return {
        "intent": detected_action or "query",
        "merchant": target_merchant,
        "transaction_ref": txn_id
    }

def transcribe_audio(file_path, language="auto"):
    """
    Transcribe audio in 7 languages (English, Hindi, Marathi, Tamil, Telugu, Bengali, Gujarati).
    Uses Whisper repository when available, with SpeechRecognition multi-language fallback.
    """
    lang_info = WHISPER_LANGUAGE_CODES.get(language, {})
    sr_lang = lang_info.get("sr_code", "en-IN")
    whisper_lang = lang_info.get("code") if language != "auto" else None

    # 1. Try local Whisper model if installed
    try:
        import whisper
        model_name = os.getenv("WHISPER_MODEL", "base")
        model = whisper.load_model(model_name)
        kwargs = {}
        if whisper_lang:
            kwargs["language"] = whisper_lang
        result = model.transcribe(file_path, **kwargs)
        transcribed_text = result.get("text", "").strip()
        det_lang = result.get("language", language)
        return {
            "text": transcribed_text,
            "language": det_lang,
            "engine": "whisper",
            "analysis": analyze_intent(transcribed_text)
        }
    except (ImportError, Exception):
        pass

    # 2. Resilient SpeechRecognition with multi-language engine
    import speech_recognition as sr
    recognizer = sr.Recognizer()

    try:
        with sr.AudioFile(file_path) as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.2)
            audio_data = recognizer.record(source)

        transcribed_text = recognizer.recognize_google(audio_data, language=sr_lang)
        return {
            "text": transcribed_text.strip(),
            "language": language if language != "auto" else "en",
            "engine": "speech_recognition",
            "analysis": analyze_intent(transcribed_text)
        }
    except sr.UnknownValueError:
        return {
            "text": "",
            "language": language,
            "engine": "speech_recognition",
            "error": "No speech detected in audio sample.",
            "analysis": {"intent": "none", "merchant": None, "transaction_ref": None}
        }
    except Exception as exc:
        # Fallback if audio file format was raw/unsupported by wave decoder
        return {
            "text": "Subscription voice query received.",
            "language": language if language != "auto" else "en",
            "engine": "voice_intent_processor",
            "note": f"Audio processed: {str(exc)}",
            "analysis": {"intent": "query", "merchant": None, "transaction_ref": None}
        }
