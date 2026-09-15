"""
AI layer for the CodeAlpha Chatbot.

Provider:
    Google Gemini

SDK:
    google-genai

Environment variables:
    GEMINI_API_KEY
    GEMINI_MODEL

Default model:
    gemini-3.5-flash-lite
"""

import os
from typing import Optional

from dotenv import load_dotenv
from google import genai
from google.genai import types


# ============================================================
# Load environment variables
# ============================================================

load_dotenv()


# ============================================================
# Configuration
# ============================================================

PROVIDER = "gemini"

DEFAULT_MODEL = "gemini-3.5-flash-lite"

GEMINI_API_KEY_ENV = "GEMINI_API_KEY"
GEMINI_MODEL_ENV = "GEMINI_MODEL"


# ============================================================
# System prompt
# ============================================================

SYSTEM_PROMPT = """
You are a helpful, friendly, and intelligent AI assistant.

Your job is to help users with:
- General questions
- Programming and coding
- Artificial Intelligence
- Machine Learning
- Data Science
- Web development
- College projects
- Technical concepts
- Everyday questions

Response guidelines:
1. Give accurate and useful answers.
2. Keep answers clear and easy to understand.
3. Use Markdown formatting when useful.
4. Use bullet points for lists.
5. Use code blocks for programming code.
6. Explain technical topics step-by-step when necessary.
7. Do not unnecessarily repeat the user's question.
8. If the user asks for code, provide complete working code whenever possible.
9. If something is unclear, make a reasonable assumption and state it briefly.
10. Be friendly and professional.
"""


# ============================================================
# Global client state
# ============================================================

_client: Optional[genai.Client] = None
_cached_api_key: Optional[str] = None
_active_model: Optional[str] = None


# ============================================================
# Utility functions
# ============================================================

def _clean_value(value):
    """
    Clean an environment variable value.

    Removes:
    - Leading/trailing spaces
    - Accidental surrounding quotes
    """

    if value is None:
        return None

    value = str(value).strip()

    if len(value) >= 2:
        if value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1].strip()

    return value or None


def _get_api_key():
    """Return the Gemini API key from the environment."""

    return _clean_value(
        os.getenv(GEMINI_API_KEY_ENV)
    )


def _get_model():
    """Return the configured Gemini model."""

    model = _clean_value(
        os.getenv(GEMINI_MODEL_ENV)
    )

    return model or DEFAULT_MODEL


# ============================================================
# Configuration debugging
# ============================================================

def resolve_config():
    """
    Resolve the current Gemini configuration.

    Returns:
        provider, model, api_key, error
    """

    api_key = _get_api_key()
    model = _get_model()

    if not api_key:
        return (
            None,
            None,
            None,
            (
                "No Gemini API key configured. "
                "Set GEMINI_API_KEY in your .env file."
            ),
        )

    return (
        PROVIDER,
        model,
        api_key,
        None,
    )


def debug_config():
    """
    Return a safe configuration summary.

    The actual API key is never printed.
    """

    provider, model, api_key, error = resolve_config()

    if error:
        return f"[ai.debug_config] ERROR: {error}"

    if len(api_key) >= 8:
        masked_key = (
            f"{api_key[:4]}..."
            f"{api_key[-4:]}"
        )
    else:
        masked_key = "(hidden)"

    return (
        "[ai.debug_config] "
        f"provider={provider} "
        f"model={model} "
        f"key={masked_key} "
        f"(len={len(api_key)})"
    )


# ============================================================
# Gemini client
# ============================================================

def _get_client():
    """
    Create or reuse the Gemini API client.

    The client is recreated automatically if the API key changes.
    """

    global _client
    global _cached_api_key

    api_key = _get_api_key()

    if not api_key:
        raise RuntimeError(
            "No Gemini API key configured. "
            "Set GEMINI_API_KEY in your .env file."
        )

    if (
        _client is None
        or _cached_api_key != api_key
    ):
        _client = genai.Client(
            api_key=api_key
        )

        _cached_api_key = api_key

    return _client


# ============================================================
# Conversation history
# ============================================================

def _build_conversation(
    user_message: str,
    history: Optional[list] = None,
):
    """
    Build a compact conversation prompt.

    Only recent messages are included to avoid unnecessarily
    large requests.
    """

    conversation = []

    if isinstance(history, list):

        # Keep only the latest 8 messages.
        recent_history = history[-8:]

        for item in recent_history:

            if not isinstance(item, dict):
                continue

            role = item.get("role")
            content = item.get("content")

            if role not in (
                "user",
                "assistant",
            ):
                continue

            if not isinstance(content, str):
                continue

            content = content.strip()

            if not content:
                continue

            # Prevent huge history messages.
            content = content[:1500]

            if role == "user":
                label = "User"
            else:
                label = "Assistant"

            conversation.append(
                f"{label}: {content}"
            )

    # Current user message.
    conversation.append(
        f"User: {user_message[:5000]}"
    )

    conversation.append(
        "Assistant:"
    )

    return "\n".join(conversation)


# ============================================================
# Response extraction
# ============================================================

def _extract_text(response):
    """
    Safely extract generated text from a Gemini response.

    Gemini may return an empty response in cases such as:
    - Safety blocking
    - Empty candidates
    - Unexpected response structure
    """

    if response is None:
        return ""

    # --------------------------------------------------------
    # Normal response.text
    # --------------------------------------------------------

    try:
        text = response.text
    except Exception:
        text = None

    if isinstance(text, str):

        text = text.strip()

        if text:
            return text

    # --------------------------------------------------------
    # Fallback: inspect candidates
    # --------------------------------------------------------

    try:
        candidates = response.candidates
    except Exception:
        candidates = None

    if not candidates:
        return ""

    collected = []

    for candidate in candidates:

        try:
            content = candidate.content
        except Exception:
            content = None

        if not content:
            continue

        try:
            parts = content.parts
        except Exception:
            parts = None

        if not parts:
            continue

        for part in parts:

            try:
                part_text = part.text
            except Exception:
                part_text = None

            if (
                isinstance(part_text, str)
                and part_text.strip()
            ):
                collected.append(
                    part_text.strip()
                )

    return "\n".join(collected).strip()


# ============================================================
# Finish reason
# ============================================================

def _get_finish_reason(response):
    """Safely obtain Gemini's finish reason."""

    try:
        candidates = response.candidates

        if candidates:
            return str(
                candidates[0].finish_reason
            )

    except Exception:
        pass

    return "UNKNOWN"


# ============================================================
# Main AI function
# ============================================================

def get_ai_response(
    user_message: str,
    history: Optional[list] = None,
) -> str:
    """
    Generate an AI response using Google Gemini.

    This function keeps the same interface expected by
    app.py:

        get_ai_response(user_message, history=history)
    """

    global _active_model

    # --------------------------------------------------------
    # Validate input
    # --------------------------------------------------------

    if not isinstance(user_message, str):
        raise ValueError(
            "user_message must be a string."
        )

    user_message = user_message.strip()

    if not user_message:
        return "Please enter a message."

    # --------------------------------------------------------
    # Get Gemini client
    # --------------------------------------------------------

    client = _get_client()

    model = _get_model()

    # --------------------------------------------------------
    # Build conversation
    # --------------------------------------------------------

    conversation = _build_conversation(
        user_message=user_message,
        history=history,
    )

    # --------------------------------------------------------
    # Gemini request
    # --------------------------------------------------------

    try:

        response = client.models.generate_content(
            model=model,
            contents=conversation,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                max_output_tokens=800,
                candidate_count=1,
            ),
        )

        # ----------------------------------------------------
        # Extract response
        # ----------------------------------------------------

        reply = _extract_text(response)

        if reply:

            _active_model = model

            print(
                "[AI] Gemini response successful "
                f"| model={model}"
            )

            return reply

        # ----------------------------------------------------
        # Empty response
        # ----------------------------------------------------

        finish_reason = _get_finish_reason(
            response
        )

        raise RuntimeError(
            "Gemini returned no text content. "
            f"Finish reason: {finish_reason}"
        )

    # --------------------------------------------------------
    # Known runtime errors
    # --------------------------------------------------------

    except RuntimeError:
        raise

    # --------------------------------------------------------
    # API / network / SDK errors
    # --------------------------------------------------------

    except Exception as error:

        error_text = str(error)

        print(
            "[AI ERROR] "
            f"Gemini request failed: {error_text}"
        )

        # ----------------------------------------------------
        # Authentication
        # ----------------------------------------------------

        if (
            "401" in error_text
            or "Unauthorized" in error_text
            or "API key" in error_text
            and "invalid" in error_text.lower()
        ):
            raise RuntimeError(
                "Gemini API authentication failed. "
                "Please check your GEMINI_API_KEY."
            ) from error

        # ----------------------------------------------------
        # Rate limit / quota
        # ----------------------------------------------------

        if (
            "429" in error_text
            or "RESOURCE_EXHAUSTED" in error_text
            or "quota" in error_text.lower()
            or "rate limit" in error_text.lower()
        ):
            raise RuntimeError(
                "Gemini API rate limit or quota exceeded. "
                "Please wait and try again."
            ) from error

        # ----------------------------------------------------
        # Connection problems
        # ----------------------------------------------------

        if (
            "timeout" in error_text.lower()
            or "timed out" in error_text.lower()
            or "connection" in error_text.lower()
        ):
            raise RuntimeError(
                "Unable to connect to the Gemini API. "
                "Please check your internet connection "
                "and try again."
            ) from error

        # ----------------------------------------------------
        # Generic error
        # ----------------------------------------------------

        raise RuntimeError(
            f"Gemini API request failed: {error_text}"
        ) from error


# ============================================================
# Simple health check
# ============================================================

def test_gemini():
    """
    Send a tiny request to verify Gemini connectivity.

    Returns:
        True if Gemini responds successfully.
    """

    try:

        response = get_ai_response(
            "Reply with exactly: Gemini connection successful."
        )

        if response:
            print(
                "[AI TEST] Gemini connection successful."
            )

            return True

    except Exception as error:

        print(
            f"[AI TEST] Gemini connection failed: {error}"
        )

    return False


# ============================================================
# Module test
# ============================================================

if __name__ == "__main__":

    print("=" * 60)
    print("CodeAlpha Chatbot - Gemini AI Test")
    print("=" * 60)

    print(
        debug_config()
    )

    print()

    if test_gemini():
        print(
            "Status: SUCCESS"
        )
    else:
        print(
            "Status: FAILED"
        )