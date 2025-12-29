# BOSOM AI - Intelligent Virtual Assistant

BOSOM AI is a cross-platform, voice-activated virtual assistant powered by **Google Gemini**. It uses an intelligent "Orchestrator" pattern to understand natural language and execute complex tasks like reading emails, sending messages, and fetching real-time information from Wikipedia.

Built with **Flask**, **SocketIO**, and **Google Generative AI**, it features a unique hybrid architecture that supports **Android, PC, and iOS** devices seamlessly.

## 🚀 Key Features

* **🧠 Advanced NLP Core:** Powered by **Gemini 1.5/2.5 Flash**, enabling natural, context-aware conversations.
* **🗣️ Hybrid Voice Engine:**
    * **PC/Android:** Uses Web Speech API for instant, real-time streaming.
    * **iOS (iPhone/iPad):** Uses a fallback Audio Blob recorder to ensure full compatibility with Apple devices.
* **🤖 Agentic Orchestrator:** The AI intelligently decides whether to:
    * Answer directly (General Chat).
    * Fetch external data (`ACTION: WIKIPEDIA`).
    * Perform actions (`ACTION: CHECK_EMAILS`, `ACTION: SEND_EMAIL`).
* **📧 Gmail Integration (Headless):** Full support for reading unread emails and sending new ones via voice. Includes a custom **"Headless OAuth 2.0"** flow for easy authentication on cloud servers (like Render) without a GUI.
* **🔄 Continuous Conversation:** "Infinite Loop" mode automatically restarts the microphone after the AI speaks, mimicking a real phone call.
* **🛡️ Quota Saver:** Smart noise filtering and rate-limit handling to optimize API usage on the free tier.

---

## 🛠️ Tech Stack

* **Backend:** Python, Flask, Flask-SocketIO
* **AI Model:** Google Gemini (Generative AI)
* **APIs:** Gmail API (Google Workspace), Wikipedia Library
* **Frontend:** HTML5, JavaScript, Tailwind CSS
* **Deployment:** Gunicorn (Production ready for Render/Heroku)

---

## ⚙️ Installation & Setup

### 1. Clone the Repository
```bash
git clone [https://github.com/your-username/bosom-ai.git](https://github.com/your-username/bosom-ai.git)
cd bosom-ai
