"""
MongoDB Cloud Database layer for CodeAlpha Chatbot.
Connects to MongoDB Atlas to persist conversations and chat history.
"""

import os
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

_mongo_client = None
_db = None
_collection = None


def get_db():
    """
    Returns the MongoDB collection for storing chat messages.
    Lazily connects to MongoDB Atlas with sensible timeouts.
    """
    global _mongo_client, _db, _collection

    if _collection is not None:
        return _collection

    mongo_uri = os.environ.get("MONGODB_URI", "").strip()
    if not mongo_uri:
        logger.warning("MONGODB_URI is not set; chat history will not be persisted.")
        return None

    # Strip literal angle brackets if the user pasted <password> by mistake
    # e.g. senthil783957_db_user:<barathoo5>@... -> senthil783957_db_user:barathoo5@...
    import re
    cleaned_uri = re.sub(r':<([^>]+)>@', r':\1@', mongo_uri)

    db_name = os.environ.get("MONGODB_DB", "codealpha_chatbot").strip() or "codealpha_chatbot"
    collection_name = os.environ.get("MONGODB_COLLECTION", "chatbot").strip() or "chatbot"

    try:
        from pymongo import MongoClient
        from pymongo.errors import PyMongoError

        _mongo_client = MongoClient(
            cleaned_uri,
            serverSelectionTimeoutMS=4000,
            connectTimeoutMS=4000,
            socketTimeoutMS=5000,
        )
        _db = _mongo_client[db_name]
        _collection = _db[collection_name]
        logger.info(f"Connected to MongoDB Atlas: db='{db_name}', collection='{collection_name}'")
        return _collection
    except Exception as e:
        logger.error(f"Failed to initialize MongoDB connection: {e}")
        _collection = None
        return None


def check_db_health() -> Dict[str, Any]:
    """
    Performs a ping command to verify connection to MongoDB Atlas.
    """
    try:
        coll = get_db()
        if coll is None:
            return {"status": "disabled", "message": "MONGODB_URI not configured"}
        
        # Ping the server
        _mongo_client.admin.command("ping")
        total_count = coll.count_documents({})
        return {
            "status": "connected",
            "db": os.environ.get("MONGODB_DB", "codealpha_chatbot"),
            "collection": os.environ.get("MONGODB_COLLECTION", "chatbot"),
            "total_messages": total_count,
        }
    except Exception as e:
        logger.warning(f"MongoDB health ping failed: {e}")
        return {"status": "disconnected", "error": str(e)}


def save_chat_message(
    user_message: str,
    bot_reply: str,
    source: str,
    session_id: Optional[str] = None,
    model: Optional[str] = None,
    ip_address: Optional[str] = None,
    extra_meta: Optional[Dict[str, Any]] = None,
) -> bool:
    """
    Saves a conversation turn to MongoDB Atlas.
    Fails safely without raising exceptions to protect the main chat response.
    """
    try:
        coll = get_db()
        if coll is None:
            return False

        now = datetime.now(timezone.utc)
        doc = {
            "session_id": session_id or "default",
            "user_message": user_message,
            "bot_reply": bot_reply,
            "source": source,
            "model": model,
            "ip_address": ip_address,
            "created_at": now.isoformat(),
            "timestamp": now,
        }
        if extra_meta and isinstance(extra_meta, dict):
            doc["meta"] = extra_meta

        coll.insert_one(doc)
        return True
    except Exception as e:
        logger.error(f"Failed to persist chat message to MongoDB: {e}")
        return False


def get_chat_history(session_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """
    Retrieves recent chat history for a session from MongoDB.
    """
    try:
        coll = get_db()
        if coll is None:
            return []

        cursor = coll.find(
            {"session_id": session_id},
            {"_id": 0, "session_id": 1, "user_message": 1, "bot_reply": 1, "source": 1, "created_at": 1}
        ).sort("timestamp", 1).limit(limit)

        return list(cursor)
    except Exception as e:
        logger.error(f"Failed to fetch history from MongoDB: {e}")
        return []
