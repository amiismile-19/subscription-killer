/**
 * Subscription Killer API Client
 * Seamlessly connects React Frontend to Flask Backend & ElevenLabs linguistic engine
 */

const DIRECT_BACKEND = 'http://127.0.0.1:5000/api';
const API_BASE = (typeof window !== 'undefined' && (window.location.port === '5173' || window.location.port === '5174'))
  ? '/api'
  : DIRECT_BACKEND;

async function request(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  const config = {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers || {})
    }
  };

  try {
    const res = await fetch(url, config);
    const contentType = res.headers.get('content-type') || '';
    if (contentType.includes('application/json')) {
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.error || `Request failed with status ${res.status}`);
      }
      return data;
    }
    if (!res.ok) {
      throw new Error(`Request failed with status ${res.status}`);
    }
    return await res.text();
  } catch (err) {
    if (API_BASE !== DIRECT_BACKEND) {
      try {
        const directUrl = `${DIRECT_BACKEND}${endpoint}`;
        const res = await fetch(directUrl, config);
        const contentType = res.headers.get('content-type') || '';
        if (contentType.includes('application/json')) {
          const data = await res.json();
          if (!res.ok) throw new Error(data.error || `Status ${res.status}`);
          return data;
        }
        if (res.ok) return await res.text();
      } catch (retryErr) {
        // fallback failed, throw original error
      }
    }
    console.warn(`API Error [${endpoint}]:`, err.message);
    throw err;
  }
}

// --------------------------------------------------------------------------
// Subscriptions API
// --------------------------------------------------------------------------

export async function fetchSubscriptions(userId = 1, status = null) {
  const params = new URLSearchParams({ user_id: userId });
  if (status) params.append('status', status);
  return request(`/subscriptions?${params.toString()}`);
}

export async function createSubscription(subData) {
  return request('/subscriptions', {
    method: 'POST',
    body: JSON.stringify(subData)
  });
}

export async function batchSyncSubscriptions(subscriptions, userId = 1) {
  return request('/subscriptions/batch', {
    method: 'POST',
    body: JSON.stringify({ subscriptions, user_id: userId })
  });
}

export async function cancelSubscription(subscriptionId, userId = 1) {
  return request(`/subscriptions/${subscriptionId}/cancel`, {
    method: 'POST',
    body: JSON.stringify({ user_id: userId })
  });
}

export async function cancelByTransaction(transactionRef, userId = 1) {
  return request('/subscriptions/cancel-by-transaction', {
    method: 'POST',
    body: JSON.stringify({ transaction_ref: transactionRef, user_id: userId })
  });
}

export async function upgradeSubscription(subscriptionId, newPlan, newAmount, userId = 1) {
  return request(`/subscriptions/${subscriptionId}/upgrade`, {
    method: 'POST',
    body: JSON.stringify({
      user_id: userId,
      new_plan: newPlan,
      new_amount: newAmount
    })
  });
}

export async function deleteSubscription(subscriptionId, userId = 1) {
  return request(`/subscriptions/${subscriptionId}`, {
    method: 'DELETE',
    body: JSON.stringify({ user_id: userId })
  });
}

// --------------------------------------------------------------------------
// Credit Scores & Ledger API
// --------------------------------------------------------------------------

export async function fetchUserScore(userId = 1) {
  return request(`/score?user_id=${userId}`);
}

export async function fetchScoreHistory(userId = 1) {
  return request(`/score/history?user_id=${userId}`);
}

// --------------------------------------------------------------------------
// Notifications API
// --------------------------------------------------------------------------

export async function fetchNotifications(userId = 1, status = null) {
  const params = new URLSearchParams({ user_id: userId });
  if (status) params.append('status', status);
  return request(`/notifications?${params.toString()}`);
}

export async function createCustomNotification(notifData) {
  return request('/notifications', {
    method: 'POST',
    body: JSON.stringify(notifData)
  });
}

export async function fetchPreferences(userId = 1) {
  return request(`/notification-preferences?user_id=${userId}`);
}

export async function updatePreferences(prefs, userId = 1) {
  return request('/notification-preferences', {
    method: 'PUT',
    body: JSON.stringify({ ...prefs, user_id: userId })
  });
}

// --------------------------------------------------------------------------
// Voice & ElevenLabs Linguistic API
// --------------------------------------------------------------------------

export async function fetchSupportedLanguages() {
  return request('/voice/languages');
}

export async function fetchElevenLabsVoices(apiKey = '') {
  const headers = apiKey ? { 'xi-api-key': apiKey } : {};
  return request('/voice/elevenlabs/voices', { headers });
}

export async function verifyElevenLabsKey(apiKey) {
  return request('/voice/elevenlabs/verify-key', {
    method: 'POST',
    body: JSON.stringify({ api_key: apiKey })
  });
}

export async function synthesizeSpeech(text, options = {}) {
  const {
    language = 'en',
    provider = 'elevenlabs',
    apiKey = '',
    voiceId = '21m00Tcm4TlvDq8ikWAM',
    modelId = 'eleven_multilingual_v2'
  } = options;

  return request('/voice/speak', {
    method: 'POST',
    body: JSON.stringify({
      text,
      language,
      provider,
      api_key: apiKey,
      voice_id: voiceId,
      model_id: modelId
    })
  });
}

export async function voiceAssistantChat(query, options = {}) {
  const {
    language = 'en',
    userId = 1,
    apiKey = '',
    voiceId = '21m00Tcm4TlvDq8ikWAM',
    provider = 'elevenlabs'
  } = options;

  return request('/voice/assistant-chat', {
    method: 'POST',
    body: JSON.stringify({
      query,
      language,
      user_id: userId,
      elevenlabs_api_key: apiKey,
      voice_id: voiceId,
      provider
    })
  });
}

export async function fetchCommands(language = 'en') {
  return request(`/voice/commands?language=${encodeURIComponent(language)}`);
}

export async function readAllCommandsAudio(options = {}) {
  const {
    language = 'en',
    apiKey = '',
    voiceId = '21m00Tcm4TlvDq8ikWAM',
    modelId = 'eleven_multilingual_v2'
  } = options;
  return request('/voice/read-all-commands', {
    method: 'POST',
    body: JSON.stringify({
      language,
      api_key: apiKey,
      voice_id: voiceId,
      model_id: modelId
    })
  });
}

export async function transcribeAudio(audioFileOrBlob, language = 'auto') {
  const formData = new FormData();
  const filename = (audioFileOrBlob && audioFileOrBlob.name) || 'recording.wav';
  formData.append('audio', audioFileOrBlob, filename);
  formData.append('language', language);

  const urls = [
    `${API_BASE}/voice/transcribe`,
    'http://127.0.0.1:5000/api/voice/transcribe'
  ];

  let lastError = null;
  for (const url of urls) {
    try {
      const res = await fetch(url, {
        method: 'POST',
        body: formData
      });
      if (res.ok) {
        return await res.json();
      }
      const data = await res.json().catch(() => ({}));
      lastError = new Error(data.error || `HTTP ${res.status}`);
    } catch (err) {
      lastError = err;
    }
  }
  throw lastError || new Error('Audio transcription failed');
}

// --------------------------------------------------------------------------
// System Status & DB Verification
// --------------------------------------------------------------------------

export async function checkBackendHealth() {
  const endpoints = [
    '/api/health',
    'http://127.0.0.1:5000/api/health',
    '/health',
    'http://127.0.0.1:5000/health'
  ];

  for (const url of endpoints) {
    try {
      const res = await fetch(url, { signal: AbortSignal.timeout(2000) });
      if (res.ok) {
        const data = await res.json().catch(() => null);
        if (data && (data.ok || data.status === 'healthy')) {
          return { ok: true, data };
        }
      }
    } catch (_) {
      // try next endpoint
    }
  }
  return { ok: false };
}
