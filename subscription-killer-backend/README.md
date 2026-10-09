# Subscription Killer — runnable Flask backend

A hackathon-ready starter backend for transaction-reference subscription tracking,
cancellation request workflows, deadline reminders, in-app notifications, a gamified
subscription responsibility score, and optional speech integrations.

## Important behavior and limitations

- The default `APP_MODE=demo` records cancellation requests but does **not** claim
  the merchant actually cancelled the subscription.
- Real direct cancellation requires each merchant's authorized API or a supported
  cancellation flow. A transaction ID is a reference, not proof of ownership or
  cancellation authorization.
- The score is a gamified platform score, **not an official credit score**.
- Reminder dispatch is in-app/demo only. Email/SMS/push delivery needs a provider.
- The Whisper endpoint is optional and requires `openai-whisper` plus FFmpeg.
- BHASHINI API request formats depend on the selected service/pipeline. The adapter
  intentionally raises NotImplementedError until you wire the current official schema.

## 1. Install

Python 3.10+ recommended.

### Windows (PowerShell)

```powershell
py -m venv .venv
.venv\\Scripts\\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python app.py
```

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python app.py
```

Server: http://127.0.0.1:5000  
Health: http://127.0.0.1:5000/health

The database is created automatically. A demo user is seeded as `user_id=1`.

## 2. Quick API test

### Add a subscription

```bash
curl -X POST http://127.0.0.1:5000/api/subscriptions \\
  -H "Content-Type: application/json" \\
  -d '{
    "user_id": 1,
    "transaction_ref": "TXN-DEMO-001",
    "merchant": "MusicBox",
    "amount": 199,
    "currency": "INR",
    "billing_frequency": "monthly",
    "renewal_date": "2026-12-15",
    "cancellation_deadline": "2026-12-14"
  }'
```

### List subscriptions

```bash
curl "http://127.0.0.1:5000/api/subscriptions?user_id=1"
```

### Request cancellation (demo)

```bash
curl -X POST http://127.0.0.1:5000/api/subscriptions/1/cancel
```

Expected: HTTP 202 with `subscription_status: cancellation_requested`.
This means the request was recorded; it is not merchant-confirmed cancellation.

### Check deadline

```bash
curl "http://127.0.0.1:5000/api/subscriptions/1/deadline"
```

### Change notification preferences

```bash
curl -X PUT http://127.0.0.1:5000/api/notification-preferences \\
  -H "Content-Type: application/json" \\
  -d '{"user_id":1,"in_app_enabled":true,"price_alerts":true,"reminder_days":[14,7,2,1]}'
```

### List notifications

```bash
curl "http://127.0.0.1:5000/api/notifications?user_id=1"
```

### Read score and history

```bash
curl "http://127.0.0.1:5000/api/score?user_id=1"
curl "http://127.0.0.1:5000/api/score/history?user_id=1"
```

### Voice endpoints

Transcription expects multipart upload field `audio`:

```bash
curl -X POST http://127.0.0.1:5000/api/voice/transcribe -F "audio=@sample.wav"
```

Text-to-speech endpoint:

```bash
curl -X POST http://127.0.0.1:5000/api/voice/speak \\
  -H "Content-Type: application/json" \\
  -d '{"text":"Your cancellation request has been recorded.","language":"hi"}'
```

The voice endpoints return HTTP 501 with setup instructions until the optional integration is configured.

## 3. Endpoint list

- `GET /`
- `GET /health`
- `POST /api/subscriptions`
- `GET /api/subscriptions?user_id=1`
- `GET /api/subscriptions/<id>?user_id=1`
- `POST /api/subscriptions/<id>/cancel`
- `GET /api/subscriptions/<id>/deadline`
- `GET /api/notifications?user_id=1`
- `GET /api/notification-preferences?user_id=1`
- `PUT /api/notification-preferences`
- `GET /api/score?user_id=1`
- `GET /api/score/history?user_id=1`
- `POST /api/voice/transcribe`
- `POST /api/voice/speak`

## 4. Before production

Add real authentication and authorization; do not trust a user ID supplied by a client.
Add CSRF protection if using cookie sessions, rate limiting, input size limits, secure
secrets, database migrations, retention policies, tests, and an actual delivery provider.
Configure and verify each merchant integration before marking a subscription cancelled.
