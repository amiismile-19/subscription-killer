import os
import requests

def text_to_speech(text, language="hi"):
    """
    BHASHINI integrations can change by service/pipeline and API contract.
    Configure a compatible pipeline ID and credentials. This generic adapter
    deliberately refuses to guess a provider endpoint or request schema.
    """
    user_id = os.getenv("BHASHINI_USER_ID")
    api_key = os.getenv("BHASHINI_API_KEY")
    pipeline_id = os.getenv("BHASHINI_PIPELINE_ID")
    if not (user_id and api_key and pipeline_id):
        raise RuntimeError(
            "Set BHASHINI_USER_ID, BHASHINI_API_KEY, and BHASHINI_PIPELINE_ID "
            "and implement the request schema for your selected BHASHINI service."
        )
    raise NotImplementedError(
        "Add the current request/response schema for your selected BHASHINI TTS pipeline."
    )
