import os
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv

from chatbot.responses import match_faq
from chatbot.ai import get_ai_response
from chatbot.db import save_chat_message, get_chat_history, check_db_health

load_dotenv()

app = Flask(__name__)

MAX_MESSAGE_LENGTH = 500


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/health")
def health():
    db_status = check_db_health()
    return jsonify({
        "status": "ok",
        "database": db_status.get("status", "unknown"),
        "db_details": db_status
    }), 200


@app.route("/api/db-status")
def db_status():
    return jsonify(check_db_health()), 200


@app.route("/api/history")
def history():
    session_id = request.args.get("session_id", "default").strip()
    limit = min(int(request.args.get("limit", 50)), 100)
    messages = get_chat_history(session_id=session_id, limit=limit)
    return jsonify({"session_id": session_id, "messages": messages}), 200


@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    user_message = (data.get("message") or "").strip()
    history = data.get("history")
    session_id = (data.get("session_id") or "default").strip()

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
        save_chat_message(
            user_message=user_message,
            bot_reply=faq_answer,
            source="faq",
            session_id=session_id,
            ip_address=request.remote_addr,
        )
        return jsonify({"reply": faq_answer, "source": "faq"}), 200

    # 2. Fall back to generative AI model
    try:
        ai_answer = get_ai_response(user_message, history=history)
        save_chat_message(
            user_message=user_message,
            bot_reply=ai_answer,
            source="ai",
            session_id=session_id,
            ip_address=request.remote_addr,
        )
        return jsonify({"reply": ai_answer, "source": "ai"}), 200
    except RuntimeError as rerr:
        app.logger.warning(f"AI configuration warning: {rerr}")
        warn_reply = f"⚠️ **AI Backend Notice**: {rerr}"
        save_chat_message(
            user_message=user_message,
            bot_reply=warn_reply,
            source="warning",
            session_id=session_id,
            ip_address=request.remote_addr,
        )
        return jsonify({
            "reply": warn_reply,
            "source": "warning"
        }), 200
    except Exception as e:
        app.logger.error(f"AI backend error: {e}")
        err_reply = "Sorry, I'm having trouble answering right now. Please try again in a moment or ask about tasks, certificates, or guidelines!"
        save_chat_message(
            user_message=user_message,
            bot_reply=err_reply,
            source="error",
            session_id=session_id,
            ip_address=request.remote_addr,
        )
        return jsonify({
            "reply": err_reply,
            "source": "error"
        }), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug)
