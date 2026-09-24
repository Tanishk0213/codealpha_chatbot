# AI Assistant

A dual-engine AI conversational assistant. It merges an instant pattern-matching FAQ engine for zero-cost answers with an OpenRouter-powered generative AI fallback, wrapped in a modern, responsive web UI.

---

## ✨ Features

### 🎨 Modern UI / UX
- **Dark & Light Mode:** Seamless toggle with user preference saved in `localStorage`.
- **Rich Markdown Formatting:** Clean rendering of bold text, bullet points, links, and formatted code blocks using `marked.js` + `DOMPurify`.
- **Dynamic 3-Dot Typing Indicator:** Smooth CSS bouncing animation while waiting for responses.
- **Quick Suggestion Chips:** One-click prompt pills for common questions.
- **Speech-to-Text Voice Input:** Dictate queries directly via the Web Speech API with real-time mic animation.
- **Conversation Actions:**
  - **Copy Message:** 1-click clipboard copy on every message bubble.
  - **Export Chat:** Download the full conversation transcript as a `.txt` file.
  - **Clear Chat:** Reset conversation history with a fresh hero welcome state.
- **Live Status Indicator:** Real-time pinging to `/health` showing server connectivity with pulse animations.
- **Mobile Responsive:** Works seamlessly on mobile devices, tablets, and desktop displays.

### 🧠 Dual-Engine Architecture & Context Memory
- **Layer 1: Instant FAQ Engine (`chatbot/responses.py`):** High-speed regex matching for instant, deterministic, free answers to common questions.
- **Layer 2: Generative AI Fallback (`chatbot/ai.py`):** OpenRouter OpenAI-compatible LLM completion (Llama 3.1, Gemma 2, Mistral, Qwen) for open-ended queries.
- **Multi-Turn Context Memory:** Retains recent conversation turns (`history`) so users can ask contextual follow-up questions.
- **Automatic Model Fallback:** Failover across free models if the primary model is busy or rate-limited.

---

## 🏛️ Architecture

```
User Input (Text / Voice)
          │
          ▼
Web UI (Markdown Renderer)
          │
          ▼  POST /chat { message, history }
Flask Backend
          │
    ┌─────┴─────────────────────────┐
    ▼                               ▼
FAQ Pattern Matcher           OpenRouter Generative AI
(Deterministic, Free)         (Multi-Turn Contextual LLM)
    │                               │
    └──────────────┬────────────────┘
                   ▼
       JSON Response + Source Tag
    (⚡ Instant FAQ  or  🤖 AI)
```

---

## 📁 Project Structure

```
.
├── app.py                 # Flask server with /chat, /health, / routes
├── test_app.py            # Automated unit test suite
├── requirements.txt       # Python dependencies
├── Dockerfile             # Production containerization
├── .env.example           # Environment variables template
├── .gitignore
├── templates/
│   └── index.html         # Chat application UI
├── static/
│   ├── style.css          # Theme & design system stylesheet
│   └── script.js          # Client logic (memory, voice input, markdown, theme)
├── chatbot/
│   ├── __init__.py
│   ├── responses.py       # FAQ regex knowledge base
│   ├── ai.py              # Multi-provider generative AI (Groq, OpenRouter, Mistral, Grok)
│   └── db.py              # MongoDB Atlas Cloud Database manager
├── diagnose.py            # Complete AI & MongoDB Atlas diagnostics tool
└── README.md
```

---

## 🚀 Local Setup

1. **Clone and navigate to repository:**
   ```bash
   git clone <your-repo-url>
   cd CodeAlpha_Chatbot
   ```

2. **Set up virtual environment (optional):**
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On Linux/macOS:
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment:**
   ```bash
   copy .env.example .env     # Windows
   # or: cp .env.example .env  # Linux/macOS
   ```
   Add your OpenRouter API key in `.env` (get one at https://openrouter.ai/keys):
   ```env
   OPENROUTER_API_KEY=your_key_here
   OPENROUTER_MODEL=meta-llama/llama-3.1-8b-instruct:free
   PORT=5000
   ```

5. **Run the application:**
   ```bash
   python app.py
   ```
   Visit `http://localhost:5000` in your web browser.

---

## 🧪 Running Tests

```bash
python test_app.py
```

---

## 📡 API Reference

### `POST /chat`
Sends a message to the chatbot.

**Request Body:**
```json
{
  "message": "What can you help me with?",
  "history": [
    { "role": "user", "content": "Hello" },
    { "role": "assistant", "content": "Welcome to AI Assistant!" }
  ]
}
```

**Response Body:**
```json
{
  "reply": "💡 **What I can help with** ...",
  "source": "faq"
}
```
*Note: `source` can be `"faq"`, `"ai"`, or `"warning"`.*

### `GET /health`
Health check route used for container orchestrators and status pings.
```json
{ "status": "ok" }
```

---

## 🐳 Docker Deployment

```bash
# Build image
docker build -t ai-chatbot .

# Run container
docker run -p 8080:8080 --env-file .env ai-chatbot
```

---

## ☁️ Deploy to Google Cloud Run

```bash
# 1. Authenticate & set project
gcloud auth login
gcloud config set project YOUR_PROJECT_ID

# 2. Build and push container via Cloud Build
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/ai-chatbot

# 3. Deploy to Cloud Run
gcloud run deploy ai-chatbot \
  --image gcr.io/YOUR_PROJECT_ID/ai-chatbot \
  --platform managed \
  --region asia-south1 \
  --allow-unauthenticated \
  --set-env-vars OPENROUTER_API_KEY=your_openrouter_api_key_here
```
"# codealpha_chatbot" 
