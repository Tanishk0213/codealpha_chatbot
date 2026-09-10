import os
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv

from chatbot.responses import match_faq
from chatbot.ai import get_ai_response

load_dotenv()

app = Flask(__name__)

MAX_MESSAGE_LENGTH = 500


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/health")
def health():
    return jsonify({"status": "ok"}), 200


@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    user_message = (data.get("message") or "").strip()
    history = data.get("history")

    if not user_message:
        return jsonify({"error": "message field is required"}), 400

    if len(user_message) > MAX_MESSAGE_LENGTH:
        return jsonify({"error": f"message too long (max {MAX_MESSAGE_LENGTH} chars)"}), 400

    # Sanitize history to be a list if provided
    if not isinstance(history, list):
        history = None

    # 1. Try FAQ / pattern matching first (fast, free, deterministic)
    faq_answer = match_faq(user_message)
    if faq_answer:
        return jsonify({"reply": faq_answer, "source": "faq"}), 200

    # 2. Fall back to generative AI model
    try:
        ai_answer = get_ai_response(user_message, history=history)
        return jsonify({"reply": ai_answer, "source": "ai"}), 200
    except RuntimeError as rerr:
        app.logger.warning(f"AI configuration warning: {rerr}")
        return jsonify({
            "reply": "⚠️ **AI Fallback Unavailable**: OPENROUTER_API_KEY is not set or invalid. Please add your key to `.env` to enable generative AI.",
            "source": "warning"
        }), 200
    except Exception as e:
        app.logger.error(f"AI backend error: {e}")
        return jsonify({
            "reply": "Sorry, I'm having trouble answering right now. Please try again in a moment or ask about tasks, certificates, or guidelines!",
            "source": "error"
        }), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug)
