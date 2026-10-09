import os
import io
import tempfile
import base64
import time
from flask import Blueprint, jsonify, request, Response
from integrations.whisper_adapter import transcribe_audio, WHISPER_LANGUAGE_CODES
from integrations.bhashini_adapter import text_to_speech, get_audio_bytes, LANGUAGE_MAP
from integrations.elevenlabs_adapter import (
    text_to_speech_elevenlabs,
    get_elevenlabs_voices,
    verify_elevenlabs_key,
    get_api_key as get_el_key
)
from database import get_db
from services.scoring import get_user_score, award_points
from integrations.merchant_adapter import request_direct_cancellation
from config import Config

bp = Blueprint("voice", __name__)

LANGUAGE_PROMPTS = {
    "en": {
        "welcome": "Hello! I am your SubKiller AI financial voice assistant. How can I help with your subscriptions today?",
        "killed": "Direct cancellation confirmed for {merchant}. Your subscription has been stopped and credit score points have been allotted!",
        "deadlines": "You have upcoming cancellation deadlines. Would you like me to cancel them before renewal?",
        "score": "Your current subscription responsibility credit score is {score} ({tier}).",
        "general": "You have {count} active subscriptions with a total recurring spend of ₹{amount} per month.",
        "commands_guide": "Here are all the available voice commands you can say: First, 'Show total spend' to hear your annual recurring expenditure. Second, 'Cancel Netflix' or any service to immediately trigger zero-trust direct cancellation and earn 50 credit score points. Third, 'What is my credit score' to check your responsibility tier and score points. Fourth, 'Upcoming deadlines' to identify renewal dates 48 hours in advance. Fifth, 'Keep subscription' to verify and confirm an active subscription for 15 points. Sixth, 'Upgrade plan' to view discounted plans with score savings. Seventh, 'Open evidence' to view your verified audit pack."
    },
    "hi": {
        "welcome": "नमस्ते! मैं आपका सब-किलर एआई वित्तीय वॉयस सहायक हूँ। मैं आपकी कैसे मदद कर सकता हूँ?",
        "killed": "{merchant} का सीधा रद्दीकरण सफल हुआ। बिलिंग रोक दी गई है और आपके क्रेडिट स्कोर में अंक जोड़े गए हैं!",
        "deadlines": "आपके पास आगामी रद्दीकरण समयसीमाएं हैं। क्या आप रिन्यूअल से पहले इन्हें रद्द करना चाहते हैं?",
        "score": "आपका वर्तमान सब्सक्रिप्शन रिस्पॉन्सिबिलिटी क्रेडिट स्कोर {score} ({tier}) है।",
        "general": "आपके पास {count} सक्रिय सब्सक्रिप्शन हैं, जिनका कुल मासिक खर्च ₹{amount} है।",
        "commands_guide": "यहाँ वे सभी वॉयस कमांड हैं जिन्हें आप बोल सकते हैं: पहला, 'कुल खर्च दिखाएं' - अपना कुल वार्षिक खर्च सुनने के लिए। दूसरा, 'नेटफ्लिक्स रद्द करें' - सीधा रद्दीकरण करने और पचास क्रेडिट अंक पाने के लिए। तीसरा, 'मेरा स्कोर क्या है' - अपना क्रेडिट स्कोर और टियर जानने के लिए। चौथा, 'आगामी समयसीमाएं' - ऑटो-डेबिट से पहले रिन्यूअल तारीखें देखने के लिए। पांचवां, 'जारी रखें' - एक्टिव सब्सक्रिप्शन को पंद्रह अंकों के साथ कंफर्म करने के लिए। छठा, 'अपग्रेड प्लान' - डिस्काउंट ऑफर देखने के लिए। सातवां, 'सबूत खोलें' - अपना ऑडिट एविडेंस पैक देखने के लिए।"
    },
    "mr": {
        "welcome": "नमस्कार! मी तुमचा सब-किलर एआय आर्थिक व्हॉइस असिस्टंट आहे. मी तुम्हाला कशी मदत करू शकेन?",
        "killed": "{merchant} चे थेट रद्दीकरण यशस्वी झाले. बिलिंग थांबवले गेले आहे आणि तुमचे क्रेडिट गुण वाढवले गेले आहेत!",
        "deadlines": "तुमच्याकडे आगामी रद्दीकरण मुदत आहे. नूतनीकरणापूर्वी ते रद्द करायचे आहे का?",
        "score": "तुमचा सध्याचा सब्सक्रिप्शन जबाबदारी क्रेडिट स्कोअर {score} ({tier}) आहे.",
        "general": "तुमच्याकडे ₹{amount} मासिक खर्चासह {count} सक्रिय सदस्यत्वे आहेत.",
        "commands_guide": "तुम्ही बोलू शकता अशा सर्व व्हॉइस कमांड खालीलप्रमाणे आहेत: पहिले, 'एकूण खर्च दाखवा' - वार्षिक खर्च ऐकण्यासाठी. दुसरे, 'नेटफ्लिक्स रद्द करा' - थेट रद्दीकरण करून पन्नास क्रेडिट गुण मिळवण्यासाठी. तिसरे, 'माझा स्कोअर काय आहे' - तुमचा क्रेडिट स्कोअर तपासण्यासाठी. चौथे, 'आगामी मुदत' - नूतनीकरणाच्या तारखा तपासण्यासाठी. पाचवे, 'सुरू ठेवा' - पंधरा गुणांसह सबस्क्रिप्शन चालू ठेवण्यासाठी. सहावे, 'अपग्रेड प्लॅन' - नवीन ऑफर पाहण्यासाठी. सातवे, 'पुरावा उघडा' - संपूर्ण ऑडिट पॅक पाहण्यासाठी."
    },
    "ta": {
        "welcome": "வணக்கம்! நான் உங்கள் சப்-கில்லர் AI குரல் உதவியாளர். நான் உங்களுக்கு எவ்வாறு உதவ முடியும்?",
        "killed": "{merchant} நேரடி ரத்து செய்யப்பட்டது. கட்டணம் நிறுத்தப்பட்டது மற்றும் உங்கள் கிரெடிட் ஸ்கோர் புள்ளிகள் சேர்க்கப்பட்டன!",
        "deadlines": "உங்களுக்கு வரவிருக்கும் ரத்து காலக்கெடு உள்ளது. புதுப்பிப்பதற்கு முன் அதை ரத்து செய்ய விரும்புகிறீர்களா?",
        "score": "உங்கள் தற்போதைய சந்தா பொறுப்பு கிரெடிட் ஸ்கோர் {score} ({tier}) ஆகும்.",
        "general": "உங்களிடம் மாதந்தோறும் ₹{amount} செலவில் {count} செயலில் உள்ள சந்தாக்கள் உள்ளன.",
        "commands_guide": "நீங்கள் கூறக்கூடிய அனைத்து குரல் கட்டளைகளும் இதோ: முதலாவதாக, 'மொத்த செலவைக் காட்டு' - உங்கள் வருடாந்திர செலவை அறிய. இரண்டாவதாக, 'நெட்ஃபிக்ஸ் ரத்து செய்' - உடனடி ரத்து செய்து ஐம்பது கிரெடிட் புள்ளிகளைப் பெற. மூன்றாவதாக, 'என் கிரெடிட் ஸ்கோர் என்ன' - உங்கள் தரத்தை அறிய. நான்காவதாக, 'வரவிருக்கும் காலக்கெடு' - புதுப்பித்தல் தேதிகளை சரிபார்க்க. ஐந்தாவதாக, 'தொடர்க' - சந்தாவை உறுதிப்படுத்த. ஆறாவதாக, 'அப்கிரேட்' - புதிய திட்டங்களை பார்க்க. ஏழாவதாக, 'ஆதாரம் திற' - தணிக்கை அறிக்கையைக் காண."
    },
    "te": {
        "welcome": "నమస్కారం! నేను మీ సబ్-కిల్లర్ AI వాయిస్ అసిస్టెంట్‌ని. నేను మీకు ఎలా సహాయపడగలను?",
        "killed": "{merchant} నేరుగా రద్దు చేయబడింది. బిల్లింగ్ ఆపబడింది మరియు మీ క్రెడిట్ స్కోర్ పాయింట్లు జోడించబడ్డాయి!",
        "deadlines": "మీకు రాబోయే రద్దు గడువులు ఉన్నాయి. పునరుద్ధరణకు ముందే వాటిని రద్దు చేయాలా?",
        "score": "మీ ప్రస్తుత చందా బాధ్యత క్రెడిట్ స్కోరు {score} ({tier}).",
        "general": "మీకు నెలకు ₹{amount} ఖర్చుతో {count} సక్రియ చందాలు ఉన్నాయి.",
        "commands_guide": "మీరు ఉపయోగించగల అన్ని వాయిస్ ఆదేశాలు ఇక్కడ ఉన్నాయి: మొదటిది, 'మొత్తం ఖర్చు చూపించు' - మీ వార్షిక ఖర్చులను వినడానికి. రెండవది, 'నెట్‌ఫ్లిక్స్ రద్దు చేయి' - నేరుగా రద్దు చేసి యాభై క్రెడిట్ పాయింట్లు పొందడానికి. మూడవది, 'నా క్రెడిట్ స్కోరు ఎంత' - మీ స్థాయిని తెలుసుకోవడానికి. నాల్గవది, 'రాబోయే గడువులు' - పునరుద్ధరణ తేదీలను తనిఖీ చేయడానికి. ఐదవది, 'కొనసాగించు' - చందాను ఉంచడానికి. ఆరవది, 'అప్‌గ్రేడ్' - డిస్కౌంట్ ప్లాన్లు చూడటానికి. ఏడవది, 'ఆధారాలు తెరువు' - ఆడిట్ ప్యాక్ చూడటానికి."
    },
    "bn": {
        "welcome": "নমস্কার! আমি আপনার সাব-কিলার এআই ভয়েস সহকারী। আমি আপনাকে কীভাবে সাহায্য করতে পারি?",
        "killed": "{merchant} সরাসরি বাতিল করা হয়েছে। বিলিং বন্ধ করা হয়েছে এবং আপনার ক্রেডিট স্কোরে পয়েন্ট যুক্ত হয়েছে!",
        "deadlines": "আপনার আসন্ন বাতিলের সময়সীমা রয়েছে। নবায়নের আগে আপনি কি এটি বাতিল করতে চান?",
        "score": "আপনার বর্তমান সাবস্ক্রিপশন দায়িত্ব क्रेडिट स्कोर {score} ({tier})।",
        "general": "আপনার কাছে প্রতি মাসে ₹{amount} খরচে {count}টি সক্রিয় সাবস্ক্রিপশন রয়েছে।",
        "commands_guide": "এখানে আপনি যে সমস্ত ভয়েস কমান্ড ব্যবহার করতে পারেন: প্রথম, 'মোট খরচ দেখাও' - আপনার বার্ষিক খরচ জানতে। দ্বিতীয়, 'নেটফ্লিক্স বাতিল করো' - সরাসরি বাতিল করে পঞ্চাশ ক্রেডিট পয়েন্ট অর্জন করতে। তৃতীয়, 'আমার ক্রেডিট স্কোর কত' - আপনার স্কোর ও স্তর জানতে। চতুর্থ, 'আসন্ন সময়সীমা' - অটো-ডেবিট এড়াতে নবায়ন তারিখ জানতে। পঞ্চম, 'চালিয়ে রাখো' - সক্রিয় সাবস্ক্রিপশন রাখতে। ষষ্ঠ, 'আপগ্রেড' - ডিসকাউন্ট প্ল্যান দেখতে। সপ্তম, 'প্রমাণ খোলো' - অডিট প্যাক দেখতে।"
    },
    "gu": {
        "welcome": "નમસ્તે! હું તમારો સબ-કિલર AI નાણાકીય વૉઇસ સહાયક છું. હું તમને કેવી રીતે મદદ કરી શકું?",
        "killed": "{merchant} નું સીધું રદ્દીકરણ સફળ થયું. બિલિંગ બંધ કરવામાં આવ્યું છે અને તમારા ક્રેડિટ સ્કોરમાં પોઇન્ટ ઉમેરાયા છે!",
        "deadlines": "તમારી પાસે આગામી રદ્દીકરણ સમયમર્યાદા છે. શું તમે રિન્યુઅલ પહેલાં તેને રદ કરવા માંગો છો?",
        "score": "તમારો વર્તમાન સબ્સ્ક્રિપ્શન જવાબદારી ક્રેડિટ સ્કોર {score} ({tier}) છે.",
        "general": "તમારી પાસે દર મહિને ₹{amount} ના ખર્ચ સાથે {count} સક્રિય સબ્સ્ક્રિપ્શન્સ છે.",
        "commands_guide": "અહીં તમે બોલી શકો તેવા તમામ વૉઇસ કમાન્ડ્સ છે: પહેલું, 'કુલ ખર્ચ બતાવો' - તમારો વાર્ષિક ખર્ચ સાંભળવા માટે. બીજું, 'નેટફ્લિક્સ રદ કરો' - સીધું રદ્દીકરણ કરવા અને પચાસ ક્રેડિટ પોઇન્ટ્સ મેળવવા માટે. ત્રીજું, 'મારો ક્રેડિટ સ્કોર શું છે' - તમારો સ્કોર તપાસવા માટે. ચોથું, 'આગામી સમયમર્યાદા' - રિન્યુઅલ તારીખો જોવા માટે. પાંચમું, 'ચાલુ રાખો' - સબ્સ્ક્રિપ્શન જાળવી રાખવા માટે. છઠ્ઠું, 'અપગ્રેડ' - નવી યોજનાઓ જોવા માટે. સાતમું, 'પુરાવો ખોલો' - ઓડિટ પેક જોવા માટે."
    }
}

AVAILABLE_COMMANDS = [
    {
        "id": "spend",
        "command": "Show total spend",
        "native": {
            "en": "Show total spend",
            "hi": "कुल खर्च दिखाएं",
            "mr": "एकूण खर्च दाखवा",
            "ta": "மொத்த செலவைக் காட்டு",
            "te": "మొత్తం ఖర్చు చూపించు",
            "bn": "মোট খরচ দেখাও",
            "gu": "કુલ ખર્ચ બતાવો"
        },
        "description": "Reads out your total recurring spend and annual commitment across all subscriptions.",
        "action": "Reads recurring spend calculation aloud"
    },
    {
        "id": "cancel",
        "command": "Cancel [Merchant]",
        "native": {
            "en": "Cancel Netflix",
            "hi": "नेटफ्लिक्स रद्द करें",
            "mr": "नेटफ्लिक्स रद्द करा",
            "ta": "நெட்ஃபிக்ஸ் ரத்து செய்",
            "te": "నెట్‌ఫ్లిక్స్ రద్దు చేయి",
            "bn": "নেটফ্লিক্স বাতিল করো",
            "gu": "નેટફ્લિક્સ રદ કરો"
        },
        "description": "Executes immediate zero-trust direct cancellation, stops billing, and awards +50 credit score points.",
        "action": "Direct cancellation with timestamped confirmation"
    },
    {
        "id": "score",
        "command": "What is my credit score?",
        "native": {
            "en": "What is my credit score?",
            "hi": "मेरा क्रेडिट स्कोर क्या है?",
            "mr": "माझा क्रेडिट स्कोअर काय आहे?",
            "ta": "என் கிரெடிட் ஸ்கோர் என்ன?",
            "te": "నా క్రెడిట్ స్కోరు ఎంత?",
            "bn": "আমার ক্রেডিট স্কোর কত?",
            "gu": "મારો ક્રેડિટ સ્કોર શું છે?"
        },
        "description": "Speaks your current financial responsibility score and level tier (Seed, Sprout, Saver, Guardian, Champion).",
        "action": "Reads credit score tier & points balance"
    },
    {
        "id": "deadlines",
        "command": "Upcoming deadlines",
        "native": {
            "en": "Upcoming cancellation deadlines",
            "hi": "आगामी रद्दीकरण समयसीमाएं",
            "mr": "आगामी रद्दीकरण मुदत",
            "ta": "வரவிருக்கும் ரத்து காலக்கெடு",
            "te": "రాబోయే రద్దు గడువులు",
            "bn": "আসন্ন বাতিলের সময়সীমা",
            "gu": "આગામી રદ્દીકરણ સમયમર્યાદા"
        },
        "description": "Identifies subscriptions renewing within 48 hours to execute safe cancellation before autopay triggers.",
        "action": "Checks renewal deadlines & alerts"
    },
    {
        "id": "keep",
        "command": "Keep [Merchant]",
        "native": {
            "en": "Keep subscription",
            "hi": "सब्सक्रिप्शन जारी रखें",
            "mr": "सबस्क्रिप्शन सुरू ठेवा",
            "ta": "சந்தாவைத் தொடர்க",
            "te": "చందాను కొనసాగించు",
            "bn": "সাবস্ক্রিপশন চালিয়ে রাখো",
            "gu": "સબ્સ્ક્રિપ્શન ચાલુ રાખો"
        },
        "description": "Confirms an intentional active subscription and records +15 credit score points.",
        "action": "Confirms active status"
    },
    {
        "id": "upgrade",
        "command": "Upgrade plan",
        "native": {
            "en": "Upgrade plan",
            "hi": "अपग्रेड प्लान",
            "mr": "अपग्रेड प्लॅन",
            "ta": "அப்கிரேட் திட்டம்",
            "te": "అప్‌గ్రేడ్ ప్లాన్",
            "bn": "আপগ্রেড প্ল্যান",
            "gu": "અપગ્રેડ પ્લાન"
        },
        "description": "Displays upgrade options with loyalty score discounts (1 point = 1% off, up to 25% discount).",
        "action": "Opens plan upgrade modal"
    },
    {
        "id": "evidence",
        "command": "Open evidence pack",
        "native": {
            "en": "Open evidence pack",
            "hi": "सबूत पैक खोलें",
            "mr": "पुरावा पॅक उघडा",
            "ta": "ஆதாரத் தொகுப்பைத் திற",
            "te": "ఆధారాల ప్యాక్ తెరువు",
            "bn": "প্রমাণ প্যাক খোলো",
            "gu": "પુરાવો પેક ખોલો"
        },
        "description": "Opens verified client-side evidence audit pack with dispute proofs and export options.",
        "action": "Opens verified evidence pack"
    }
]

@bp.get("/languages")
def supported_languages():
    """Return all 7 supported Indian languages for voice I/O"""
    languages = [
        {"code": "en", "name": "English", "native": "English", "default": False},
        {"code": "hi", "name": "Hindi", "native": "हिन्दी", "default": True},
        {"code": "mr", "name": "Marathi", "native": "मराठी", "default": False},
        {"code": "ta", "name": "Tamil", "native": "தமிழ்", "default": False},
        {"code": "te", "name": "Telugu", "native": "తెలుగు", "default": False},
        {"code": "bn", "name": "Bengali", "native": "বাংলা", "default": False},
        {"code": "gu", "name": "Gujarati", "native": "ગુજરાતી", "default": False},
    ]
    return jsonify(supported_languages=languages)

@bp.get("/commands")
def get_commands():
    """
    Return all available voice commands with localized translations and descriptions.
    """
    lang = request.args.get("language", "en").lower()
    if lang not in LANGUAGE_PROMPTS:
        lang = "en"
    guide_text = LANGUAGE_PROMPTS[lang].get("commands_guide", LANGUAGE_PROMPTS["en"]["commands_guide"])
    return jsonify(
        language=lang,
        commands=AVAILABLE_COMMANDS,
        commands_guide_text=guide_text
    )

@bp.post("/read-all-commands")
def read_all_commands():
    """
    Synthesize speech for all voice commands using ElevenLabs linguistic engine.
    Returns audio data URL and text for immediate audio readout.
    """
    data = request.get_json(silent=True) or {}
    language = str(data.get("language", "en")).lower()
    voice_id = data.get("voice_id")
    api_key = data.get("api_key") or data.get("elevenlabs_api_key") or request.headers.get("xi-api-key")
    model_id = data.get("model_id")

    if language not in LANGUAGE_PROMPTS:
        language = "en"

    guide_text = LANGUAGE_PROMPTS[language].get("commands_guide", LANGUAGE_PROMPTS["en"]["commands_guide"])

    speech_res = text_to_speech_elevenlabs(
        text=guide_text,
        voice_id=voice_id,
        api_key=api_key,
        model_id=model_id,
        language=language
    )

    return jsonify(
        language=language,
        guide_text=guide_text,
        audio_data_url=speech_res["audio_data_url"],
        audio_format=speech_res["audio_format"],
        audio_provider=speech_res["provider"],
        voice_id=speech_res.get("voice_id"),
        commands=AVAILABLE_COMMANDS
    )

@bp.get("/elevenlabs/voices")
def elevenlabs_voices():
    """
    Return curated and available linguistic voices from ElevenLabs repository.
    Allows passing api_key query param or using configured environment key.
    """
    api_key = request.args.get("api_key") or request.headers.get("xi-api-key")
    result = get_elevenlabs_voices(api_key=api_key)
    return jsonify(result)

@bp.post("/elevenlabs/verify-key")
def elevenlabs_verify_key():
    """
    Validate user's ElevenLabs API key and return subscription character balance & tier.
    """
    data = request.get_json(silent=True) or {}
    api_key = data.get("api_key") or request.headers.get("xi-api-key")
    result = verify_elevenlabs_key(api_key=api_key)
    return jsonify(result)

@bp.post("/elevenlabs/speak")
def elevenlabs_speak():
    """
    Explicit ElevenLabs Linguistic Text-to-Speech synthesis with multilingual models.
    Supports English, Hindi, Bengali, Marathi, Tamil, Telugu, Gujarati, and 20+ other languages.
    """
    data = request.get_json(silent=True) or {}
    text = str(data.get("text", "")).strip()
    language = str(data.get("language", "en")).lower()
    voice_id = data.get("voice_id")
    api_key = data.get("api_key") or request.headers.get("xi-api-key")
    model_id = data.get("model_id")

    if not text:
        return jsonify(error="text is required"), 400

    result = text_to_speech_elevenlabs(
        text=text,
        voice_id=voice_id,
        api_key=api_key,
        model_id=model_id,
        language=language
    )
    return jsonify(result)

@bp.post("/transcribe")
def transcribe():
    """
    Audio Input (Speech-to-Text) using Whisper repository with SpeechRecognition fallback.
    Supports English, Hindi, Marathi, Tamil, Telugu, Bengali, Gujarati.
    """
    language = request.form.get("language") or request.args.get("language", "auto")
    uploaded = request.files.get("audio")
    path = None

    try:
        if uploaded and uploaded.filename:
            suffix = os.path.splitext(uploaded.filename)[1][:10] or ".wav"
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp:
                path = temp.name
                uploaded.save(path)
        else:
            json_data = request.get_json(silent=True) or {}
            audio_b64 = json_data.get("audio_base64")
            language = json_data.get("language", language)
            if audio_b64:
                raw_bytes = base64.b64decode(audio_b64)
                with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp:
                    path = temp.name
                    temp.write(raw_bytes)
            else:
                return jsonify(error="Provide multipart file 'audio' or JSON 'audio_base64'"), 400

        result = transcribe_audio(path, language)
        return jsonify(result)
    except Exception as exc:
        return jsonify(error=str(exc)), 500
    finally:
        if path and os.path.exists(path):
            try:
                os.remove(path)
            except Exception:
                pass

@bp.post("/speak")
def speak():
    """
    Audio Output (Text-to-Speech) supporting ElevenLabs linguistic voice
    with automated fallback to Bhashini and multi-language engine.
    """
    data = request.get_json(silent=True) or {}
    text = str(data.get("text", "")).strip()
    language = str(data.get("language", "hi")).lower()
    provider = str(data.get("provider", "")).lower()
    api_key = data.get("api_key") or data.get("elevenlabs_api_key") or request.headers.get("xi-api-key")
    voice_id = data.get("voice_id")

    if not text:
        return jsonify(error="text is required"), 400

    try:
        if provider == "elevenlabs" or api_key or Config.ELEVENLABS_API_KEY:
            result = text_to_speech_elevenlabs(
                text=text,
                voice_id=voice_id,
                api_key=api_key,
                language=language
            )
            return jsonify(result)

        result = text_to_speech(text, language)
        return jsonify(result)
    except Exception as exc:
        return jsonify(error=str(exc)), 500

@bp.get("/audio-stream")
def audio_stream():
    """
    Direct playable audio streaming endpoint for HTML5 <audio src="..."> tags.
    """
    text = request.args.get("text", "").strip()
    language = request.args.get("language", "hi").lower()
    provider = request.args.get("provider", "").lower()
    api_key = request.args.get("api_key") or request.headers.get("xi-api-key")
    voice_id = request.args.get("voice_id")

    if not text:
        text = "SubKiller audio assistant ready"

    try:
        if provider == "elevenlabs" or api_key or Config.ELEVENLABS_API_KEY:
            res = text_to_speech_elevenlabs(text=text, voice_id=voice_id, api_key=api_key, language=language)
            audio_bytes = base64.b64decode(res["audio_base64"])
            return Response(audio_bytes, mimetype="audio/mpeg", headers={"Content-Disposition": "inline"})

        audio_bytes, audio_fmt = get_audio_bytes(text, language)
        mimetype = "audio/mpeg" if audio_fmt == "mp3" else "audio/wav"
        return Response(audio_bytes, mimetype=mimetype, headers={"Content-Disposition": "inline"})
    except Exception as exc:
        return jsonify(error=str(exc)), 500

@bp.post("/assistant-chat")
def assistant_chat():
    """
    Complete interactive voice copilot endpoint:
    Processes user query (text or transcription), assesses subscriptions in DB,
    generates contextual reply in selected language, and generates playable
    ElevenLabs linguistic speech audio!
    """
    data = request.get_json(silent=True) or {}
    query_text = str(data.get("query", "")).strip()
    language = str(data.get("language", "hi")).lower()
    user_id = int(data.get("user_id", 1))
    elevenlabs_key = data.get("elevenlabs_api_key") or data.get("api_key") or request.headers.get("xi-api-key")
    voice_id = data.get("voice_id")
    provider = str(data.get("provider", "")).lower()

    if language not in LANGUAGE_PROMPTS:
        language = "hi"

    lang_prompts = LANGUAGE_PROMPTS[language]
    db = get_db()
    active_subs = db.execute(
        "SELECT * FROM subscriptions WHERE user_id=? AND status='active'",
        (user_id,)
    ).fetchall()
    active_list = [dict(s) for s in active_subs]
    total_monthly = sum(float(s["amount"]) if s["billing_frequency"] == "monthly" else float(s["amount"])/12 for s in active_list)

    user_score_data = get_user_score(user_id)
    query_lower = query_text.lower()

    # Determine intent & formulate response
    executed_action = None
    if any(k in query_lower for k in [
        "command", "commands", "help", "list", "read all", "tell me what you can do",
        "कमांड", "आदेश", "मदद", "सहायता", "कमांड्स", "आज्ञा", "कमांड बताओ",
        "કમાન્ડ", "આદેશ", "સહાય", "કમાન્ડ્સ",
        "கட்டளை", "ஆணை", "உதவி", "கட்டளைகள்",
        "ఆదేశాలు", "సహాయం", "కమాండ్లు",
        "কমান্ড", "সাহায্য", "আদেশ"
    ]):
        reply_text = lang_prompts.get("commands_guide", LANGUAGE_PROMPTS["en"]["commands_guide"])
        executed_action = {
            "action": "read_all_commands",
            "commands_count": len(AVAILABLE_COMMANDS)
        }
    elif any(k in query_lower for k in ["score", "स्कोर", "गुण", "மதிப்பெண்", "స్కోరు", "સ્કોર"]):
        reply_text = lang_prompts["score"].format(
            score=user_score_data["credit_score"],
            tier=user_score_data["tier"]
        )
        executed_action = {"action": "check_score", "score": user_score_data["credit_score"]}
    elif any(k in query_lower for k in ["deadline", "तारीख", "मुदत", "தேதி", "గడువు", "সময়সীমা", "તારીખ"]):
        if active_list:
            top_sub = sorted(active_list, key=lambda s: s.get("cancellation_deadline") or "9999")[0]
            dl = top_sub.get("cancellation_deadline") or top_sub.get("renewal_date") or "Soon"
            reply_text = f"{top_sub['merchant']} (Txn ID: {top_sub['transaction_ref']}) deadline: {dl}. " + lang_prompts["deadlines"]
        else:
            reply_text = "No active deadlines. All clean!"
        executed_action = {"action": "check_deadlines"}
    elif any(k in query_lower for k in ["cancel", "रद्द", "बंद", "थांबवा", "ரத்து", "రద్దు", "বাতিল", "રદ"]):
        matched_sub = None
        for s in active_list:
            if s["merchant"].lower() in query_lower:
                matched_sub = s
                break
        if matched_sub:
            sub_id = matched_sub["subscription_id"]
            db.execute("UPDATE subscriptions SET status='cancelled' WHERE subscription_id=?", (sub_id,))
            db.execute(
                """INSERT INTO cancellation_requests(subscription_id, transaction_ref, status, confirmation_ref, message)
                   VALUES (?, ?, 'cancelled', ?, 'Direct voice cancellation')""",
                (sub_id, matched_sub["transaction_ref"], f"KILL-VOICE-{matched_sub['transaction_ref']}")
            )
            db.commit()
            award_points(user_id, sub_id, "subscription_cancelled", f"voice-cancel-{matched_sub['transaction_ref']}-{int(time.time())}",
                         f"Voice direct cancellation of {matched_sub['merchant']}", matched_sub['transaction_ref'])
            reply_text = lang_prompts["killed"].format(merchant=matched_sub["merchant"])
            executed_action = {
                "action": "direct_cancellation",
                "subscription_id": sub_id,
                "merchant": matched_sub["merchant"],
                "confirmation_code": f"KILL-VOICE-{matched_sub['transaction_ref']}"
            }
        else:
            reply_text = lang_prompts["deadlines"]
    elif not query_text:
        reply_text = lang_prompts["welcome"]
    else:
        reply_text = lang_prompts["general"].format(
            count=len(active_list),
            amount=int(total_monthly)
        )

    # Generate speech audio via ElevenLabs linguistic synthesis or fallback
    has_el_key = bool(elevenlabs_key or Config.ELEVENLABS_API_KEY)
    if provider == "elevenlabs" or has_el_key:
        speech_output = text_to_speech_elevenlabs(
            text=reply_text,
            voice_id=voice_id,
            api_key=elevenlabs_key,
            language=language
        )
    else:
        speech_output = text_to_speech(reply_text, language)

    # Refresh score in case an action was executed
    refreshed_score = get_user_score(user_id)

    return jsonify(
        language=language,
        language_name=LANGUAGE_MAP.get(language, {}).get("name", language.upper()),
        query=query_text,
        reply_text=reply_text,
        audio_data_url=speech_output["audio_data_url"],
        audio_format=speech_output["audio_format"],
        audio_provider=speech_output["provider"],
        voice_id=speech_output.get("voice_id"),
        executed_action=executed_action,
        credit_score=refreshed_score["credit_score"],
        tier=refreshed_score["tier"]
    )
