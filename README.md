# BOSOM AI - Intelligent Virtual Assistant

[![Live Demo](https://img.shields.io/badge/Live_Demo-bosom.onrender.com-blue?style=for-the-badge&logo=render)](https://bosom.onrender.com)
[![Python](https://img.shields.io/badge/Python-3.9%2B-yellow?style=flat&logo=python)](https://www.python.org/)
[![Powered By](https://img.shields.io/badge/AI-Google_Gemini-magenta?style=flat&logo=google)](https://ai.google.dev/)

**BOSOM AI** is a next-generation, voice-activated virtual assistant that bridges the gap between simple chatbots and functional agents. Powered by **Google Gemini (1.5/2.5 Flash)**, it employs an intelligent **"Orchestrator Pattern"** to understand natural language and execute complex tasks—like reading your emails, sending messages, or fetching real-time facts from Wikipedia—all through voice commands.

Uniquely designed with a **Hybrid Voice Engine**, it works seamlessly across **Android, PC (Chrome/Edge), and iOS (iPhone/iPad)** by dynamically switching between real-time streaming and audio blob processing.

---

## 🚀 Key Features

### 🧠 Intelligent Core
* **Agentic Orchestrator:** The AI doesn't just chat; it decides actions. It routes requests to the correct API (Gmail, Wikipedia) or handles them as general conversation.
* **Dual-Model Brain:** Prioritizes **Gemini 2.5 Pro** for complex reasoning and automatically falls back to **Gemini 1.5 Flash** for speed and reliability.

### 🗣️ Hybrid Voice Architecture
* **PC & Android:** Utilizes the Web Speech API for instant, low-latency text streaming.
* **iOS Support:** Automatically detects Apple devices and switches to a dedicated "Audio Recorder" mode to process raw audio via Gemini's multimodal capabilities.

### ⚡ Functional Capabilities
* **Gmail Integration (Headless):** * Read unread emails with summaries.
    * Send emails via voice dictation.
    * **Headless Auth Flow:** Custom-built OAuth 2.0 system allows secure authentication on cloud servers (like Render) without a GUI.
* **Wikipedia Knowledge:** Fetches accurate, real-time summaries for factual queries.
* **Infinite Loop Mode:** Mimics a real phone call by automatically listening again after speaking, enabling hands-free conversation.
* **Smart Quota Saver:** Filters out background noise and manages API rate limits to prevent crashes on the free tier.

---

## 🛠️ Tech Stack

* **Backend:** Python, Flask, Flask-SocketIO (Threading mode)
* **AI Engine:** Google Generative AI (Gemini 2.5)
* **APIs:** Google Gmail API, Wikipedia Library
* **Frontend:** HTML5, JavaScript (Socket.IO client), Tailwind CSS
* **Deployment:** Gunicorn, Render.com

---

## ⚙️ Local Installation & Setup

### 1. Clone the Repository
```bash
git clone [https://github.com/your-username/bosom-ai.git](https://github.com/your-username/bosom-ai.git)
cd bosom-ai
