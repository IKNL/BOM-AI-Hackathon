# SocialNet — AI-Powered Cancer Information Platform

**Team 7** — Martijn van de Wetering, Bas Gremmen, Kay Smits, Maxim Gehlmann, Gijs Verdonk

---

## Proposed AI Solution

SocialNet is an AI-powered platform that helps cancer patients and information seekers get personalised, reliable answers about cancer. Instead of navigating complex medical websites, users can ask questions in natural language and receive accurate, empathetic responses grounded in trusted Dutch cancer sources.

The core of the solution is a **Retrieval-Augmented Generation (RAG)** pipeline: curated content from [kanker.nl](https://www.kanker.nl) is embedded into a vector database, and when a user asks a question, the most relevant information is retrieved and fed to a large language model (**GPT-OSS-120B** via AWS Bedrock) to generate a grounded answer — complete with source references. This ensures responses are factual and traceable, reducing the risk of AI hallucinations.

For patients, the platform goes further: by creating a disease profile (cancer type, stage, treatments, symptoms), the AI tailors its answers to the individual's situation. Patients can also choose a communication tone — direct, understanding, or empathetic — so the information is delivered in a way that suits their emotional needs. Profiles can be shared with others via deep links, enabling caregivers and family members to ask informed questions too.

The platform supports two user types:

- **Patients** — log in via mock DigiD, create a disease profile, and receive personalised AI responses based on their medical situation and preferred tone.
- **Information seekers** — use the chatbot without authentication to ask general cancer-related questions.

## Expected Impact

- **Improved accessibility** — Patients and their families can get clear, personalised cancer information 24/7 without needing to interpret complex medical literature or wait for a consultation.
- **Reduced information overload** — Instead of browsing dozens of pages, users get a concise, relevant answer with direct links to the source material for further reading.
- **Emotional sensitivity** — The adjustable communication tone acknowledges that cancer patients have different emotional needs; not everyone wants clinical language, and not everyone wants gentle phrasing.
- **Patient empowerment** — Shareable disease profiles enable better conversations with caregivers, family, and healthcare professionals by giving them the right context upfront.
- **Trust through transparency** — Every AI answer includes the kanker.nl sources it was based on, allowing users to verify information themselves.

## Architecture Overview

```
┌──────────────────────┐    ┌──────────────────────┐
│   Flutter Frontend   │    │    Nuxt Web Frontend  │
│   (Mobile / Web)     │    │    (Lightweight SPA)  │
└─────────┬────────────┘    └─────────┬────────────┘
          │  POST /chat, /chat/stream, /tts          │
          └──────────────┬───────────────────────────┘
                         ▼
              ┌─────────────────────┐
              │   FastAPI Backend   │
              │   (Python / uv)     │
              └────────┬────────────┘
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
    ┌───────────┐ ┌──────────┐ ┌──────────┐
    │ ChromaDB  │ │ AWS      │ │ AWS      │
    │ Vector    │ │ Bedrock  │ │ Polly    │
    │ Store     │ │ LLM      │ │ TTS      │
    └───────────┘ └──────────┘ └──────────┘
```

## Technologies

### Backend (Python)

| Technology | Purpose |
|---|---|
| **FastAPI** + **Uvicorn** | Async HTTP server with SSE streaming |
| **AWS Bedrock** | LLM inference (GPT-OSS-120B via Bedrock Marketplace) |
| **LangChain** | LLM orchestration, prompt engineering, RAG pipeline |
| **ChromaDB** | Persistent vector database for document embeddings |
| **AWS Bedrock Titan Embed Text V2** | Embedding model for RAG retrieval |
| **AWS Polly** | Neural text-to-speech (Dutch voice "Laura") |
| **OpenAI Whisper** | Local speech-to-text transcription (Dutch) |
| **uv** | Fast Python package manager |

### Frontend — Flutter (primary)

| Technology | Purpose |
|---|---|
| **Flutter 3.35.1** (via FVM) | Cross-platform app framework |
| **Provider** | State management (ChangeNotifier pattern) |
| **go_router** | Declarative routing with deep link support |
| **SharedPreferences** | Local data persistence |

### Frontend — Nuxt (lightweight web chat)

| Technology | Purpose |
|---|---|
| **Nuxt 3** (Vue 3 + TypeScript) | SPA web chat interface |
| **marked** | Markdown rendering of AI responses |

## RAG Pipeline

The backend uses **Retrieval-Augmented Generation** to provide grounded, source-backed answers:

1. **Indexing** — Pages from kanker.nl are chunked (4,000 chars, 500 overlap) and embedded using **AWS Bedrock Titan Embed Text V2**, then stored in a local **ChromaDB** vector store.
2. **Retrieval** — When a user asks a question, the query is embedded and the top 5 most similar document chunks are retrieved.
3. **Generation** — The retrieved context, along with the user's disease profile (if available) and tone preference, is injected into the system prompt. **GPT-OSS-120B** (via AWS Bedrock) generates the final answer.
4. **Sources** — The original kanker.nl URLs for retrieved chunks are returned alongside the answer.

## Getting Started

### Prerequisites

- **Python 3.10+** and [**uv**](https://docs.astral.sh/uv/) (Python package manager)
- **AWS credentials** with access to Bedrock and Polly
- **FVM** (Flutter Version Manager) — for the Flutter frontend
- **Node.js 18+** — for the Nuxt web frontend

### Backend

```bash
cd backend

# Create a virtual environment and install dependencies
uv venv
uv pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env with your AWS credentials and model ID:
#   AWS_REGION=us-east-1
#   BEDROCK_API_KEY=your-bedrock-marketplace-api-key
#   BEDROCK_MODEL_ID=openai.gpt-oss-120b-1:0

# (Optional) Rebuild the vector store from source data
uv run python build_vectorstore.py

# Start the API server
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`.

### Frontend — Flutter

```bash
cd frontend

# Install dependencies
fvm flutter pub get

# Run on Chrome (recommended for deep linking)
fvm flutter run -d chrome

# Or run on the default connected device
fvm flutter run
```

### Frontend — Nuxt Web

```bash
cd web

# Install dependencies
npm install

# Start development server
npm run dev
```

The web app will be available at `http://localhost:3000`.

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/chat` | Send a message, receive an AI answer + sources |
| `POST` | `/chat/stream` | Streaming response via Server-Sent Events |
| `POST` | `/tts` | Convert text to speech (returns MP3 audio) |

### Example `/chat` request

```json
{
  "message": "Wat zijn de bijwerkingen van chemotherapie?",
  "simplified_explanation": false,
  "tone": "empathisch",
  "profile": {
    "kankersoort": "borstkanker",
    "stadium": "stadium 2",
    "behandelingen": ["chemotherapie"],
    "symptomen": ["vermoeidheid"]
  }
}
```

Response:

```json
{
  "answer": "De meest voorkomende bijwerkingen van chemotherapie zijn...",
  "sources": [
    "https://www.kanker.nl/kankersoorten/borstkanker/behandeling/chemotherapie"
  ]
}
```

## Project Structure

```
├── backend/                 # Python FastAPI backend
│   ├── main.py              # API endpoints
│   ├── llm.py               # LLM integration + prompt engineering
│   ├── vectorstore.py       # ChromaDB RAG retrieval
│   ├── build_vectorstore.py # Vector store indexing script
│   ├── config.py            # Settings & environment variables
│   ├── conversation.py      # Voice conversation loop
│   ├── speech_to_text/      # Whisper transcription
│   ├── text_to_speech/      # AWS Polly synthesis
│   └── data/                # Source data + ChromaDB storage
├── frontend/                # Flutter app
│   └── lib/
│       ├── models/          # Data classes
│       ├── providers/       # State management
│       ├── services/        # Backend connectors
│       ├── screens/         # UI screens
│       └── widgets/         # Reusable components
└── web/                     # Nuxt 3 web chat interface
```
