# 🔍 Subscription Killer
### Take control of your recurring payments.

**An intelligent, multilingual subscription management assistant that helps users detect recurring payments, track renewals, avoid unwanted charges, and manage subscriptions from one place.**

---

## 🚨 Problem Statement

In today's digital world, users subscribe to multiple streaming platforms, productivity tools, fitness applications, and other online services. Over time, they often forget about recurring payments, miss cancellation deadlines, and pay for services they no longer use.

Managing subscriptions across multiple platforms is time-consuming, and language or accessibility barriers can make the process even more difficult.

**Subscription Killer aims to make subscription management simpler, smarter, and more accessible.**

## 💡 Our Solution

Subscription Killer provides a centralized interface where users can upload transaction records, identify potential recurring payments, monitor renewal dates, configure personalized reminders, and access guided cancellation workflows.

With multilingual voice interaction and automated document extraction, the platform aims to make subscription management accessible even to users who prefer speaking over typing.

## ✨ Key Features

- **📄 Smart Transaction Detection** — Extract transaction details from uploaded CSV files, PDFs, and screenshots using document parsing and OCR.
- **🔁 Recurring Payment Identification** — Analyze transaction history to identify potential subscriptions and recurring payment patterns.
- **🛑 Cancellation Assistance** — Help users navigate cancellation workflows and track cancellation requests. Direct cancellation depends on supported payment-provider integrations.
- **🔔 Personalized Notifications** — Configure reminder preferences and deadlines according to individual needs.
- **🎙️ Multilingual Voice Interface** — Use speech recognition and language services to support voice-based interaction.
- **🌐 Language Accessibility** — Designed to support English, Hindi, Marathi, Tamil, Telugu, Bengali, and Gujarati.
- **🎮 Subscription Health Score** — Gamify responsible subscription management with points for actions such as reviewing renewals and completing verified cancellations.
- **🗓️ Renewal and Deadline Tracking** — Keep upcoming renewal dates and user-defined cancellation deadlines visible in one place.

## 🔄 How It Works

1. **Upload** — The user uploads a transaction screenshot, PDF, or CSV file.
2. **Extract** — The system extracts candidate transaction details using parsing and OCR.
3. **Review** — The user verifies the merchant, amount, date, and transaction reference.
4. **Detect** — The system analyzes transaction history to identify possible recurring payments.
5. **Track** — Confirmed subscriptions are stored and displayed with renewal dates and deadlines.
6. **Remind** — Personalized reminders help users review subscriptions before renewal.
7. **Manage** — The user follows a supported cancellation workflow and records the outcome.
8. **Earn Points** — The application awards Subscription Health Score points for eligible, verified actions.

## 🧰 Technology Stack

| Component | Technology |
|---|---|
| Frontend | React.js, Node.js tooling |
| Backend | Python, FastAPI |
| Database | PostgreSQL |
| Speech Recognition | OpenAI Whisper |
| Indian Language Services | Bhashini APIs, where available |
| Document Processing | Python, Pandas |
| PDF Extraction | PyMuPDF |
| Image Text Extraction | Tesseract OCR |
| API Communication | REST APIs |
| Version Control | Git and GitHub |

## 🏗️ System Architecture

```text
             USER
              |
              v
       React Web Interface
              |
       Upload / Voice Input
              |
              v
        FastAPI Backend
              |
       +------+------+
       |             |
       v             v
  File Extraction  Voice Processing
  CSV / PDF / OCR  Whisper / Bhashini
       |             |
       +------+------+
              |
              v
    Transaction Analysis
              |
              v
        PostgreSQL
              |
              v
  Subscriptions / Reminders /
  Health Score / Cancellation
         Request Tracking
```

## 🗂️ Planned Repository Structure

```text
subscription-killer/
├── frontend/                  # React web application
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI entry point
│   │   ├── voice_processor.py  # Voice intent processing
│   │   └── transaction_extractor.py
│   ├── requirements.txt
│   └── .env.example
├── database/
│   └── schema.sql             # PostgreSQL database schema
├── tests/
├── .gitignore
└── README.md
```

## 🚀 Getting Started

### Prerequisites

Install the following before running the application:

- Node.js and npm
- Python 3.11 or later
- PostgreSQL
- Git
- Tesseract OCR, if image OCR is enabled

### 1. Clone the Repository

```bash
git clone https://github.com/amiismile-19/subscription-killer.git
cd subscription-killer
```

### 2. Configure PostgreSQL

Create a database named `subscription_killer`.

```sql
CREATE DATABASE subscription_killer;
```

Run the project's database schema against this database using pgAdmin or `psql`.

### 3. Start the Backend

```bash
cd backend
python -m venv .venv
```

Activate the environment.

**Windows:**

```powershell
.venv\Scripts\Activate.ps1
```

**macOS/Linux:**

```bash
source .venv/bin/activate
```

Install dependencies and configure the environment:

```bash
pip install -r requirements.txt
```

Create a local `.env` file using `.env.example` as a template. Configure your PostgreSQL connection string and any required service credentials.

Start FastAPI:

```bash
uvicorn app.main:app --reload
```

API documentation: `http://127.0.0.1:8000/docs`

### 4. Start the Frontend

Open another terminal:

```bash
cd frontend
npm install
npm run dev
```

Open the local address printed by Vite in your browser.

> These instructions assume the repository contains the corresponding application files and configuration templates. Optional services such as Whisper, Bhashini, and OCR must be configured before their features can be used.

## 🔐 Privacy and Security

- Never request bank passwords, UPI PINs, OTPs, or card security codes.
- Store API keys and database credentials in environment variables, not in GitHub.
- Ask users to review extracted transaction data before saving it.
- Restrict access to user-specific subscription records.
- Avoid storing full financial documents longer than necessary.
- Use secure, authorized integrations for cancellation workflows.

## ⚠️ Important Limitations

- OCR and transaction extraction may produce inaccurate results; user verification is necessary.
- Recurring-payment detection identifies potential patterns and should not automatically assume every repeated payment is a subscription.
- A transaction ID alone does not authorize cancellation of an AutoPay mandate.
- Direct cancellation requires an appropriate provider integration or a supported official cancellation process.
- The Subscription Health Score is an application-specific gamification metric, **not a CIBIL score or official credit score**.
- Whisper and Bhashini integrations require implementation and configuration before they can be considered operational.

## 🎯 Future Enhancements

- Automated recurring-payment detection using historical transaction patterns.
- Provider-specific cancellation integrations.
- Real-time notification scheduling.
- Text-to-speech responses in supported Indian languages.
- Subscription spending analytics and monthly savings reports.
- Secure authentication and multi-user access.
- Deployment to a cloud platform.

## 🌟 Project Vision

Our vision is to give users greater visibility and control over recurring payments through intelligent detection, timely reminders, accessible voice interaction, and simpler subscription management.

**Less subscription confusion. More financial awareness. Greater user control.**

---

### Built for a Hackathon 🚀

*Subscription Killer — bringing recurring payments into focus.*
