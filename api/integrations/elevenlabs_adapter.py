import os
import io
import base64
import requests

# Curated ElevenLabs voices known for high multilingual and linguistic fidelity
CURATED_VOICES = [
    {
        "voice_id": "21m00Tcm4TlvDq8ikWAM",
        "name": "Rachel",
        "category": "premade",
        "description": "Calm, clear, natural multilingual narrator",
        "labels": {"accent": "american", "gender": "female", "use_case": "narration"}
    },
    {
        "voice_id": "pNInz6obpgDQGcFmaJgB",
        "name": "Adam",
        "category": "premade",
        "description": "Warm, deep, conversational multilingual assistant",
        "labels": {"accent": "american", "gender": "male", "use_case": "conversational"}
    },
    {
        "voice_id": "9BWtsMINqrJLrRacOk9x",
        "name": "Aria",
        "category": "premade",
        "description": "Expressive, bright, engaging financial copilot",
        "labels": {"accent": "american", "gender": "female", "use_case": "news/copilot"}
    },
    {
        "voice_id": "IKne3meq5aSn9XLyUdCD",
        "name": "Charlie",
        "category": "premade",
        "description": "Casual, confident, authoritative tone",
        "labels": {"accent": "australian", "gender": "male", "use_case": "conversational"}
    },
    {
        "voice_id": "EXAVITQu4vr4xnSDxMaL",
        "name": "Sarah",
        "category": "premade",
        "description": "Soft, professional, helpful customer advisory",
        "labels": {"accent": "american", "gender": "female", "use_case": "support"}
    },
    {
        "voice_id": "JBFqnCBsd6RMkjVDRZzb",
        "name": "George",
        "category": "premade",
        "description": "Warm, raspy British narrator",
        "labels": {"accent": "british", "gender": "male", "use_case": "narration"}
    },
    {
        "voice_id": "XB0fDUnXU5powFXDhCwa",
        "name": "Charlotte",
        "category": "premade",
        "description": "Seductive, articulate Swedish-accented English",
        "labels": {"accent": "swedish", "gender": "female", "use_case": "characters"}
    },
    {
        "voice_id": "onwK4e9ZLuTAKqWW03F9",
        "name": "Daniel",
        "category": "premade",
        "description": "Authoritative British broadcaster",
        "labels": {"accent": "british", "gender": "male", "use_case": "news"}
    }
]

SUPPORTED_MODELS = [
    {
        "model_id": "eleven_multilingual_v2",
        "name": "Eleven Multilingual v2",
        "description": "State-of-the-art multilingual model supporting 29+ languages including English, Hindi, Bengali, Tamil, Telugu, Marathi, Gujarati.",
        "can_do_text_to_speech": True
    },
    {
        "model_id": "eleven_turbo_v2_5",
        "name": "Eleven Turbo v2.5",
        "description": "Ultra low-latency multilingual speech model optimized for conversational agents.",
        "can_do_text_to_speech": True
    },
    {
        "model_id": "eleven_flash_v2",
        "name": "Eleven Flash v2",
        "description": "Blazing fast inference (approx 75ms) for real-time voice copilots.",
        "can_do_text_to_speech": True
    }
]

def get_api_key(passed_key=None):
    if passed_key and str(passed_key).strip():
        return str(passed_key).strip()
    return os.getenv("ELEVENLABS_API_KEY", "").strip()

def verify_elevenlabs_key(api_key=None):
    """
    Validate ElevenLabs API Key and fetch user subscription info.
    """
    key = get_api_key(api_key)
    if not key:
        return {
            "valid": False,
            "error": "No ElevenLabs API key provided. Add key in settings or backend .env.",
            "tier": "none"
        }

    try:
        url = "https://api.elevenlabs.io/v1/user/subscription"
        headers = {"xi-api-key": key}
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            data = res.json()
            return {
                "valid": True,
                "tier": data.get("tier", "free"),
                "character_count": data.get("character_count", 0),
                "character_limit": data.get("character_limit", 10000),
                "can_extend_character_limit": data.get("can_extend_character_limit", False),
                "status": data.get("status", "active")
            }
        else:
            return {
                "valid": False,
                "status_code": res.status_code,
                "error": f"Invalid key or ElevenLabs error (HTTP {res.status_code})"
            }
    except Exception as exc:
        return {
            "valid": False,
            "error": f"Connection error to ElevenLabs API: {str(exc)}"
        }

def get_elevenlabs_voices(api_key=None):
    """
    Fetch voices from ElevenLabs API or return curated high-fidelity voices.
    """
    key = get_api_key(api_key)
    if key:
        try:
            url = "https://api.elevenlabs.io/v1/voices"
            headers = {"xi-api-key": key}
            res = requests.get(url, headers=headers, timeout=5)
            if res.status_code == 200:
                data = res.json()
                api_voices = data.get("voices", [])
                formatted = []
                for v in api_voices:
                    formatted.append({
                        "voice_id": v.get("voice_id"),
                        "name": v.get("name"),
                        "category": v.get("category", "premade"),
                        "description": v.get("description") or (v.get("labels", {}).get("description", "")),
                        "labels": v.get("labels", {}),
                        "preview_url": v.get("preview_url")
                    })
                if formatted:
                    return {
                        "source": "elevenlabs_api",
                        "voices": formatted,
                        "models": SUPPORTED_MODELS,
                        "count": len(formatted)
                    }
        except Exception:
            pass

    return {
        "source": "curated_catalog",
        "voices": CURATED_VOICES,
        "models": SUPPORTED_MODELS,
        "count": len(CURATED_VOICES)
    }

def text_to_speech_elevenlabs(
    text,
    voice_id=None,
    api_key=None,
    model_id=None,
    stability=0.5,
    similarity_boost=0.75,
    language="en"
):
    """
    Synthesize multilingual linguistic speech using ElevenLabs API.
    Falls back gracefully to multi-language Bhashini / gTTS if key is absent or request fails.
    """
    key = get_api_key(api_key)
    voice = voice_id or os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM").strip()
    model = model_id or os.getenv("ELEVENLABS_MODEL_ID", "eleven_multilingual_v2").strip()

    if key:
        try:
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice}?output_format=mp3_44100_128"
            headers = {
                "xi-api-key": key,
                "Content-Type": "application/json",
                "Accept": "audio/mpeg"
            }
            payload = {
                "text": text,
                "model_id": model,
                "voice_settings": {
                    "stability": float(stability),
                    "similarity_boost": float(similarity_boost),
                    "style": 0.0,
                    "use_speaker_boost": True
                }
            }

            resp = requests.post(url, json=payload, headers=headers, timeout=12)
            if resp.status_code == 200 and resp.content:
                audio_bytes = resp.content
                b64_audio = base64.b64encode(audio_bytes).decode("utf-8")
                return {
                    "success": True,
                    "provider": "elevenlabs",
                    "model_id": model,
                    "voice_id": voice,
                    "language": language,
                    "text": text,
                    "audio_format": "mp3",
                    "audio_base64": b64_audio,
                    "audio_data_url": f"data:audio/mp3;base64,{b64_audio}"
                }
            else:
                # Log or return error details with fallback
                error_msg = f"ElevenLabs API returned {resp.status_code}: {resp.text[:200]}"
        except Exception as exc:
            error_msg = f"ElevenLabs exception: {str(exc)}"
    else:
        error_msg = "No ElevenLabs API key specified"

    # Seamless linguistic fallback using Bhashini / local engine
    from integrations.bhashini_adapter import text_to_speech as bhashini_tts
    fallback_res = bhashini_tts(text, language)
    fallback_res["fallback_from"] = "elevenlabs"
    fallback_res["fallback_reason"] = error_msg
    return fallback_res
