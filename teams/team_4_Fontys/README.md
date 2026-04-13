
# IKNL Cancer Assistant – BrabantHack_26

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.8+-blue?logo=python" alt="Python"/>
  <img src="https://img.shields.io/badge/Flask-2.x-lightgrey?logo=flask" alt="Flask"/>
  <img src="https://img.shields.io/badge/Amazon%20Bedrock-LLM-orange?logo=amazonaws" alt="Amazon Bedrock"/>
  <img src="https://img.shields.io/badge/OpenAI%20GPT--OSS-120B-green?logo=openai" alt="OpenAI GPT-OSS"/>
  <img src="https://img.shields.io/badge/HTML%2FCSS-frontend-yellow?logo=html5" alt="HTML/CSS"/>
  <img src="https://img.shields.io/badge/IKNL%20Data-medical-informational?logo=readthedocs" alt="IKNL Data"/>
</p>

## Demo Video

[BrabantHack_2026_MedTech_Fontys.mp4](BrabantHack_2026_MedTech_Fontys.mp4)

<p align="center">
  <img src="https://rewin.nl/wp-content/uploads/2026/02/BrabantHack-logo.png" alt="BrabantHack Logo" width="260"/>
</p>

---

**BrabantHack_26 – HTC Eindhoven, Friday 10th April, 2026**  
*Built in 1 day by a group of 4 Fontys students:*

**Beatrice Marro, Pedro Vicq, Thomas Brauns, Ouassim El Kadiaoui**  
Mentor: **Iman Mossavat**

In collaboration with **TRACK MED TECH & LIFE SCIENCES**

<p align="center">
  <img src="https://iknl.nl/getmedia/151a9540-e433-489d-a18e-a612121d2013/iknl_logo_uk_rgb_tekst-rechts_300dpi.png" alt="IKNL Logo" width="320"/>
</p>

---

## AI for Smarter Access to Cancer Information

People increasingly turn to general AI systems for cancer information because they are quick and easy to use, but the results are not always reliable. At the same time, trusted cancer knowledge is spread across different platforms, which makes it harder for patients, professionals, and policymakers to find accurate and consistent information when they need it.

### Challenge

In this track, you’ll explore how AI can connect and unlock trusted knowledge sources: **How can we make reliable cancer information faster and smarter to access by using AI to connect different sources of knowledge?**

---


## Overview
This is a small hackathon project that provides a cancer information assistant using a simple web frontend and a Python backend powered by an LLM. The project uses trusted medical sources (IKNL) and supports question answering about 70+ cancer types.

---

# Backend Details

- See the [Backend README](BACKEND_README.md) for API endpoints, setup, and usage details.

---

## Technical Overview

- **Frontend**: Static HTML/CSS/JS (no framework), with `homePage.html` as the landing page and `chatbotPage.html` as the chat interface.
- **Backend**: Python Flask API (`backend_api.py`) exposes endpoints for chat and session management.
- **AI Engine**: The backend uses Amazon Bedrock (OpenAI GPT-OSS 120B) via `boto3` to generate answers, with context from trusted markdown files (IKNL cancer info).
- **Data**: 70+ markdown files in `data/markdowns/` provide structured, reliable cancer information.
- **Session**: Simple in-memory session management for multi-turn conversations.

---

## Pre-requisites

- **Python 3.8+**
- **Amazon Bedrock access** (for LLM):
  - You need AWS credentials with access to Bedrock and the OpenAI GPT-OSS 120B model in region `us-east-1`.
  - See `llm_startup.md` for details on model usage and configuration.
- **boto3** and other dependencies (see `requirements.txt`)

---

---

## Project Structure

```
.
├── backend_api.py           # Flask backend API
├── cancer_assistant.py      # LLM-powered cancer assistant logic
├── requirements.txt         # Python dependencies
├── start_backend.sh         # Shell script to start backend
// ...existing code...
├── mapping.md               # Mapping of cancer types to markdown files
├── data/
│   └── markdowns/           # 70+ markdown files (IKNL cancer info)
├── css/
│   ├── chatBotPage.css      # Styles for chatbot page
│   ├── footer.css           # Shared footer styles
│   └── homePage.css         # Styles for home page
├── chatbotPage.html         # Chatbot UI
├── homePage.html            # Landing page
├── images/                  # (Place images here, e.g. logo.png, patient.png)
└── README.md                # (This file)
```

---

## Setup & Usage

### 1. Install Python dependencies
```bash
pip install -r requirements.txt
```

### 2. Start the backend
```bash
./start_backend.sh
# or
python3 backend_api.py
```
The backend runs on http://localhost:5000

### 3. Open the frontend
- Open `homePage.html` in your browser
- Click on "Patient" to access the chatbot
- Ask questions about cancer types, treatments, etc.

---

## Features
- Natural language Q&A about 70+ cancer types
- Trusted medical content (IKNL)
- Simple, modern web UI
- Session management and context-aware answers

---

## Notes
- Place required images (logo, patient, etc.) in the `images/` folder. Example images are provided in the `webpage/images/` directory.
// ...existing code...
- All backend logic is in Python; no database is required.

---

## Credits
- Medical content: IKNL (Integraal Kankercentrum Nederland)
- Hackathon team
- BrabantHack_26, TRACK MED TECH & LIFE SCIENCES
