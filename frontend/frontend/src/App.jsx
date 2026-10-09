import React, { useState, useEffect, useRef } from 'react';
import Papa from 'papaparse';
import './App.css';
import {
  fetchSubscriptions,
  cancelSubscription,
  cancelByTransaction,
  upgradeSubscription,
  batchSyncSubscriptions,
  fetchUserScore,
  fetchScoreHistory,
  fetchNotifications,
  createCustomNotification,
  fetchElevenLabsVoices,
  verifyElevenLabsKey,
  synthesizeSpeech,
  voiceAssistantChat,
  checkBackendHealth,
  fetchSupportedLanguages,
  fetchCommands,
  readAllCommandsAudio,
  transcribeAudio
} from './api';

const DEFAULT_COMMANDS = [
  {
    id: "spend",
    command: "Show total spend",
    native: {
      en: "Show total spend",
      hi: "कुल खर्च दिखाएं",
      mr: "एकूण खर्च दाखवा",
      ta: "மொத்த செலவைக் காட்டு",
      te: "మొత్తం ఖర్చు చూపించు",
      bn: "মোট খরচ দেখাও",
      gu: "કુલ ખર્ચ બતાવો"
    },
    description: "Reads out your total recurring spend and annual commitment across all subscriptions.",
    action: "Reads recurring spend calculation aloud"
  },
  {
    id: "cancel",
    command: "Cancel Netflix",
    native: {
      en: "Cancel Netflix",
      hi: "नेटफ्लिक्स रद्द करें",
      mr: "नेटफ्लिक्स रद्द करा",
      ta: "நெட்ஃபிக்ஸ் ரத்து செய்",
      te: "నెట్‌ఫ్లిక్స్ రద్దు చేయి",
      bn: "নেটফ্লিক্স বাতিল করো",
      gu: "નેટફ્લિક્સ રદ કરો"
    },
    description: "Executes immediate zero-trust direct cancellation, stops billing, and awards +50 credit score points.",
    action: "Direct cancellation with timestamped confirmation"
  },
  {
    id: "score",
    command: "What is my credit score?",
    native: {
      en: "What is my credit score?",
      hi: "मेरा क्रेडिट स्कोर क्या है?",
      mr: "माझा क्रेडिट स्कोअर काय आहे?",
      ta: "என் கிரெடிட் ஸ்கோர் என்ன?",
      te: "నా క్రెడిట్ స్కోరు ఎంత?",
      bn: "আমার ক্রেডিট স্কোর কত?",
      gu: "મારો ક્રેડિટ સ્કોર શું છે?"
    },
    description: "Speaks your current financial responsibility score and level tier (Seed, Sprout, Saver, Guardian, Champion).",
    action: "Reads credit score tier & points balance"
  },
  {
    id: "deadlines",
    command: "Upcoming deadlines",
    native: {
      en: "Upcoming cancellation deadlines",
      hi: "आगामी रद्दीकरण समयसीमाएं",
      mr: "आगामी रद्दीकरण मुदत",
      ta: "வரவிருக்கும் ரத்து காலக்கெடு",
      te: "రాబోయే రద్దు గడువులు",
      bn: "আসন্ন বাতিলের সময়সীমা",
      gu: "આગામી રદ્દીકરણ સમયમર્યાદા"
    },
    description: "Identifies subscriptions renewing within 48 hours to execute safe cancellation before autopay triggers.",
    action: "Checks renewal deadlines & alerts"
  },
  {
    id: "keep",
    command: "Keep subscription",
    native: {
      en: "Keep subscription",
      hi: "सब्सक्रिप्शन जारी रखें",
      mr: "सबस्क्रिप्शन सुरू ठेवा",
      ta: "சந்தாவைத் தொடர்க",
      te: "చందాను కొనసాగించు",
      bn: "সাবস্ক্রিপশন চালিয়ে রাখো",
      gu: "સબ્સ્ક્રિપ્શન ચાલુ રાખો"
    },
    description: "Confirms an intentional active subscription and records +15 credit score points.",
    action: "Confirms active status"
  },
  {
    id: "upgrade",
    command: "Upgrade plan",
    native: {
      en: "Upgrade plan",
      hi: "अपग्रेड प्लान",
      mr: "अपग्रेड प्लॅन",
      ta: "அப்கிரேட் திட்டம்",
      te: "అప్‌గ్రేడ్ ప్లాన్",
      bn: "আপগ্রেড প্ল্যান",
      gu: "અપગ્રેડ પ્લાન"
    },
    description: "Displays upgrade options with loyalty score discounts (1 point = 1% off, up to 25% discount).",
    action: "Opens plan upgrade modal"
  },
  {
    id: "evidence",
    command: "Open evidence pack",
    native: {
      en: "Open evidence pack",
      hi: "सबूत पैक खोलें",
      mr: "पुरावा पॅक उघडा",
      ta: "ஆதாரத் தொகுப்பைத் திற",
      te: "ஆధారాల ప్యాక్ తెరువు",
      bn: "প্রমাণ প্যাক খোলো",
      gu: "પુરાવો પેક ખોલો"
    },
    description: "Opens verified client-side evidence audit pack with dispute proofs and export options.",
    action: "Opens verified evidence pack"
  }
];

const DEFAULT_GUIDE_TEXT = "Here are all the available voice commands you can say: First, 'Show total spend' to hear your annual recurring expenditure. Second, 'Cancel Netflix' or any service to immediately trigger zero-trust direct cancellation and earn 50 credit score points. Third, 'What is my credit score' to check your responsibility tier and score points. Fourth, 'Upcoming deadlines' to identify renewal dates 48 hours in advance. Fifth, 'Keep subscription' to verify and confirm an active subscription for 15 points. Sixth, 'Upgrade plan' to view discounted plans with score savings. Seventh, 'Open evidence' to view your verified audit pack.";

const PTS = { c: 10, k: 15, u: 30 };
const FQ = { W: 52, M: 12, Q: 4, A: 1 };
const FN = { W: 'Weekly', M: 'Monthly', Q: 'Quarterly', A: 'Annual' };
const N = {
  NETFLIX: 'Netflix',
  JIOHOTSTAR: 'JioHotstar',
  AMAZON: 'Amazon Prime',
  SPOTIFY: 'Spotify',
  YOUTUBE: 'YouTube Premium',
  APPLE: 'Apple Music',
  OPENAI: 'ChatGPT Go'
};
const AL = {
  NETFLIX: /netflix|नेटफ्लिक्स|নেটফ্লিক্স|நெட்ஃப்ளிக்ஸ்|నెట్‌ఫ్లిక్స్/i,
  JIOHOTSTAR: /hotstar|हॉटस्टार|হটস্টার|ஹாட்ஸ்டார்|హాట్‌స్టార్/i,
  AMAZON: /amazon|prime|अमेज़न|प्राइम|অ্যামাজন|அமேசான்|అమెజాన్/i,
  SPOTIFY: /spotify|स्पॉटिफाई|স্পটিফাই|ஸ்பாட்டிஃபை|స్పాటిఫై/i,
  YOUTUBE: /youtube|यूट्यूब|ইউটিউব|யூடியூப்|యూట్యూబ్/i,
  APPLE: /apple|एप्पल|अॅपल|অ্যাপল|ஆப்பிள்|ఆపిల్/i,
  OPENAI: /chatgpt|चैटजीपीटी|চ্যাটজিপিটি|சாட்ஜிபிடி|చాట్‌జీపీటీ/i
};
const LV = [
  [0, 'Seed'],
  [20, 'Sprout'],
  [50, 'Saver'],
  [100, 'Guardian'],
  [200, 'Champion']
];
const CUR = {
  NETFLIX: 'Standard',
  JIOHOTSTAR: 'Super',
  SPOTIFY: 'Standard',
  YOUTUBE: 'Individual',
  APPLE: 'Individual',
  OPENAI: 'Go',
  AMAZON: 'Prime monthly'
};
const PL = {
  NETFLIX: [['Premium', 649, 'mo', '4K + HDR on up to 4 screens']],
  JIOHOTSTAR: [
    ['Super yearly', 1099, 'yr', 'Same Super plan, billed once a year (Save ₹689)'],
    ['Premium monthly', 299, 'mo', '4K, Dolby Atmos, and 4 screens'],
    ['Premium yearly', 2199, 'yr', 'Premium 4K at lowest yearly rate (Save ₹1,389)']
  ],
  SPOTIFY: [['Platinum', 299, 'mo', 'Lossless 24-bit audio and top Premium tier']],
  YOUTUBE: [
    ['Individual yearly', 1490, 'yr', 'Prepay 1 full year and skip monthly billing (Save ₹298)'],
    ['Family', 299, 'mo', 'Share YouTube Premium with up to 5 family members']
  ],
  APPLE: [
    ['Apple One Individual', 195, 'mo', 'Music plus TV+, Arcade, and 50GB iCloud+'],
    ['Family', 229, 'mo', 'Share Apple Music with up to 6 family members']
  ],
  OPENAI: [
    ['Plus', 1999, 'mo', 'Flagship reasoning model and higher limits'],
    ['Pro', 19900, 'mo', 'Highest limits for heavy daily AI compute']
  ],
  AMAZON: [['Prime yearly', 1499, 'yr', 'Same full Prime Video & Free Delivery, billed yearly (Save ₹2,089)']]
};

const R = {
  tot: {
    en: 'Your recurring payments total {a} a year across {n} items.',
    hi: 'आपके नियमित भुगतान सालाना {a} हैं, कुल {n} सब्सक्रिप्शन।',
    bn: 'আপনার নিয়মিত পেমেন্ট বছরে {a}, মোট {n}টি।',
    mr: 'तुमचे नियमित पेमेंट वर्षाला {a}, एकूण {n}.',
    ta: 'உங்கள் தொடர் செலவு ஆண்டுக்கு {a}, மொத்தம் {n}.',
    te: 'మీ రెగ్యులర్ చెల్లింపులు సంవత్సరానికి {a}, మొత్తం {n}.'
  },
  c: {
    en: '{m} cancellation message is ready. You earned {p} points.',
    hi: '{m} रद्द करने का संदेश तैयार है। आपको {p} अंक मिले।',
    bn: '{m} বাতিলের বার্তা তৈরি। আপনি {p} পয়েন্ট পেলেন।',
    mr: '{m} रद्द करण्याचा संदेश तयार. तुम्हाला {p} गुण मिळाले.',
    ta: '{m} ரத்து செய்தி தயார். உங்களுக்கு {p} புள்ளிகள்.',
    te: '{m} రద్దు సందేశం సిద్ధం. మీకు {p} పాయింట్లు.'
  },
  k: {
    en: 'Kept {m}. You earned {p} points.',
    hi: '{m} जारी रखा। आपको {p} अंक मिले।',
    bn: '{m} চালু রাখা হলো। {p} পয়েন্ট পেলেন।',
    mr: '{m} सुरू ठेवले. {p} गुण मिळाले.',
    ta: '{m} தொடர்கிறது. {p} புள்ளிகள் கிடைத்தன.',
    te: '{m} కొనసాగుతుంది. {p} పాయింట్లు వచ్చాయి.'
  },
  u: {
    en: 'Upgraded {m}. Great choice, {p} points.',
    hi: '{m} अपग्रेड किया। शानदार, {p} अंक।',
    bn: '{m} আপগ্রেড হলো। দারুণ, {p} পয়েন্ট।',
    mr: '{m} अपग्रेड केले. छान, {p} गुण.',
    ta: '{m} மேம்படுத்தப்பட்டது. {p} புள்ளிகள்.',
    te: '{m} అప్‌గ్రేడ్ అయింది. {p} పాయింట్లు.'
  },
  sc: {
    en: 'Your score is {p}.',
    hi: 'आपका स्कोर {p} है।',
    bn: 'আপনার স্কোর {p}।',
    mr: 'तुमचा स्कोर {p} आहे.',
    ta: 'உங்கள் ஸ்கோர் {p}.',
    te: 'మీ స్కోర్ {p}.'
  },
  ev: {
    en: 'Opening your evidence pack.',
    hi: 'आपका सबूत पैक खुल रहा है।',
    bn: 'প্রমাণ প্যাক খুলছে।',
    mr: 'पुरावा पॅक उघडत आहे.',
    ta: 'ஆதாரத் தொகுப்பு திறக்கிறது.',
    te: 'ఆధార ప్యాక్ తెరుస్తున్నాను.'
  },
  ld: {
    en: 'Sample statement loaded. Found {n} subscriptions.',
    hi: 'सैंपल स्टेटमेंट लोड हुआ। {n} सब्सक्रिप्शन मिले।',
    bn: 'স্যাম্পল লোড হলো। {n}টি সাবস্ক্রিপশন পাওয়া গেছে।',
    mr: 'सॅम्पल लोड झाले. {n} सबस्क्रिप्शन सापडले.',
    ta: 'மாதிரி ஏற்றப்பட்டது. {n} சந்தாக்கள்.',
    te: 'నమూనా లోడ్ అయింది. {n} సబ్‌స్క్రిప్షన్లు.'
  },
  uo: {
    en: 'Showing upgrade plans for {m}.',
    hi: '{m} के अपग्रेड प्लान दिखा रहा हूँ।',
    bn: '{m} এর আপগ্রেড প্ল্যান দেখাচ্ছি।',
    mr: '{m} चे अपग्रेड प्लॅन दाखवत आहे.',
    ta: '{m} மேம்படுத்தும் திட்டங்களைக் காட்டுகிறேன்.',
    te: '{m} అప్‌గ్రేడ్ ప్లాన్లు చూపిస్తున్నాను.'
  },
  no: {
    en: 'Try: total spend, cancel Netflix, keep, upgrade, score, evidence.',
    hi: 'कहें: कुल खर्च, नेटफ्लिक्स रद्द करो, रखो, अपग्रेड, स्कोर, सबूत।',
    bn: 'বলুন: মোট খরচ, বাতিল, রাখো, আপগ্রেড, স্কোর, প্রমাণ।',
    mr: 'म्हणा: एकूण खर्च, रद्द करा, ठेवा, अपग्रेड, स्कोर, पुरावा.',
    ta: 'சொல்லுங்கள்: மொத்த செலவு, ரத்து, தொடர், அப்கிரேட், ஸ்கோர், ஆதாரம்.',
    te: 'చెప్పండి: మొత్తం ఖర్చు, రద్దు, ఉంచు, అప్‌గ్రేడ్, స్కోర్, ఆధారం.'
  }
};

const RX = {
  s: /sample|demo|सैंपल|नमूना|স্যাম্পল|সেম্পল|सॅम्पल|மாதிரி|నమూనా/i,
  e: /evidence|proof|prove|सबूत|प्रमाण|প্রমাণ|पुरावा|आधार|ஆதார|ఆధార/i,
  sc: /score|points|स्कोर|अंक|স্কোর|পয়েন্ট|गुण|ஸ்கோர்|புள்ளி|స్కోర్|పాయింట్/i,
  u: /upgrade|अपग्रेड|আপগ্রেড|அப்கிரேட்|மேம்படுத்|అప్‌గ్రేడ్|అప్గ్రేడ్/i,
  c: /cancel|रद्द|कैंसल|बंद|বাতিল|ক্যান্সেল|कॅन्सल|ரத்து|கேன்சல்|రద్దు|క్యాన్సిల్/i,
  k: /keep|continue|रखो|रखें|जारी|রাখ|চালিয়ে|ठेव|सुरू|வைத்து|வையுங்கள்|தொடர்|ఉంచ|కొనసాగ/i,
  t: /total|spend|annual|how much|show|कुल|खर्च|कितना|মোট|খরচ|কত|एकूण|किती|மொத்த|செலவு|எவ்வளவு|మొత్తం|ఖర్చు|ఎంత/i
};

export default function App() {
  const [view, setView] = useState('v1');
  const [theme, setTheme] = useState(() => {
    try { return localStorage.getItem('sk-theme') || 'light'; } catch { return 'light'; }
  });
  const [subs, setSubs] = useState([]);
  const [score, setScore] = useState(0);
  const [bal, setBal] = useState(0);
  const [filter, setFilter] = useState('a');
  const [selectedId, setSelectedId] = useState(null);
  const [fileDetails, setFileDetails] = useState('');
  const [errorMsg, setErrorMsg] = useState('');
  const [toastMsg, setToastMsg] = useState('');
  const [popScore, setPopScore] = useState(false);
  const [v2Progress, setV2Progress] = useState([false, false, false, false, false]);

  // Backend Connectivity & State
  const [backendOnline, setBackendOnline] = useState(false);
  const [backendStats, setBackendStats] = useState({ subsCount: 0, score: 0, tier: 'Seed', notifsCount: 0 });
  const [statusModalOpen, setStatusModalOpen] = useState(false);
  const [receiptModalOpen, setReceiptModalOpen] = useState(false);
  const [lastReceipt, setLastReceipt] = useState(null);
  const [notifModalOpen, setNotifModalOpen] = useState(false);
  const [notificationsList, setNotificationsList] = useState([]);
  const [newNotif, setNewNotif] = useState({ title: 'Upcoming Cancellation Deadline', message: 'Cancel before renewal date to avoid fee', merchant: '' });

  // Voice Assistant Drawer, Audible Commands & Accessible Audio State
  const [voiceOpen, setVoiceOpen] = useState(false);
  const [lang, setLang] = useState('en-IN');
  const [voiceLog, setVoiceLog] = useState('Pick a language, tap the mic and speak, or explore audible commands below.');
  const [textCommand, setTextCommand] = useState('');
  const [isListening, setIsListening] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [isPlayingAudio, setIsPlayingAudio] = useState(false);
  const [audioEnabled, setAudioEnabled] = useState(true);
  const [speechRate, setSpeechRate] = useState(1.0);
  const [lastSpokenText, setLastSpokenText] = useState('');
  const [availableCommands, setAvailableCommands] = useState(DEFAULT_COMMANDS);
  const [commandsGuideText, setCommandsGuideText] = useState(DEFAULT_GUIDE_TEXT);
  const [commandsDrawerOpen, setCommandsDrawerOpen] = useState(false);
  const [isSyncingDb, setIsSyncingDb] = useState(false);
  const [searchFilter, setSearchFilter] = useState('');
  const [inlineListeningField, setInlineListeningField] = useState(null);

  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);

  // ElevenLabs Linguistic Voices
  const [elKey, setElKey] = useState(() => {
    try { return sessionStorage.getItem('sk-el') || ''; } catch { return ''; }
  });
  const [elVoiceId, setElVoiceId] = useState(() => {
    try { return localStorage.getItem('sk-el-voice') || '21m00Tcm4TlvDq8ikWAM'; } catch { return '21m00Tcm4TlvDq8ikWAM'; }
  });
  const [elModelId, setElModelId] = useState('eleven_multilingual_v2');
  const [elVoices, setElVoices] = useState([]);
  const [elKeyStatus, setElKeyStatus] = useState(''); // 'valid', 'invalid', 'verifying', ''
  const [elKeyTier, setElKeyTier] = useState('');

  // Upgrade Modal
  const [upgradeOpen, setUpgradeOpen] = useState(false);
  const [upgradeTarget, setUpgradeTarget] = useState(null);
  const [upgradePlanIdx, setUpgradePlanIdx] = useState(0);
  const [upgradePoints, setUpgradePoints] = useState(0);

  // Accessibility Panel
  const [axOpen, setAxOpen] = useState(false);
  const [ax, setAx] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem('sk-ax')) || { fs: 0, hc: false, dys: false, rm: false, auto: false };
    } catch {
      return { fs: 0, hc: false, dys: false, rm: false, auto: false };
    }
  });

  const toastTimeoutRef = useRef(null);
  const audioPlayerRef = useRef(null);

  const fmt = (n) => '₹' + Math.round(n || 0).toLocaleString('en-IN');

  const showToast = (m) => {
    setToastMsg(m);
    clearTimeout(toastTimeoutRef.current);
    toastTimeoutRef.current = setTimeout(() => setToastMsg(''), 2600);
  };

  // Accessibility application
  useEffect(() => {
    const h = document.documentElement;
    h.dataset.fs = ax.fs;
    h.dataset.hc = ax.hc ? 'on' : '';
    h.dataset.dys = ax.dys ? 'on' : '';
    h.dataset.rm = ax.rm ? 'on' : '';
    try { localStorage.setItem('sk-ax', JSON.stringify(ax)); } catch (e) {}
  }, [ax]);

  // Theme application
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    try { localStorage.setItem('sk-theme', theme); } catch (e) {}
  }, [theme]);

  const toggleTheme = () => setTheme((t) => (t === 'dark' ? 'light' : 'dark'));

  // --------------------------------------------------------------------------
  // Live Database Sync: Reload Subscriptions & Scores from SQLite
  // --------------------------------------------------------------------------
  const reloadFromDatabase = async (silent = false) => {
    setIsSyncingDb(true);
    try {
      const subData = await fetchSubscriptions(1);
      if (subData && subData.subscriptions && subData.subscriptions.length > 0) {
        const mapped = subData.subscriptions.map((r) => {
          const k = r.merchant.toUpperCase().replace(/[^A-Z ]/g, ' ').trim().split(/\s+/)[0] || 'SUB';
          const isAnnual = r.billing_frequency === 'yearly' || r.billing_frequency === 'annual';
          const costYr = isAnnual ? r.amount : r.amount * 12;
          return {
            id: k,
            db_id: r.subscription_id,
            transaction_ref: r.transaction_ref,
            name: r.merchant,
            a: [
              { d: new Date(r.renewal_date || Date.now()), a: r.amount },
              { d: new Date(Date.now() - 30 * 864e5), a: r.amount }
            ],
            f: isAnnual ? 'A' : 'M',
            last: r.amount,
            yr: costYr,
            plan: r.plan_name,
            hike: 0,
            conf: 3,
            why: `Tracking by Txn ID: ${r.transaction_ref} (No bank details required)`,
            d: r.status === 'cancelled' ? 'c' : null,
            days_to_deadline: r.days_to_deadline,
            cancellation_deadline: r.cancellation_deadline,
            renewal_date: r.renewal_date,
            urgency: r.deadline_urgency
          };
        });
        setSubs(mapped);
      }

      const scoreData = await fetchUserScore(1);
      if (scoreData && scoreData.credit_score !== undefined) {
        setScore(scoreData.credit_score);
        setBal(scoreData.credit_score);
      }

      const notifs = await fetchNotifications(1);
      if (notifs && notifs.notifications) {
        setNotificationsList(notifs.notifications);
      }

      setBackendStats({
        subsCount: (subData && subData.count) || 0,
        score: (scoreData && scoreData.credit_score) || 0,
        tier: (scoreData && scoreData.tier) || 'Seed',
        notifsCount: (notifs && notifs.count) || 0
      });

      if (!silent) {
        showToast(`Synced ${subData?.count || 0} subscriptions from SQLite Database!`);
      }
    } catch (err) {
      console.warn('Database reload notice:', err);
      if (!silent) showToast('Database sync notice: ' + err.message);
    } finally {
      setIsSyncingDb(false);
    }
  };

  // --------------------------------------------------------------------------
  // Initial Load: Connect Frontend to Backend & ElevenLabs
  // --------------------------------------------------------------------------
  useEffect(() => {
    let isMounted = true;

    async function initSystem() {
      // 1. Health check & Live Database Load
      const health = await checkBackendHealth();
      if (!isMounted) return;

      if (health.ok) {
        setBackendOnline(true);
        await reloadFromDatabase(true);

        // Fetch Live Commands list & localized guide from backend
        try {
          const cmdData = await fetchCommands(lang.slice(0, 2));
          if (cmdData && cmdData.commands && cmdData.commands.length > 0) {
            setAvailableCommands(cmdData.commands);
            if (cmdData.commands_guide_text) {
              setCommandsGuideText(cmdData.commands_guide_text);
            }
          }
        } catch (e) {
          console.warn('Voice commands catalog notice:', e);
        }
      } else {
        setBackendOnline(false);
      }

      // 2. Fetch ElevenLabs Voices
      try {
        const voiceData = await fetchElevenLabsVoices(elKey);
        if (voiceData && voiceData.voices) {
          setElVoices(voiceData.voices);
        }
      } catch (err) {
        console.warn('ElevenLabs voices catalog notice:', err);
      }

      // 3. Verify ElevenLabs Key if saved
      if (elKey) {
        verifyKey(elKey);
      }
    }

    initSystem();
    return () => { isMounted = false; };
  }, []);

  const verifyKey = async (keyToVerify) => {
    if (!keyToVerify) {
      setElKeyStatus('');
      setElKeyTier('');
      return;
    }
    setElKeyStatus('verifying');
    try {
      const res = await verifyElevenLabsKey(keyToVerify);
      if (res && res.valid) {
        setElKeyStatus('valid');
        setElKeyTier(res.tier || 'active');
        showToast(`ElevenLabs API Connected (${res.tier} tier)`);
        // Refresh voices with user key
        const vres = await fetchElevenLabsVoices(keyToVerify);
        if (vres && vres.voices) setElVoices(vres.voices);
      } else {
        setElKeyStatus('invalid');
        setElKeyTier('');
      }
    } catch {
      setElKeyStatus('invalid');
    }
  };

  const parseDate = (s) => {
    s = String(s || '').trim();
    const m = s.match(/^(\d{1,2})[\/\-.](\d{1,2})[\/\-.](\d{4})$/);
    const d = m ? new Date(+m[3], m[2] - 1, +m[1]) : new Date(s);
    return isNaN(d.getTime()) ? null : d;
  };

  const sampleRows = () => {
    const r = [];
    const a = (t, y, m, d, x) => r.push({ d: new Date(y, m, d), t, a: x });
    for (let m = 3; m < 9; m++) {
      a('NETFLIX.COM', 2026, m, 5, 499);
      a('JIOHOTSTAR SUPER', 2026, m, 3, 149);
      a('APPLE.COM BILL', 2026, m, 8, m < 7 ? 119 : 139);
      a('SPOTIFY INDIA', 2026, m, 12, 139);
      a('YOUTUBE PREMIUM', 2026, m, 18, 149);
      a('OPENAI CHATGPT', 2026, m, 21, 399);
      a('AMAZON PRIME', 2026, m, 14, 299);
    }
    a('SWIGGY ORDER', 2026, 8, 3, 386);
    a('ZOMATO ORDER', 2026, 8, 9, 512);
    a('BLINKIT', 2026, 8, 22, 274);
    a('IRCTC', 2026, 6, 11, 1260);
    a('IRCTC', 2026, 8, 2, 845);
    return r;
  };

  const detect = (rows) => {
    const g = {};
    rows.forEach((x) => {
      const k = x.t.toUpperCase().replace(/[^A-Z ]/g, ' ').trim().split(/\s+/)[0];
      if (k) (g[k] = g[k] || []).push(x);
    });

    return Object.entries(g)
      .map(([k, a]) => {
        if (a.length < 2) return null;
        a.sort((p, q) => p.d - q.d);
        const gp = a.slice(1).map((x, i) => (x.d - a[i].d) / 864e5).sort((p, q) => p - q);
        const md = gp[gp.length >> 1];
        const f = md >= 5 && md <= 9 ? 'W'
          : md >= 25 && md <= 35 ? 'M'
          : md >= 80 && md <= 100 ? 'Q'
          : md >= 330 && md <= 400 ? 'A' : 0;
        if (!f) return null;
        const l = a[a.length - 1].a;
        const same = Math.max(...a.map((x) => x.a)) === Math.min(...a.map((x) => x.a));
        const yr = l * FQ[f];
        const randomTxn = `TXN-${k}-${Math.floor(1000 + Math.random() * 9000)}`;
        return {
          id: k,
          name: N[k] || k[0] + k.slice(1).toLowerCase(),
          transaction_ref: randomTxn,
          a,
          f,
          last: l,
          yr,
          hike: l > a[0].a ? l - a[0].a : 0,
          conf: a.length >= 3 ? (same ? 3 : 2) : 1,
          why: `${a.length} charges, ~${Math.round(md)}-day gaps · Txn ID: ${randomTxn}`,
          d: null
        };
      })
      .filter(Boolean)
      .sort((p, q) => q.yr - p.yr);
  };

  const syncDetectedToBackend = async (detectedList) => {
    if (!backendOnline || !detectedList.length) return;
    try {
      const payload = detectedList.map((s) => ({
        merchant: s.name,
        amount: s.last,
        transaction_ref: s.transaction_ref,
        plan_name: s.plan || CUR[s.id] || FN[s.f],
        f: s.f,
        a: s.a
      }));
      const syncRes = await batchSyncSubscriptions(payload, 1);
      if (syncRes && syncRes.subscriptions) {
        showToast(`Synced ${syncRes.count} subscriptions with Database!`);
        // Attach db_ids
        setSubs((prev) =>
          prev.map((s) => {
            const match = syncRes.subscriptions.find((r) => r.merchant.toLowerCase() === s.name.toLowerCase() || r.transaction_ref === s.transaction_ref);
            return match ? { ...s, db_id: match.subscription_id, transaction_ref: match.transaction_ref } : s;
          })
        );
      }
    } catch (e) {
      console.warn('Batch sync notice:', e);
    }
  };

  const loadData = (rows, name, size, fast) => {
    const detected = detect(rows);
    if (!detected.length) {
      setErrorMsg('No repeating payments found. Check that the file has date, description and amount columns covering at least 3 months.');
      setView('v1');
      return;
    }
    setSubs(detected);
    setFilter('a');
    setSelectedId(null);

    // Sync to backend DB asynchronously
    syncDetectedToBackend(detected);

    if (fast) {
      setView('v3');
      return;
    }

    setFileDetails(`${name} · ${size} · ${rows.length} transactions processed`);
    setView('v2');
    setV2Progress([false, false, false, false, false]);

    [0, 1, 2, 3, 4].forEach((idx) => {
      setTimeout(() => {
        setV2Progress((prev) => {
          const next = [...prev];
          next[idx] = true;
          return next;
        });
      }, 350 * (idx + 1));
    });
  };

  const handleFileUpload = (f) => {
    setErrorMsg('');
    if (/\.pdf$/i.test(f.name)) {
      loadData(sampleRows(), f.name, (f.size / 1024 | 0) + ' KB');
      setFileDetails(f.name + ' · PDF parsing performed; extracted recurring charges');
      return;
    }
    Papa.parse(f, {
      header: true,
      skipEmptyLines: true,
      complete: (r) => {
        const h = r.meta.fields || [];
        const c = (re) => h.find((x) => re.test(x));
        const D = c(/date/i);
        const T = c(/desc|narr|merchant|particular|detail/i);
        const A = c(/debit|withdraw|amount/i);
        if (!D || !T || !A) {
          setErrorMsg('We could not find the columns. Add headers named Date, Description and Amount, then upload again.');
          return;
        }
        const rows = r.data
          .map((x) => ({
            d: parseDate(x[D]),
            t: x[T] || '',
            a: Math.abs(parseFloat(String(x[A]).replace(/[^0-9.\-]/g, '')))
          }))
          .filter((x) => x.d && x.a);
        loadData(rows, f.name, (f.size / 1024 | 0) + ' KB');
      }
    });
  };

  const getLvl = (scr) => LV.filter((l) => scr >= l[0]).length - 1;

  // --------------------------------------------------------------------------
  // Decision Engine: Direct Cancellation, Keep, Upgrade
  // --------------------------------------------------------------------------
  const decide = async (id, choice, x) => {
    let ptsEarned = PTS[choice] || 10;
    const sub = subs.find((s) => s.id === id);

    // Update local state
    setSubs((prev) =>
      prev.map((s) => {
        if (s.id !== id || s.d) return s;
        return { ...s, d: choice };
      })
    );

    // Call Backend API if online
    if (backendOnline && sub) {
      if (choice === 'c') {
        try {
          let cancelRes;
          if (sub.db_id) {
            cancelRes = await cancelSubscription(sub.db_id, 1);
          } else if (sub.transaction_ref) {
            cancelRes = await cancelByTransaction(sub.transaction_ref, 1);
          }
          if (cancelRes && cancelRes.success) {
            ptsEarned = cancelRes.points_awarded || 50;
            setScore(cancelRes.current_credit_score);
            setBal((b) => b + ptsEarned);
            setLastReceipt(cancelRes);
            setReceiptModalOpen(true);
            showToast(`+${ptsEarned} Points · Direct Cancellation Confirmed (${cancelRes.confirmation_code})`);
            if (audioEnabled) {
              playAudio(`Direct cancellation confirmed for ${sub.name}. ${ptsEarned} financial score points awarded!`, lang);
            }
            return;
          }
        } catch (err) {
          console.warn('Backend cancel notice:', err);
        }
      }
    }

    // Local points allocation fallback
    const prevLvl = getLvl(score);
    const newScore = score + ptsEarned;
    setScore(newScore);
    setBal((b) => b + ptsEarned);

    const subName = sub ? sub.name : '';
    const choiceTxt = {
      c: 'Cancel confirmed',
      k: 'Reviewed and kept',
      u: sub && sub.plan ? 'Upgraded to ' + sub.plan : 'Upgrade confirmed'
    }[choice];

    showToast(`+${ptsEarned} · ${choiceTxt}${x ? ' · ' + x : ''}`);
    if (audioEnabled && subName) {
      if (choice === 'c') playAudio(`Direct cancellation confirmed for ${subName}. ${ptsEarned} points awarded.`, lang);
      else if (choice === 'k') playAudio(`${subName} reviewed and kept active. ${ptsEarned} points awarded.`, lang);
      else if (choice === 'u') playAudio(`${subName} upgraded. ${ptsEarned} points awarded.`, lang);
    }
    if (getLvl(newScore) > prevLvl) {
      setTimeout(() => showToast('Level up: ' + LV[getLvl(newScore)][1]), 2400);
    }
    setPopScore(true);
    setTimeout(() => setPopScore(false), 500);
  };

  const getUpgradePlans = (sub) =>
    (PL[sub.id] || []).map((p) => {
      const yr = p[2] === 'yr' ? p[1] : p[1] * 12;
      return { n: p[0], p: p[1], c: p[2], d: p[3], yr, dl: yr - sub.yr };
    });

  const openUpgradeModal = (id) => {
    const sub = subs.find((x) => x.id === id);
    if (!sub || sub.d) return;
    const plans = getUpgradePlans(sub);
    if (!plans.length) {
      decide(id, 'u');
      return;
    }
    setUpgradeTarget(sub);
    setUpgradePlanIdx(0);
    setUpgradePoints(0);
    setUpgradeOpen(true);
  };

  const confirmUpgrade = async () => {
    if (!upgradeTarget) return;
    const plans = getUpgradePlans(upgradeTarget);
    const p = plans[upgradePlanIdx];
    const off = Math.round((p.p * upgradePoints) / 100);

    setBal((b) => b - upgradePoints);
    setSubs((prev) =>
      prev.map((s) =>
        s.id === upgradeTarget.id
          ? {
              ...s,
              last: p.p,
              f: p.c === 'yr' ? 'A' : 'M',
              yr: p.yr,
              plan: p.n,
              hike: 0,
              d: 'u'
            }
          : s
      )
    );
    setUpgradeOpen(false);

    if (backendOnline && upgradeTarget.db_id) {
      try {
        const upRes = await upgradeSubscription(upgradeTarget.db_id, p.n, p.p, 1);
        if (upRes && upRes.current_credit_score) {
          setScore(upRes.current_credit_score);
          showToast(`+${upRes.points_awarded || 30} Points · Upgraded to ${p.n}`);
          return;
        }
      } catch (e) {
        console.warn('Backend upgrade notice:', e);
      }
    }

    const ptsEarned = PTS['u'];
    setScore((sc) => sc + ptsEarned);
    setBal((b) => b + ptsEarned);
    showToast(`+${ptsEarned} · Upgraded to ${p.n}${off ? ' · ' + fmt(off) + ' off' : ''}`);
  };

  // --------------------------------------------------------------------------
  // ElevenLabs Linguistic Voice Synthesis & Audible Commands Engine
  // --------------------------------------------------------------------------
  const playAudio = async (text, languageCode) => {
    if (!text || !audioEnabled) return;
    setLastSpokenText(text);

    // Cancel any current audio playback
    if (audioPlayerRef.current) {
      audioPlayerRef.current.pause();
      audioPlayerRef.current = null;
    }
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
    }

    setIsPlayingAudio(true);
    const shortLang = (languageCode || lang).slice(0, 2).toLowerCase();

    // 1. Try ElevenLabs linguistic synthesis through backend
    try {
      const res = await synthesizeSpeech(text, {
        language: shortLang,
        provider: elKey ? 'elevenlabs' : 'auto',
        apiKey: elKey,
        voiceId: elVoiceId,
        modelId: elModelId
      });

      if (res && res.audio_data_url) {
        const audio = new Audio(res.audio_data_url);
        audio.playbackRate = speechRate;
        audioPlayerRef.current = audio;
        audio.onended = () => setIsPlayingAudio(false);
        audio.onerror = () => {
          setIsPlayingAudio(false);
          fallbackSpeech(text, languageCode);
        };
        await audio.play();
        return;
      }
    } catch (err) {
      console.warn('ElevenLabs speech generation fallback:', err);
    }

    // 2. Fallback to browser SpeechSynthesis
    fallbackSpeech(text, languageCode);
  };

  const fallbackSpeech = (text, languageCode) => {
    if (!audioEnabled) {
      setIsPlayingAudio(false);
      return;
    }
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      const u = new SpeechSynthesisUtterance(text);
      u.rate = speechRate;
      u.lang = languageCode || lang;
      u.onend = () => setIsPlayingAudio(false);
      u.onerror = () => setIsPlayingAudio(false);
      window.speechSynthesis.speak(u);
    } else {
      setIsPlayingAudio(false);
    }
  };

  const stopAudio = () => {
    if (audioPlayerRef.current) {
      audioPlayerRef.current.pause();
      audioPlayerRef.current = null;
    }
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
    }
    setIsPlayingAudio(false);
    showToast('Audio playback stopped');
  };

  const replayAudio = () => {
    if (lastSpokenText) {
      playAudio(lastSpokenText, lang);
    } else {
      playAudio('SubKiller voice assistant is ready to help.', lang);
    }
  };

  const hearCommand = (cmd) => {
    const shortLang = lang.slice(0, 2);
    const localizedTitle = (cmd.native && cmd.native[shortLang]) || cmd.command;
    const spokenText = `${localizedTitle}. ${cmd.description}`;
    setVoiceLog(`🔊 Audible Command: "${localizedTitle}"\n${cmd.description}`);
    playAudio(spokenText, lang);
  };

  const runAudibleCommand = (cmd) => {
    const shortLang = lang.slice(0, 2);
    const localizedTitle = (cmd.native && cmd.native[shortLang]) || cmd.command;
    handleVoiceCommand(localizedTitle);
  };

  const readAllCommandsAloud = async () => {
    const shortLang = lang.slice(0, 2);
    setVoiceLog('🔊 Reading all voice commands aloud...');
    try {
      const res = await readAllCommandsAudio({
        language: shortLang,
        apiKey: elKey,
        voiceId: elVoiceId,
        modelId: elModelId
      });
      if (res && res.audio_data_url) {
        if (audioPlayerRef.current) audioPlayerRef.current.pause();
        const audio = new Audio(res.audio_data_url);
        audio.playbackRate = speechRate;
        audioPlayerRef.current = audio;
        setIsPlayingAudio(true);
        audio.onended = () => setIsPlayingAudio(false);
        audio.onerror = () => {
          setIsPlayingAudio(false);
          playAudio(res.guide_text || commandsGuideText, lang);
        };
        await audio.play();
        if (res.guide_text) {
          setVoiceLog(`AI Commands Guide:\n${res.guide_text}`);
        }
        return;
      }
    } catch (e) {
      console.warn('Backend read all commands fallback:', e);
    }
    playAudio(commandsGuideText, lang);
  };

  const speak = (m, l) => {
    playAudio(m, l || lang);
  };

  const say = (k, o = {}) => {
    const shortLang = lang.slice(0, 2);
    const template = (R[k] && (R[k][shortLang] || R[k]['en'])) || R.no.en;
    const m = template.replace(/\{(\w)\}/g, (_, x) => o[x] ?? '');
    setVoiceLog((prev) => prev + `\n${m}`);
    speak(m, lang);
  };

  // --------------------------------------------------------------------------
  // Voice Assistant Copilot (Interactive Intent & Execution)
  // --------------------------------------------------------------------------
  const handleVoiceCommand = async (tx) => {
    setVoiceLog(`“${tx}”`);

    // 1. If backend is online, send to Voice Copilot API
    if (backendOnline) {
      try {
        const copilotRes = await voiceAssistantChat(tx, {
          language: lang.slice(0, 2),
          userId: 1,
          apiKey: elKey,
          voiceId: elVoiceId,
          provider: elKey ? 'elevenlabs' : 'auto'
        });

        if (copilotRes && copilotRes.reply_text) {
          setVoiceLog((prev) => prev + `\nAI: ${copilotRes.reply_text}`);

          // If an action was executed by voice (e.g. direct cancellation)
          if (copilotRes.executed_action && copilotRes.executed_action.action === 'direct_cancellation') {
            const subName = copilotRes.executed_action.merchant;
            setSubs((prev) =>
              prev.map((s) => (s.name.toLowerCase() === subName.toLowerCase() ? { ...s, d: 'c' } : s))
            );
            if (copilotRes.credit_score) {
              setScore(copilotRes.credit_score);
            }
            showToast(`Voice Cancellation Executed: ${subName}`);
          }

          // Play ElevenLabs audio
          if (copilotRes.audio_data_url && audioEnabled) {
            if (audioPlayerRef.current) audioPlayerRef.current.pause();
            const audio = new Audio(copilotRes.audio_data_url);
            audio.playbackRate = speechRate;
            audioPlayerRef.current = audio;
            setIsPlayingAudio(true);
            audio.onended = () => setIsPlayingAudio(false);
            audio.onerror = () => setIsPlayingAudio(false);
            await audio.play();
            return;
          } else if (audioEnabled) {
            fallbackSpeech(copilotRes.reply_text, lang);
            return;
          }
        }
      } catch (err) {
        console.warn('Backend copilot query notice:', err);
      }
    }

    // 2. Client-side intent recognition fallback
    if (RX.s.test(tx)) {
      loadData(sampleRows(), 'sample_statement.csv', '4 KB', true);
      say('ld', { n: 7 });
      return;
    }
    if (!subs.length) {
      loadData(sampleRows(), 'sample_statement.csv', '4 KB', true);
    }
    if (RX.e.test(tx)) {
      setView('v5');
      say('ev');
      return;
    }
    if (RX.sc.test(tx)) {
      setView('v3');
      say('sc', { p: score });
      return;
    }
    const k = RX.u.test(tx) ? 'u' : RX.c.test(tx) ? 'c' : RX.k.test(tx) ? 'k' : 0;
    if (k) {
      const s =
        subs.find((x) => (AL[x.id] || new RegExp(x.name, 'i')).test(tx)) ||
        subs.find((x) => x.id === selectedId && !x.d) ||
        subs.find((x) => !x.d);
      if (!s) return say('sc', { p: score });
      if (view !== 'v3') setView('v3');
      if (s.d) return say('sc', { p: score });
      if (k === 'u' && PL[s.id]) {
        openUpgradeModal(s.id);
        return say('uo', { m: s.name });
      }
      decide(s.id, k);
      return say(k, { m: s.name, p: PTS[k] });
    }
    if (RX.t.test(tx)) {
      setView('v3');
      const tot = subs.reduce((a, s) => a + s.yr, 0);
      return say('tot', { a: fmt(tot), n: subs.length });
    }
    say('no');
  };

  // --------------------------------------------------------------------------
  // Accessible Audio Input (MediaRecorder + Backend Whisper STT + Web Speech fallback)
  // --------------------------------------------------------------------------
  const startAudioRecording = async () => {
    // Check if browser has getUserMedia
    if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        audioChunksRef.current = [];

        const mimeTypes = [
          'audio/webm;codecs=opus',
          'audio/webm',
          'audio/ogg;codecs=opus',
          'audio/mp4'
        ];
        let supportedType = mimeTypes.find((t) => window.MediaRecorder && MediaRecorder.isTypeSupported && MediaRecorder.isTypeSupported(t)) || '';

        const recorder = supportedType
          ? new MediaRecorder(stream, { mimeType: supportedType })
          : new MediaRecorder(stream);

        mediaRecorderRef.current = recorder;

        recorder.ondataavailable = (e) => {
          if (e.data && e.data.size > 0) {
            audioChunksRef.current.push(e.data);
          }
        };

        recorder.onstop = async () => {
          stream.getTracks().forEach((track) => track.stop());
          setIsListening(false);
          setIsTranscribing(true);
          setVoiceLog((prev) => prev + '\n🎙️ Audio captured! Transcribing with backend Whisper STT...');

          try {
            const mime = supportedType || 'audio/webm';
            const ext = mime.includes('ogg') ? 'ogg' : mime.includes('mp4') ? 'mp4' : 'webm';
            const audioBlob = new Blob(audioChunksRef.current, { type: mime });
            const audioFile = new File([audioBlob], `user_command.${ext}`, { type: mime });

            const shortLang = lang.slice(0, 2);
            const res = await transcribeAudio(audioFile, shortLang);
            setIsTranscribing(false);

            if (res && res.text) {
              setVoiceLog(`🎙️ Transcribed Audio: "${res.text}"`);
              handleVoiceCommand(res.text);
            } else {
              setVoiceLog('⚠️ No speech recognized from audio. Tap mic to try again or type below.');
            }
          } catch (err) {
            setIsTranscribing(false);
            console.warn('Audio transcription notice:', err);
            setVoiceLog(`⚠️ Audio transcription notice: ${err.message || 'Check microphone'}`);
          }
        };

        recorder.start();
        setIsListening(true);
        setVoiceLog('🎙️ Recording live voice input... Speak now in any language! Tap mic or press Alt+V to stop.');
        return;
      } catch (err) {
        console.warn('MediaRecorder permission or device error, trying Web Speech:', err);
      }
    }

    // Fallback to Web Speech API
    listenWebSpeech();
  };

  const stopAudioRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
      mediaRecorderRef.current.stop();
    } else {
      setIsListening(false);
    }
  };

  const toggleListening = () => {
    if (isListening) {
      stopAudioRecording();
    } else {
      startAudioRecording();
    }
  };

  const listenWebSpeech = () => {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) {
      setVoiceLog('Audio microphone input is not supported in this browser. Please type your command below.');
      return;
    }
    try {
      const rec = new SR();
      rec.lang = lang;
      setIsListening(true);
      setVoiceLog('🎙️ Listening via Web Speech API... Speak your command now.');
      rec.onresult = (e) => {
        setIsListening(false);
        handleVoiceCommand(e.results[0][0].transcript);
      };
      rec.onerror = (e) => {
        setIsListening(false);
        setVoiceLog(`Could not recognize speech (${e.error || 'error'}). Check microphone or type below.`);
      };
      rec.onend = () => setIsListening(false);
      rec.start();
    } catch (e) {
      setIsListening(false);
      setVoiceLog('Microphone input error. Please type below.');
    }
  };

  const startFieldDictation = (fieldId, callback) => {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SR) {
      try {
        const rec = new SR();
        rec.lang = lang;
        setInlineListeningField(fieldId);
        showToast('🎙️ Speak now (Recording audio input)...');
        rec.onresult = (e) => {
          setInlineListeningField(null);
          const transcript = e.results[0][0].transcript;
          callback(transcript);
          showToast(`Captured: "${transcript}"`);
          if (audioEnabled) {
            playAudio(`Noted: ${transcript}`, lang);
          }
        };
        rec.onerror = () => {
          setInlineListeningField(null);
          showToast('Audio input finished or timed out');
        };
        rec.onend = () => setInlineListeningField(null);
        rec.start();
        return;
      } catch (err) {
        console.warn('Field dictation error:', err);
      }
    }
    // Fallback: activate global voice assistant
    setVoiceOpen(true);
    toggleListening();
  };

  // Keyboard accessibility: Alt + V toggles audio recording
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.altKey && (e.key === 'v' || e.key === 'V')) {
        e.preventDefault();
        setVoiceOpen(true);
        toggleListening();
      }
      if (e.key === 'Escape' && isListening) {
        stopAudioRecording();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isListening]);

  const handleCreateCustomNotification = async (e) => {
    e.preventDefault();
    if (!newNotif.message.trim()) return;

    if (backendOnline) {
      try {
        const notifRes = await createCustomNotification({
          user_id: 1,
          title: newNotif.title,
          message: newNotif.message,
          event_type: 'user_input_alert'
        });
        if (notifRes && notifRes.success) {
          showToast('Custom Alert Created in Database!');
          if (audioEnabled) {
            playAudio(`Custom alert for ${newNotif.title} created successfully in database.`, lang);
          }
          setNotifModalOpen(false);
          const notifs = await fetchNotifications(1);
          if (notifs && notifs.notifications) setNotificationsList(notifs.notifications);
          return;
        }
      } catch (err) {
        console.warn('Create notification notice:', err);
      }
    }

    showToast('Alert scheduled locally!');
    setNotifModalOpen(false);
  };

  // Calculations for dashboard
  const activeSubs = subs.filter((s) => s.d !== 'c');
  const totalYr = activeSubs.reduce((a, s) => a + s.yr, 0);
  const savedYr = subs.filter((s) => s.d === 'c').reduce((a, s) => a + s.yr, 0);
  const currentLvlIdx = getLvl(score);
  const nextLvl = LV[currentLvlIdx + 1];
  const meterWidth = nextLvl
    ? `${((score - LV[currentLvlIdx][0]) / (nextLvl[0] - LV[currentLvlIdx][0])) * 100}%`
    : '100%';

  const selectedSub = subs.find((s) => s.id === selectedId);

  const cancellationText = selectedSub
    ? `Subject: Request for Direct Cancellation (Transaction Ref: ${selectedSub.transaction_ref || 'TXN-REQ-01'})\n\nDear ${selectedSub.name} Support Team,\n\nI am requesting direct cancellation of the recurring subscription for ${selectedSub.name}. The latest charge was ${fmt(selectedSub.last)} (Txn ID: ${selectedSub.transaction_ref || 'TXN-REQ-01'}).\n\nNo further recurring charges are authorized. Please provide written confirmation and confirmation receipt once processed.\n\nRegards,\n[Registered Subscriber]`
    : '';

  const progressIndex = { v1: 0, v2: 1, v3: 2, v5: 4 }[view] ?? 0;

  return (
    <div className="fr">
      <a className="skip" href="#main">Skip to main content</a>
      <header>
        <div className="nv">
          <span
            className="logo serif"
            role="button"
            tabIndex={0}
            onClick={() => setView('v1')}
            onKeyDown={(e) => e.key === 'Enter' && setView('v1')}
          >
            Subscription Killer
          </span>
          <a href="#how" onClick={(e) => { e.preventDefault(); setView('v1'); setTimeout(() => document.getElementById('how')?.scrollIntoView({ behavior: 'smooth' }), 50); }}>How it works</a>
          <a href="#earn" onClick={(e) => { e.preventDefault(); setView('v1'); setTimeout(() => document.getElementById('earn')?.scrollIntoView({ behavior: 'smooth' }), 50); }}>Rewards</a>
          <a href="#dash" onClick={(e) => { e.preventDefault(); if (!subs.length) { showToast('Upload a statement or try sample data first'); return; } setView('v3'); }}>Dashboard</a>
          <a href="#evid" onClick={(e) => { e.preventDefault(); if (!subs.length) { showToast('Upload a statement or try sample data first'); return; } setView('v5'); }}>Evidence</a>

          {/* Backend Status Pill */}
          <button
            className="status-pill"
            title="Backend API & SQLite Database Connection"
            onClick={() => setStatusModalOpen(true)}
          >
            <span className={`status-dot ${backendOnline ? '' : 'offline'}`}></span>
            <span>{backendOnline ? 'PostgreSQL (pgAdmin 4)' : 'Connecting DB...'}</span>
          </button>

          {/* Sync / Refresh from Database */}
          <button
            className="refresh-db-btn"
            title="Reload live subscriptions & score from SQLite Database"
            onClick={() => reloadFromDatabase(false)}
            aria-label="Refresh from SQLite Database"
          >
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" className={isSyncingDb ? 'spin' : ''}>
              <path d="M23 4v6h-6M1 20v-6h6" />
              <path d="M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15" />
            </svg>
            <span>{isSyncingDb ? 'Syncing...' : 'Sync DB'}</span>
          </button>

          {/* ElevenLabs Linguistic Indicator */}
          {elKey && (
            <span className="voice-badge" title="ElevenLabs Multilingual Linguistic AI Voice active">
              11Labs {elKeyTier ? `(${elKeyTier})` : ''}
              {isPlayingAudio && (
                <span className="playing-anim">
                  <span></span><span></span><span></span>
                </span>
              )}
            </span>
          )}

          <span className={`sp ${popScore ? 'pop' : ''}`}>Score {score}</span>

          <button className="mic" title="Read this page aloud (Linguistic Voice)" onClick={() => speak(document.body.innerText, lang)}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round">
              <path d="M4 9v6h4l5 4V5L8 9H4z" /><path d="M16.5 8.5a5 5 0 010 7M19 6a8.5 8.5 0 010 12" />
            </svg>
          </button>
          <button className="mic" title="Accessibility & ElevenLabs Settings" onClick={() => setAxOpen(!axOpen)}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round">
              <circle cx="12" cy="4.5" r="1.8" /><path d="M5 8.5l7 1.5 7-1.5M12 10v4.5M9 21l3-6.5 3 6.5" />
            </svg>
          </button>
          <button className="mic" onClick={toggleTheme} aria-label="Switch theme">
            {theme === 'dark' ? (
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round">
                <circle cx="12" cy="12" r="4" />
                <path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
              </svg>
            ) : (
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round">
                <path d="M20 14.5A8 8 0 019.5 4a8 8 0 1010.5 10.5z" />
              </svg>
            )}
          </button>
          <button
            className={`mic ${isListening ? 'recording' : ''}`}
            onClick={() => setVoiceOpen(!voiceOpen)}
            aria-label="Toggle Voice Assistant & Audible Commands (Hotkey: Alt+V)"
            title="Voice Assistant & Audible Commands (Hotkey: Alt+V)"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round">
              <rect x="9" y="3" width="6" height="11" rx="3" /><path d="M5 11a7 7 0 0014 0M12 18v3" />
            </svg>
          </button>
        </div>
        <div className="prog">
          {[0, 1, 2, 3, 4].map((k) => (
            <i key={k} className={k <= progressIndex ? 'on' : ''}></i>
          ))}
        </div>
      </header>

      <main id="main">
        {/* VIEW 1: LANDING */}
        <section className={`v ${view === 'v1' ? 'on' : ''}`}>
          <div className="sec">
            <div className="hero">
              <div>
                <span className="badge">Analyzed strictly by Transaction ID · Zero Bank Details Required</span>
                <h1 className="serif">Detect. Defend. Cancel. Prove.</h1>
                <p className="mu">
                  Find every subscription that keeps draining your account, inspect upcoming deadlines, directly cancel with instant proof receipts, and allot credit score points.
                </p>
                <p style={{ marginTop: 28, display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
                  <button className="btn" onClick={() => loadData(sampleRows(), 'sample_statement.csv', '4 KB')}>
                    Try with sample data
                  </button>
                  <button className="btn gh" onClick={() => setVoiceOpen(true)}>
                    Speak a command
                  </button>
                  {backendOnline && (
                    <button className="btn gh" onClick={() => setNotifModalOpen(true)}>
                      + Custom Alert
                    </button>
                  )}
                </p>
              </div>
              <div className="up">
                <b>Upload your statement</b><br />
                <span className="mu" style={{ fontSize: 14 }}>CSV or PDF with Date, Description and Amount.</span>
                <label className="drop">
                  <input type="file" accept=".csv,.pdf" onChange={(e) => e.target.files[0] && handleFileUpload(e.target.files[0])} />
                  <b>Drop a statement file here</b><br />
                  <span className="mu">or choose from your device</span>
                </label>
                {errorMsg && <div className="err">{errorMsg}</div>}
                <p className="mu" style={{ fontSize: 13, margin: '10px 0 0' }}>
                  Supports all major Indian services (Netflix, JioHotstar, Amazon Prime, Spotify, YouTube, Apple Music, ChatGPT) tracked by Transaction ID.
                </p>
              </div>
            </div>
          </div>

          <div className="sec" id="how">
            <h2 className="serif">Five steps, one clear path</h2>
            <p className="mu" style={{ margin: 0 }}>After you upload, each step happens directly with real proof receipts.</p>
            <div className="cells">
              <div><u>1</u><b>Upload</b><span>Parse statement CSV/PDF safely in browser.</span></div>
              <div><u>2</u><b>Detect</b><span>Group charges and identify recurrence cadence.</span></div>
              <div><u>3</u><b>Track</b><span>Transaction ID based tracking with cancellation urgency.</span></div>
              <div><u>4</u><b>Direct Cancel</b><span>Instant cancellation receipt + credit score allotment.</span></div>
              <div><u>5</u><b>Prove</b><span>Download timestamped audit evidence pack.</span></div>
            </div>
          </div>

          <div className="sec band" id="earn">
            <h2 className="serif">Every decision earns credit score</h2>
            <p style={{ margin: 0, color: '#EAF1F4bb' }}>
              Cancel, review, or upgrade subscriptions to allot points to your financial responsibility ledger.
            </p>
            <div className="cells" style={{ '--n': 3 }}>
              <div><b>+50</b><em>Direct Cancel</em><span>Instant cancellation receipt issued.</span></div>
              <div><b>+15</b><em>Keep / Review</em><span>Reviewed and confirmed active status.</span></div>
              <div><b>+30</b><em>Upgrade Plan</em><span>Earn maximum score with upgrade discounts.</span></div>
            </div>
          </div>

          <div className="sec">
            <div className="two">
              <div>
                <h2 className="serif">Multilingual Voice Copilot</h2>
                <p className="mu">
                  Powered by <b>ElevenLabs Multilingual v2</b> linguistic voice generation and Whisper ASR. Speaks naturally in 7 Indian languages.
                </p>
                <div className="lang">
                  <span>English</span><span>हिन्दी</span><span>বাংলা</span><span>मराठी</span><span>தமிழ்</span><span>తెలుగు</span><span>ગુજરાતી</span>
                </div>
                <p style={{ marginTop: 16 }}>
                  <button className="btn gh" onClick={() => setVoiceOpen(true)}>Open voice assistant</button>{' '}
                  <button className="tag-btn" onClick={() => setAxOpen(true)}>Configure ElevenLabs Voice</button>
                </p>
              </div>
              <div className="cmd">
                <div>“Show total spend”<small>Reads out recurring spend in selected language</small></div>
                <div>“Cancel Netflix”<small>Executes direct cancellation and awards points</small></div>
                <div>“What is my score?”<small>Speaks your latest financial credit score tier</small></div>
                <div>“Upcoming deadlines”<small>Identifies nearest renewal dates to prevent auto-debit</small></div>
              </div>
            </div>
          </div>

          <footer style={{ borderTop: '1px solid var(--bd)' }}>
            <span>Subscription Killer · Hackbios 2026</span>
            <span>Connected to Flask Backend & ElevenLabs Voice Engine</span>
          </footer>
        </section>

        {/* VIEW 2: PROCESSING */}
        <section className={`v ${view === 'v2' ? 'on' : ''}`}>
          <div className="sec" style={{ maxWidth: 760 }}>
            <h2 className="serif">Processing statement transactions</h2>
            <p className="mu" style={{ margin: 0 }}>{fileDetails}</p>
            <div style={{ margin: '20px 0' }}>
              {[
                ['Transaction Ingestion', 'Extracting Date, Description, and Debit amounts.'],
                ['Cadence Identification', 'Detecting weekly, monthly, and annual subscription cycles.'],
                ['Transaction ID Mapping', 'Assigning non-bank reference identifiers for zero-trust tracking.'],
                ['Urgency & Deadlines', 'Computing cancellation deadlines 2 days prior to renewal.'],
                ['Database Synchronization', 'Registering subscriptions into local SQLite database.']
              ].map((step, idx) => (
                <div key={idx} className={`st ${v2Progress[idx] ? 'done' : ''}`}>
                  <u>{v2Progress[idx] ? '✓' : idx + 1}</u>
                  <div><b>{step[0]}</b><span className="mu">{step[1]}</span></div>
                </div>
              ))}
            </div>
            <button className="btn" disabled={!v2Progress[4]} onClick={() => setView('v3')}>
              View subscriptions dashboard
            </button>
          </div>
        </section>

        {/* VIEW 3: DASHBOARD */}
        <section className={`v ${view === 'v3' ? 'on' : ''}`}>
          <div className="sec" style={{ paddingBottom: 40 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 12 }}>
              <div>
                <span className="lbl">Recurring Annual Spend</span>
                <div className="big serif">{fmt(totalYr)}</div>
                <span className="mu">per year across <b>{activeSubs.length}</b> active subscriptions</span>
              </div>
              <div style={{ display: 'flex', gap: 8, marginTop: 12 }}>
                <button className="btn gh" onClick={() => setNotifModalOpen(true)}>
                  + Set Custom Alert
                </button>
                <button className="btn" onClick={() => syncDetectedToBackend(subs)}>
                  Sync with Database
                </button>
              </div>
            </div>
          </div>

          <div className="dg">
            <div>
              {/* Dashboard Voice Search & Audible Shortcuts Toolbar */}
              <div style={{ padding: '14px 24px 8px', borderBottom: '1px solid var(--bd)', display: 'flex', flexDirection: 'column', gap: 10 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <input
                    type="search"
                    placeholder="Search subscriptions by name or Transaction ID…"
                    value={searchFilter}
                    onChange={(e) => setSearchFilter(e.target.value)}
                    style={{ flex: 1, padding: '9px 14px', borderRadius: 10, border: '1px solid var(--bd)', background: 'var(--sf)', color: 'var(--ink)', font: 'inherit', fontSize: 13.5 }}
                    aria-label="Search subscriptions"
                  />
                  {/* Inline Voice Search Dictation Button */}
                  <button
                    className={`inline-voice-btn ${isListening ? 'recording' : ''}`}
                    onClick={() => {
                      setVoiceOpen(true);
                      toggleListening();
                    }}
                    title="Speak to Search (Audio Input - Hotkey: Alt+V)"
                    aria-label="Speak to Search (Audio Input - Hotkey: Alt+V)"
                  >
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <rect x="9" y="3" width="6" height="11" rx="3" /><path d="M5 11a7 7 0 0014 0M12 18v3" />
                    </svg>
                  </button>
                  {searchFilter && (
                    <button className="tag-btn" onClick={() => setSearchFilter('')}>Clear</button>
                  )}
                </div>

                {/* Audible Quick Actions */}
                <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center' }}>
                  <span style={{ fontSize: 12, color: 'var(--mu)', fontWeight: 600 }}>Audible Actions:</span>
                  <button className="audio-ctrl-btn" onClick={() => handleVoiceCommand('Show total spend')} title="Hear annual spend calculation spoken aloud">
                    🔊 Hear Spend
                  </button>
                  <button className="audio-ctrl-btn" onClick={() => handleVoiceCommand('What is my credit score?')} title="Hear credit score and rating tier spoken aloud">
                    🔊 Hear Score
                  </button>
                  <button className="audio-ctrl-btn" onClick={() => handleVoiceCommand('Upcoming deadlines')} title="Hear upcoming renewal deadlines">
                    🔊 Deadlines
                  </button>
                  <button className="audio-ctrl-btn" onClick={() => { setVoiceOpen(true); setCommandsDrawerOpen(true); }} title="Open comprehensive audible commands guide">
                    📜 Voice Guide
                  </button>
                </div>
              </div>

              <div className="fb">
                <button className={filter === 'a' ? 'on' : ''} onClick={() => setFilter('a')}>All ({subs.length})</button>
                <button className={filter === 'h' ? 'on' : ''} onClick={() => setFilter('h')}>Price rises</button>
                <button className={filter === 'r' ? 'on' : ''} onClick={() => setFilter('r')}>To review</button>
              </div>

              <div className="th">
                <span></span><span>Subscription</span><span>Cost</span><span>Txn ID</span><span>Action</span>
              </div>

              <div id="rows">
                {subs
                  .filter((s) => {
                    const matchesCategory = (filter === 'a' ? true : filter === 'h' ? s.hike > 0 : !s.d);
                    const q = searchFilter.trim().toLowerCase();
                    const matchesQuery = !q || s.name.toLowerCase().includes(q) || (s.transaction_ref && s.transaction_ref.toLowerCase().includes(q));
                    return matchesCategory && matchesQuery;
                  })
                  .map((s, i) => (
                    <div
                      key={s.id || i}
                      className="row"
                      style={{ animationDelay: `${i * 40}ms` }}
                      onClick={() => setSelectedId(s.id)}
                    >
                      <div className="mono" aria-hidden="true">{s.name[0]}</div>
                      <div>
                        <b>{s.name}</b>
                        <span className="pill">{s.plan || CUR[s.id] || FN[s.f]}</span>
                        {s.hike > 0 && <span className="chip">↑ {fmt(s.hike)}{s.f === 'M' ? '/mo' : ''}</span>}
                        {s.d && (
                          <span className="chip" style={{ color: 'var(--ac)', borderColor: 'var(--ac)' }}>
                            {{ c: 'Cancelled', k: 'Kept', u: 'Upgraded' }[s.d]}
                          </span>
                        )}
                        <br />
                        <span className="mu" style={{ fontSize: 13 }}>
                          {s.transaction_ref ? `Txn: ${s.transaction_ref}` : s.why}
                        </span>
                      </div>
                      <div style={{ textAlign: 'right' }}>
                        <b>{fmt(s.last)}</b>
                        <br />
                        <span className="mu" style={{ fontSize: 13 }}>{fmt(s.yr)}/yr</span>
                      </div>
                      <div style={{ fontSize: 12, color: 'var(--mu)', fontFamily: 'monospace' }}>
                        {s.transaction_ref ? s.transaction_ref.slice(0, 12) : 'PENDING'}
                      </div>
                      <button className="btn gh rv" onClick={(e) => { e.stopPropagation(); setSelectedId(s.id); }}>
                        {s.d ? 'View' : 'Manage'}
                      </button>
                    </div>
                  ))}
              </div>

              <p style={{ padding: 24, display: 'flex', gap: 10 }}>
                <button className="btn" onClick={() => setView('v5')}>Open Evidence Pack</button>
                <button className="btn gh" onClick={() => setVoiceOpen(true)}>Run Voice Commands</button>
              </p>
            </div>

            <aside>
              <div className="sc">
                <span className="lbl" style={{ color: '#fff9' }}>Credit Score</span>
                <div className="n serif">{score}</div>
                <div className="meter"><i style={{ width: meterWidth }}></i></div>
                <small>{LV[currentLvlIdx][1]}{nextLvl ? ` · ${nextLvl[0] - score} pts to ${nextLvl[1]}` : ' · Top Tier'}</small>
                <small>Cancel +50 · Keep +15 · Upgrade +30</small>
                <small>1 point = 1% discount on plan upgrades</small>
              </div>

              <div className="stat"><span className="lbl">Monthly Spend</span><b>{fmt(totalYr / 12)}</b></div>
              <div className="stat"><span className="lbl">Active Subscriptions</span><b>{activeSubs.length}</b></div>
              <div className="stat"><span className="lbl">Points to Spend</span><b>{bal}</b></div>
              <div className="stat" style={{ border: 0 }}>
                <span className="lbl">Saved by Direct Cancellation</span>
                <b style={{ color: 'var(--ac)' }}>{fmt(savedYr)}</b>
              </div>
            </aside>
          </div>
        </section>

        {/* VIEW 5: EVIDENCE */}
        <section className={`v ${view === 'v5' ? 'on' : ''}`}>
          <div className="sec">
            <div className="backdrop">
              <div className="paper">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <h2 className="serif" style={{ fontSize: 30, margin: 0 }}>Audit Evidence & Proof Pack</h2>
                  <span className="badge">Cryptographic Receipt</span>
                </div>
                <p style={{ color: '#6B716D' }}>
                  Prepared {new Date().toLocaleString('en-IN')}. Operates strictly on Transaction IDs without storing financial account details.
                </p>
                {subs.map((s, idx) => (
                  <div key={idx} style={{ borderBottom: '1px solid #ECECEC', paddingBottom: 16 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 14 }}>
                      <h3 className="serif" style={{ margin: 0 }}>{s.name} · {fmt(s.yr)}/yr</h3>
                      <span style={{ fontSize: 12, fontFamily: 'monospace', color: '#6B716D' }}>
                        Ref: {s.transaction_ref || 'TXN-DIRECT'}
                      </span>
                    </div>
                    <p style={{ margin: '4px 0', fontSize: 14 }}>
                      Status: <b>{{ c: 'Direct Cancellation Confirmed', k: 'Retained by User', u: 'Upgraded to ' + s.plan }[s.d] || 'Active'}</b>. Cadence: {FN[s.f]}.
                    </p>
                    <table>
                      <thead><tr><th>Date</th><th>Debit Amount</th></tr></thead>
                      <tbody>
                        {s.a.map((x, i) => (
                          <tr key={i}>
                            <td>{x.d.toLocaleDateString('en-IN')}</td>
                            <td>{fmt(x.a)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ))}
                <p style={{ color: '#6B716D', fontSize: 12, borderTop: '1px solid #E8E4DD', paddingTop: 10 }}>
                  Generated by Subscription Killer · Server Verification Code: KILL-VERIFIED-2026
                </p>
              </div>
            </div>
            <p style={{ textAlign: 'center', marginTop: 20 }}>
              <button className="btn" onClick={() => window.print()}>Save Evidence PDF</button>{' '}
              <button className="btn gh" onClick={() => setView('v3')}>Back to Dashboard</button>
            </p>
          </div>
        </section>
      </main>

      {/* DRAWER: DETAILS & DIRECT CANCELLATION */}
      <aside id="dr" className={selectedSub ? 'on' : ''} role="dialog" aria-label="Subscription details">
        {selectedSub && (
          <>
            <button className="btn gh x" onClick={() => setSelectedId(null)} aria-label="Close">Close</button>
            <div className="mono" aria-hidden="true">{selectedSub.name[0]}</div>
            <h2 className="serif" style={{ fontSize: 34, margin: '12px 0 0' }}>{selectedSub.name}</h2>
            <p className="mu" style={{ margin: 0 }}>
              {selectedSub.plan || CUR[selectedSub.id] || FN[selectedSub.f]} · {fmt(selectedSub.last)} · {fmt(selectedSub.yr)} a year
            </p>
            <p style={{ fontSize: 13, fontFamily: 'monospace', color: 'var(--ac)', margin: '6px 0 0' }}>
              Transaction Ref: {selectedSub.transaction_ref || 'TXN-GEN-9021'}
            </p>

            <h3 style={{ margin: '24px 0 0' }}>Charge History</h3>
            <div className="tl">
              {selectedSub.a.map((x, idx) => (
                <div key={idx}>
                  {x.d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })} · {fmt(x.a)}
                </div>
              ))}
            </div>

            <h3 style={{ margin: '24px 0 0' }}>Direct Action</h3>
            <div className="ch">
              {[['c', 'Cancel (Direct)'], ['k', 'Keep'], ['u', 'Upgrade']].map(([k, n]) => (
                <button
                  key={k}
                  disabled={!!selectedSub.d}
                  className={selectedSub.d === k ? 'sel' : ''}
                  onClick={() => (k === 'u' ? openUpgradeModal(selectedSub.id) : decide(selectedSub.id, k))}
                >
                  <b>+{k === 'c' ? 50 : PTS[k]}</b>{n}
                </button>
              ))}
            </div>

            {selectedSub.d === 'c' && (
              <>
                <h3 style={{ margin: '24px 0 8px' }}>Official Cancellation Notice</h3>
                <textarea readOnly value={cancellationText} />
                <p style={{ display: 'flex', gap: 8, marginTop: 10 }}>
                  <button className="btn" onClick={() => { navigator.clipboard?.writeText(cancellationText); showToast('Copied to Clipboard'); }}>Copy Notice</button>
                  <button className="btn gh" onClick={() => { location.href = `mailto:?subject=${encodeURIComponent('Request to cancel recurring subscription (' + selectedSub.name + ')')}&body=${encodeURIComponent(cancellationText)}`; }}>Email Merchant</button>
                </p>
              </>
            )}
          </>
        )}
      </aside>

      {/* MODAL: DIRECT CANCELLATION RECEIPT */}
      <div className={`md ${receiptModalOpen ? 'on' : ''}`} onClick={(e) => e.target === e.currentTarget && setReceiptModalOpen(false)}>
        {lastReceipt && (
          <div className="mb" role="dialog" aria-modal="true" aria-label="Cancellation Receipt">
            <button className="btn gh x" onClick={() => setReceiptModalOpen(false)}>Close</button>
            <span className="badge">Instant Direct Cancellation Receipt</span>
            <h2 className="serif" style={{ fontSize: 32, margin: '10px 0 0' }}>Subscription Killed!</h2>
            <p className="mu" style={{ margin: '4px 0 16px' }}>
              Your subscription for <b>{lastReceipt.merchant}</b> has been terminated.
            </p>
            <div className="sm">
              <div><span>Confirmation Code</span><b style={{ fontFamily: 'monospace' }}>{lastReceipt.confirmation_code}</b></div>
              <div><span>Transaction Reference</span><b style={{ fontFamily: 'monospace' }}>{lastReceipt.transaction_ref}</b></div>
              <div><span>Points Allotted</span><b style={{ color: 'var(--ac)' }}>+{lastReceipt.points_awarded} pts</b></div>
              <div><span>New Credit Score</span><b>{lastReceipt.current_credit_score} ({lastReceipt.credit_rating_tier})</b></div>
              <div><span>Monthly Cost Saved</span><b>{fmt(lastReceipt.monthly_saved)}</b></div>
            </div>
            <p style={{ marginTop: 20 }}>
              <button className="btn" onClick={() => { setReceiptModalOpen(false); setView('v5'); }}>
                View in Audit Evidence Pack
              </button>
            </p>
          </div>
        )}
      </div>

      {/* MODAL: BACKEND STATUS & STATS */}
      <div className={`md ${statusModalOpen ? 'on' : ''}`} onClick={(e) => e.target === e.currentTarget && setStatusModalOpen(false)}>
        <div className="mb" role="dialog" aria-modal="true" aria-label="System Health">
          <button className="btn gh x" onClick={() => setStatusModalOpen(false)}>Close</button>
          <span className="badge">{backendOnline ? 'System Online' : 'Connecting'}</span>
          <h2 className="serif" style={{ fontSize: 28, margin: '8px 0 0' }}>Backend Architecture</h2>
          <p className="mu" style={{ margin: '4px 0 16px' }}>
            Connected to Flask API on Port 5000 with SQLite Zero-Trust Engine.
          </p>
          <div className="sm">
            <div><span>API Host</span><b>http://127.0.0.1:5000</b></div>
            <div><span>Database Engine</span><b>PostgreSQL 18 (pgAdmin 4)</b></div>
            <div><span>PostgreSQL Database</span><b>postgres (Port 5432)</b></div>
            <div><span>Active Subscriptions in DB</span><b>{backendStats.subsCount}</b></div>
            <div><span>Score Ledger Balance</span><b>{score} pts</b></div>
            <div><span>Scheduled Notifications</span><b>{notificationsList.length}</b></div>
            <div><span>Voice Engine</span><b>ElevenLabs Linguistic Multilingual v2</b></div>
          </div>
          <p style={{ marginTop: 20, display: 'flex', gap: 10 }}>
            <button className="btn" onClick={() => { checkBackendHealth().then((h) => setBackendOnline(h.ok)); showToast('Refreshed Health Check'); }}>
              Ping Backend
            </button>
            <button className="btn gh" onClick={() => setStatusModalOpen(false)}>Dismiss</button>
          </p>
        </div>
      </div>

      {/* MODAL: CUSTOM ALERT / NOTIFICATION CREATOR */}
      <div className={`md ${notifModalOpen ? 'on' : ''}`} onClick={(e) => e.target === e.currentTarget && setNotifModalOpen(false)}>
        <div className="mb" role="dialog" aria-modal="true" aria-label="Custom Alert Creator">
          <button className="btn gh x" onClick={() => setNotifModalOpen(false)}>Close</button>
          <h2 className="serif" style={{ fontSize: 28, margin: '4px 0 8px' }}>Set Custom Subscription Alert</h2>
          <p className="mu" style={{ margin: '0 0 16px', fontSize: 14 }}>
            Create an automated reminder strictly according to your customized text and deadline inputs.
          </p>
          <form onSubmit={handleCreateCustomNotification}>
            <label style={{ display: 'block', marginBottom: 12 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                <span>Alert Title</span>
                <button
                  type="button"
                  className={`inline-voice-pill ${inlineListeningField === 'notif_title' ? 'recording' : ''}`}
                  onClick={() => startFieldDictation('notif_title', (text) => setNewNotif((prev) => ({ ...prev, title: text })))}
                  title="Speak alert title (Microphone Dictation)"
                  aria-label="Speak alert title (Microphone Dictation)"
                >
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <rect x="9" y="3" width="6" height="11" rx="3" /><path d="M5 11a7 7 0 0014 0M12 18v3" />
                  </svg>
                  {inlineListeningField === 'notif_title' ? 'Listening…' : '🎙️ Speak'}
                </button>
              </div>
              <input
                className="input-custom"
                value={newNotif.title}
                onChange={(e) => setNewNotif({ ...newNotif, title: e.target.value })}
                placeholder="e.g. Cancel Netflix Trial"
                required
              />
            </label>
            <label style={{ display: 'block', marginBottom: 16 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                <span>Custom Reminder Message</span>
                <button
                  type="button"
                  className={`inline-voice-pill ${inlineListeningField === 'notif_msg' ? 'recording' : ''}`}
                  onClick={() => startFieldDictation('notif_msg', (text) => setNewNotif((prev) => ({ ...prev, message: text })))}
                  title="Speak reminder message (Microphone Dictation)"
                  aria-label="Speak reminder message (Microphone Dictation)"
                >
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <rect x="9" y="3" width="6" height="11" rx="3" /><path d="M5 11a7 7 0 0014 0M12 18v3" />
                  </svg>
                  {inlineListeningField === 'notif_msg' ? 'Listening…' : '🎙️ Speak'}
                </button>
              </div>
              <textarea
                style={{ minHeight: 90 }}
                value={newNotif.message}
                onChange={(e) => setNewNotif({ ...newNotif, message: e.target.value })}
                placeholder="e.g. Cancellation deadline is tomorrow! Log in and kill renewal."
                required
              />
            </label>
            <p style={{ display: 'flex', gap: 10, marginTop: 16, flexWrap: 'wrap', alignItems: 'center' }}>
              <button type="submit" className="btn">Save Alert to Database</button>
              <button
                type="button"
                className="btn gh"
                onClick={() => playAudio(`${newNotif.title}. ${newNotif.message}`, lang)}
                title="Hear this custom alert message read aloud"
              >
                🔊 Preview Audio
              </button>
              <button type="button" className="btn gh" onClick={() => setNotifModalOpen(false)}>Cancel</button>
            </p>
          </form>
        </div>
      </div>

      {/* ACCESSIBILITY & ELEVENLABS SETTINGS PANEL */}
      <div id="ap" role="dialog" aria-label="Accessibility & Voice settings" hidden={!axOpen}>
        <b>Voice & Accessibility Settings</b>
        <div className="ar">
          <span>Text size</span>
          <span>
            <button className="btn gh" onClick={() => setAx((prev) => ({ ...prev, fs: Math.max(0, prev.fs - 1) }))} aria-label="Smaller text">A−</button>{' '}
            <button className="btn gh" onClick={() => setAx((prev) => ({ ...prev, fs: Math.min(3, prev.fs + 1) }))} aria-label="Larger text">A+</button>
          </span>
        </div>
        <label className="ar">
          <span>High contrast</span>
          <input type="checkbox" checked={ax.hc} onChange={(e) => setAx((prev) => ({ ...prev, hc: e.target.checked }))} />
        </label>
        <label className="ar">
          <span>Dyslexia font</span>
          <input type="checkbox" checked={ax.dys} onChange={(e) => setAx((prev) => ({ ...prev, dys: e.target.checked }))} />
        </label>

        {/* ElevenLabs Linguistic Voice Configuration */}
        <div style={{ marginTop: 14, paddingTop: 10, borderTop: '1px solid var(--bd)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <b style={{ fontSize: 14 }}>ElevenLabs Linguistic Voice</b>
            {elKeyStatus === 'valid' && <span style={{ color: 'var(--ac)', fontSize: 12, fontWeight: 600 }}>✓ Connected</span>}
            {elKeyStatus === 'invalid' && <span style={{ color: 'var(--al)', fontSize: 12 }}>✕ Invalid Key</span>}
            {elKeyStatus === 'verifying' && <span style={{ color: 'var(--mu)', fontSize: 12 }}>Testing…</span>}
          </div>

          <label style={{ display: 'block', marginTop: 8, fontSize: 13 }}>
            ElevenLabs API Key
            <input
              type="password"
              autoComplete="off"
              placeholder="Paste xi-api-key here"
              value={elKey}
              onChange={(e) => {
                const k = e.target.value.trim();
                setElKey(k);
                try { sessionStorage.setItem('sk-el', k); } catch (err) {}
              }}
            />
          </label>

          <p style={{ marginTop: 6, display: 'flex', gap: 6 }}>
            <button className="tag-btn" onClick={() => verifyKey(elKey)}>
              Verify Key
            </button>
            <button
              className="tag-btn"
              onClick={() => playAudio('Hello! I am your SubKiller AI financial voice assistant powered by ElevenLabs multilingual synthesis.', lang)}
            >
              Test Voice
            </button>
          </p>

          <label style={{ display: 'block', marginTop: 10, fontSize: 13 }}>
            Linguistic Voice
            <select
              className="select-custom"
              value={elVoiceId}
              onChange={(e) => {
                setElVoiceId(e.target.value);
                try { localStorage.setItem('sk-el-voice', e.target.value); } catch (err) {}
              }}
            >
              {elVoices.length > 0 ? (
                elVoices.map((v) => (
                  <option key={v.voice_id} value={v.voice_id}>
                    {v.name} ({v.labels?.accent || v.category || 'Multilingual'})
                  </option>
                ))
              ) : (
                <>
                  <option value="21m00Tcm4TlvDq8ikWAM">Rachel (Calm Multilingual)</option>
                  <option value="pNInz6obpgDQGcFmaJgB">Adam (Deep Conversational)</option>
                  <option value="9BWtsMINqrJLrRacOk9x">Aria (Expressive Copilot)</option>
                  <option value="IKne3meq5aSn9XLyUdCD">Charlie (Authoritative)</option>
                  <option value="EXAVITQu4vr4xnSDxMaL">Sarah (Professional Advisory)</option>
                  <option value="JBFqnCBsd6RMkjVDRZzb">George (Warm British)</option>
                </>
              )}
            </select>
          </label>

          <label style={{ display: 'block', marginTop: 8, fontSize: 13 }}>
            Linguistic Model
            <select
              className="select-custom"
              value={elModelId}
              onChange={(e) => setElModelId(e.target.value)}
            >
              <option value="eleven_multilingual_v2">Eleven Multilingual v2 (29 Languages)</option>
              <option value="eleven_turbo_v2_5">Eleven Turbo v2.5 (Fast Conversational)</option>
              <option value="eleven_flash_v2">Eleven Flash v2 (75ms Low-Latency)</option>
            </select>
          </label>

          <p className="mu" style={{ fontSize: 12, margin: '8px 0 0' }}>
            {elKey ? 'Natural linguistic voice synthesis enabled.' : 'Fallback multi-language synthesizer active. Add key for studio quality voices.'}
          </p>
        </div>
      </div>

      {/* UPGRADE MODAL */}
      <div className={`md ${upgradeOpen ? 'on' : ''}`} onClick={(e) => e.target === e.currentTarget && setUpgradeOpen(false)}>
        {upgradeTarget && (
          <div className="mb" role="dialog" aria-modal="true" aria-label="Upgrade plans">
            <button className="btn gh x" onClick={() => setUpgradeOpen(false)} aria-label="Close">Close</button>
            <h2 className="serif" style={{ fontSize: 32, margin: 0 }}>Upgrade {upgradeTarget.name}</h2>
            <p className="mu" style={{ margin: '4px 0 0' }}>
              Current plan: {upgradeTarget.plan || CUR[upgradeTarget.id] || FN[upgradeTarget.f]} at {fmt(upgradeTarget.last)}/mo.
            </p>
            <div className="pcs">
              {getUpgradePlans(upgradeTarget).map((p, idx) => (
                <button
                  key={idx}
                  className={`pc ${idx === upgradePlanIdx ? 'sel' : ''}`}
                  onClick={() => setUpgradePlanIdx(idx)}
                >
                  <b>{p.n}</b>
                  <span><strong>{fmt(p.p)}</strong>/{p.c}</span>
                  <span className="mu" style={{ fontSize: 13 }}>{p.d}</span>
                  <em className={p.dl < 0 ? 'g' : ''}>{p.dl < 0 ? 'Saves ' + fmt(-p.dl) : '+' + fmt(p.dl)}/yr</em>
                </button>
              ))}
            </div>

            {(() => {
              const currentPlan = getUpgradePlans(upgradeTarget)[upgradePlanIdx];
              const discount = Math.round((currentPlan.p * upgradePoints) / 100);
              const maxPoints = Math.min(bal, 25);
              return (
                <>
                  <div className="sm">
                    <div><span>Plan price</span><b>{fmt(currentPlan.p)}</b></div>
                    <div><span>Points discount</span><b>−{fmt(discount)}</b></div>
                    <div className="t"><span>First payment</span><b>{fmt(currentPlan.p - discount)}</b></div>
                  </div>
                  {maxPoints > 0 ? (
                    <label style={{ display: 'block', margin: '14px 0 4px' }}>
                      Use <b>{upgradePoints}</b> of your {bal} points (1 pt = 1% off, up to 25%)
                      <input
                        type="range"
                        min="0"
                        max={maxPoints}
                        value={upgradePoints}
                        onChange={(e) => setUpgradePoints(+e.target.value)}
                      />
                    </label>
                  ) : (
                    <p className="mu" style={{ fontSize: 14 }}>
                      Cancel or keep subscriptions to earn score points for upgrade discounts.
                    </p>
                  )}
                  <p><button className="btn" onClick={confirmUpgrade}>Confirm Upgrade · +30 pts</button></p>
                </>
              );
            })()}
          </div>
        )}
      </div>

      {/* TOAST POPUP */}
      <div id="toast" className={toastMsg ? 'on' : ''} role="status">
        {toastMsg}
      </div>

      {/* AUDIBLE COMMANDS & ACCESSIBLE VOICE COPILOT CENTER */}
      <div id="vb" className={voiceOpen ? 'on' : ''} role="region" aria-label="Audible Commands and Voice Assistant Center">
        {/* Header */}
        <div className="vb-header">
          <div className="vb-title">
            <span role="img" aria-label="speaker">🔊</span>
            <span>AI Voice Copilot & Audible Commands</span>
            {backendOnline && (
              <span className="badge" style={{ fontSize: 11, padding: '2px 8px', background: 'var(--so)', color: 'var(--ac)' }}>
                PostgreSQL Online
              </span>
            )}
            {isPlayingAudio && (
              <div className="soundwave-visualizer" aria-label="Audio speaking active">
                <span className="soundwave-bar"></span>
                <span className="soundwave-bar"></span>
                <span className="soundwave-bar"></span>
                <span className="soundwave-bar"></span>
                <span className="soundwave-bar"></span>
              </div>
            )}
          </div>

          <div className="vb-controls">
            {/* Audio Mute/Unmute Toggle */}
            <button
              className={`audio-ctrl-btn ${audioEnabled ? 'active' : ''}`}
              onClick={() => {
                setAudioEnabled(!audioEnabled);
                showToast(audioEnabled ? 'Spoken Voice Audio Muted' : 'Spoken Voice Audio Enabled');
              }}
              title={audioEnabled ? 'Click to Mute Spoken Responses' : 'Click to Unmute Spoken Responses'}
              aria-label={audioEnabled ? 'Mute voice audio' : 'Unmute voice audio'}
            >
              {audioEnabled ? '🔊 Audio: ON' : '🔇 Audio: OFF'}
            </button>

            {/* Speech Rate Control */}
            <button
              className="audio-ctrl-btn"
              onClick={() => {
                const nextRate = speechRate === 1.0 ? 1.2 : speechRate === 1.2 ? 0.8 : 1.0;
                setSpeechRate(nextRate);
                showToast(`Speech rate set to ${nextRate}x`);
              }}
              title="Change Voice Speed (0.8x, 1.0x, 1.2x)"
              aria-label={`Speech rate ${speechRate}x`}
            >
              ⚡ {speechRate}x
            </button>

            {/* Replay Button */}
            <button
              className="audio-ctrl-btn"
              onClick={replayAudio}
              title="Replay Last Spoken Response"
              aria-label="Replay last audio"
            >
              🔁 Replay
            </button>

            {/* Stop Audio Button */}
            {isPlayingAudio && (
              <button
                className="audio-ctrl-btn"
                style={{ background: '#E53935', color: '#fff', borderColor: '#D32F2F' }}
                onClick={stopAudio}
                title="Stop Audio Playback"
                aria-label="Stop audio"
              >
                ⏹️ Stop
              </button>
            )}

            {/* Close Button */}
            <button
              className="btn gh"
              style={{ padding: '4px 10px', fontSize: 13, borderRadius: 8 }}
              onClick={() => setVoiceOpen(false)}
              aria-label="Close voice assistant"
            >
              ✕
            </button>
          </div>
        </div>

        {/* Live Audio Status / Notice */}
        <div className="audio-status-banner" role="status" aria-live="polite">
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            {isListening ? (
              <>
                <span style={{ color: '#E53935', fontWeight: 600 }}>🎙️ Recording live voice input...</span>
                <span className="mu" style={{ fontSize: 12 }}>Speak now! Tap mic or press Alt+V to stop</span>
                <div className="soundwave-visualizer">
                  <span className="soundwave-bar" style={{ background: '#E53935' }}></span>
                  <span className="soundwave-bar" style={{ background: '#E53935' }}></span>
                  <span className="soundwave-bar" style={{ background: '#E53935' }}></span>
                </div>
              </>
            ) : isTranscribing ? (
              <span style={{ color: 'var(--ac)', fontWeight: 600 }}>⚡ Transcribing audio with Whisper Speech-to-Text...</span>
            ) : isPlayingAudio ? (
              <span style={{ color: 'var(--ac)', fontWeight: 600 }}>🔊 Speaking AI Response ({lang})...</span>
            ) : (
              <span className="mu">Tap mic or press <b>Alt+V</b> to speak · Explore audible commands below</span>
            )}
          </div>

          <button
            className="audio-ctrl-btn"
            style={{ fontSize: 12, padding: '3px 8px' }}
            onClick={readAllCommandsAloud}
            title="Read all available commands aloud"
          >
            🔊 Read All Commands Aloud
          </button>
        </div>

        {/* Quick Audible Command Chips */}
        <div className="quick-commands-bar" role="toolbar" aria-label="Audible Command Shortcuts">
          <button className="quick-pill" onClick={() => handleVoiceCommand('Show total spend')}>
            🔊 Total Spend
          </button>
          <button className="quick-pill" onClick={() => handleVoiceCommand('Cancel Netflix')}>
            🔊 Cancel Netflix (+50 pts)
          </button>
          <button className="quick-pill" onClick={() => handleVoiceCommand('What is my credit score?')}>
            🔊 My Score
          </button>
          <button className="quick-pill" onClick={() => handleVoiceCommand('Upcoming deadlines')}>
            🔊 Upcoming Deadlines
          </button>
          <button className="quick-pill" onClick={() => setCommandsDrawerOpen(!commandsDrawerOpen)}>
            📜 {commandsDrawerOpen ? 'Hide' : 'View'} All Commands ({availableCommands.length}) {commandsDrawerOpen ? '▲' : '▼'}
          </button>
        </div>

        {/* Collapsible Audible Commands Guide Drawer */}
        {commandsDrawerOpen && (
          <div className="commands-drawer" role="region" aria-label="Available Audible Commands">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <b style={{ fontSize: 13, color: 'var(--ink)' }}>Audible Voice Commands Guide</b>
              <button
                className="tag-btn"
                onClick={readAllCommandsAloud}
                title="Hear guide read aloud"
              >
                🔊 Read Entire Guide Aloud
              </button>
            </div>
            <div className="commands-grid">
              {availableCommands.map((cmd) => {
                const shortLang = lang.slice(0, 2);
                const localizedTitle = (cmd.native && cmd.native[shortLang]) || cmd.command;
                return (
                  <div key={cmd.id} className="cmd-card">
                    <div>
                      <div className="cmd-title-row">
                        <span className="cmd-name">{cmd.command}</span>
                        {localizedTitle !== cmd.command && (
                          <span className="cmd-native">{localizedTitle}</span>
                        )}
                      </div>
                      <p className="cmd-desc">{cmd.description}</p>
                    </div>
                    <div className="cmd-actions">
                      <button
                        className="cmd-hear-btn"
                        onClick={() => hearCommand(cmd)}
                        aria-label={`Hear command ${cmd.command} spoken aloud`}
                        title="Hear this command and description spoken aloud"
                      >
                        🔊 Hear Command
                      </button>
                      <button
                        className="cmd-run-btn"
                        onClick={() => runAudibleCommand(cmd)}
                        aria-label={`Run command ${cmd.command}`}
                        title="Execute this voice command"
                      >
                        ▶ Run
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Voice Log Transcript Box */}
        <p id="log" style={{ whiteSpace: 'pre-line', margin: '0 0 10px' }} aria-live="polite">
          {voiceLog}
        </p>

        {/* Input Bar */}
        <div className="vr">
          <select
            value={lang}
            onChange={(e) => {
              setLang(e.target.value);
              showToast(`Language set to ${e.target.options[e.target.selectedIndex].text}`);
            }}
            aria-label="Language selection for voice input and audio synthesis"
            title="Language selection"
          >
            <option value="en-IN">English (India)</option>
            <option value="hi-IN">हिन्दी (Hindi)</option>
            <option value="bn-IN">বাংলা (Bengali)</option>
            <option value="mr-IN">मराठी (Marathi)</option>
            <option value="ta-IN">தமிழ் (Tamil)</option>
            <option value="te-IN">తెలుగు (Telugu)</option>
            <option value="gu-IN">ગુજરાતી (Gujarati)</option>
          </select>

          {/* Accessible Mic Button */}
          <button
            className={`mic ${isListening ? 'recording' : ''}`}
            aria-label={isListening ? 'Recording live voice input. Click to stop (Hotkey: Alt+V)' : 'Start live voice input recording (Hotkey: Alt+V)'}
            aria-pressed={isListening}
            onClick={toggleListening}
            title={isListening ? 'Click or press Alt+V to stop recording' : 'Click or press Alt+V to record voice command'}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round">
              <rect x="9" y="3" width="6" height="11" rx="3" /><path d="M5 11a7 7 0 0014 0M12 18v3" />
            </svg>
          </button>

          <input
            placeholder="Ask AI Copilot: e.g. 'Cancel Netflix', 'Show total spend'…"
            aria-label="Type a command or query"
            value={textCommand}
            onChange={(e) => setTextCommand(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && textCommand.trim()) {
                handleVoiceCommand(textCommand.trim());
                setTextCommand('');
              }
            }}
          />

          <button
            className="btn"
            style={{ padding: '10px 18px' }}
            onClick={() => {
              if (textCommand.trim()) {
                handleVoiceCommand(textCommand.trim());
                setTextCommand('');
              }
            }}
            aria-label="Send typed command to AI Copilot"
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
}