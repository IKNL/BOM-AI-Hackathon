# Cancer Assistant Web Application

<p align="left">
  <img src="https://img.shields.io/badge/Python-3.8+-blue?logo=python" alt="Python"/>
  <img src="https://img.shields.io/badge/Flask-2.x-lightgrey?logo=flask" alt="Flask"/>
  <img src="https://img.shields.io/badge/Amazon%20Bedrock-LLM-orange?logo=amazonaws" alt="Amazon Bedrock"/>
  <img src="https://img.shields.io/badge/OpenAI%20GPT--OSS-120B-green?logo=openai" alt="OpenAI GPT-OSS"/>
  <img src="https://img.shields.io/badge/RAG-context--injection-critical?logo=databricks" alt="RAG"/>
  <img src="https://img.shields.io/badge/IKNL%20Data-medical-informational?logo=readthedocs" alt="IKNL Data"/>
</p>


## Architecture & LLM Context Injection

**Tech Stack:** Python, Flask, boto3, Amazon Bedrock (OpenAI GPT-OSS 120B), IKNL Markdown Data

  - User questions are analyzed to detect the relevant cancer type.
  - The backend retrieves the most relevant sections from trusted markdown files (IKNL data) for that cancer type.
  - These sections are injected as context into the LLM prompt, ensuring answers are grounded in reliable medical information.

**Diagram:**

User → [Frontend] → [Flask API] → [RAG: Retrieve Context from Markdown] → [LLM (Bedrock)] → [Answer]


## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

## Running the Application

### Option 1: Using the startup script
```bash
./start_backend.sh
```

### Option 2: Manual start
```bash
python3 backend_api.py
```

The backend API will start on `http://localhost:5000`

## Accessing the Frontend

1. Open `homePage.html` in your browser
2. Click on "Patient" card to go to the chatbot
3. Ask questions about cancer types

## How It Works


## API Endpoints

  - Body: `{"question": "your question", "session_id": "optional_session_id"}`
  - Response: `{"answer": "...", "next_topics": [...], "sources": [...], "cancer_type": "..."}`

  - Body: `{"session_id": "session_id"}`


## Features
**Key Features:**
- Automatic cancer type detection from user questions
- Context-aware responses using relevant markdown sections
- Conversation history tracking
- Session management for multi-turn conversations
- Source references from IKNL markdown files

---

## How It Works

1. **User Onboarding:**
   - The backend guides the user through a short onboarding to collect wellbeing, age, gender, answer style, and cancer type.
   - Users can skip onboarding and ask questions directly.
2. **Cancer Type Detection:**
   - The backend uses keyword and fuzzy matching to identify the relevant cancer type from user input.
3. **Context Retrieval:**
   - The system loads the corresponding markdown file for the detected cancer type and splits it into sections.
   - The most relevant sections are selected based on the user’s question.
4. **LLM Prompting:**
   - The selected context is injected into the LLM prompt (Amazon Bedrock, OpenAI GPT-OSS 120B).
   - The LLM generates a JSON response with the answer, suggested next topics, and references.
5. **Session Management:**
   - Each user session tracks context, conversation history, and onboarding status in memory.

---

## API Endpoints

- `POST /backend/onboard` — Start or continue onboarding
  - Body: `{ "message": "string", "session_id": "string (optional)" }`
  - Response: `{ "response": "string", "onboarding_complete": bool, ... }`

- `POST /backend/ask` — Ask a cancer-related question
  - Body: `{ "question": "string", "session_id": "string (optional)" }`
  - Response: `{ "answer": "string", "next_topics": ["string"], "sources": ["string"], "cancer_type": "string" }`

- `POST /backend/reset` — Reset a session
  - Body: `{ "session_id": "string" }`
  - Response: `{ "status": "reset" }`

- `GET /backend/health` — Health check
  - Response: `{ "status": "healthy", "cancer_types_loaded": int }`

---

## Example Usage

**Onboarding:**
```
POST /backend/onboard
{
  "message": "Ik voel me goed",
  "session_id": "abc123"
}
```
Response:
```
{
  "response": "Wat is uw leeftijd en geslacht?",
  "onboarding_complete": false
}
```

**Ask a Question:**
```
POST /backend/ask
{
  "question": "Wat zijn de symptomen van blaaskanker?",
  "session_id": "abc123"
}
```
Response:
```
{
  "answer": "De meest voorkomende klachten bij blaaskanker zijn ...",
  "next_topics": ["Hoe wordt blaaskanker behandeld?", "Wat zijn de risicofactoren?"],
  "sources": ["https://iknl.nl/kanker/blaaskanker"]
}
```

---

## Troubleshooting

- **CORS errors:** Ensure you are running the backend on localhost and accessing the frontend from the correct port.
- **AWS Bedrock errors:** Make sure your AWS credentials are set up and you have access to the OpenAI GPT-OSS 120B model in region `us-east-1`.
- **No answer found:** The LLM will reply with "Ik kan dit niet vinden in de beschikbare informatie." if the answer is not present in the markdown files.
- **Session lost:** If the backend restarts, session data is lost (in-memory only).

---

## Contact & License

This project was built for BrabantHack_26 by Fontys students in collaboration with IKNL and TRACK MED TECH & LIFE SCIENCES.

For questions, contact the project team or see the main README.