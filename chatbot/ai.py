"""
Generative AI layer. Used when the FAQ/pattern layer in responses.py
doesn't match the user's input.

Uses OpenRouter's OpenAI-compatible chat completions API, so any model
available on OpenRouter (Llama, Mistral, Gemini, GPT, etc.) can be swapped
in via the OPENROUTER_MODEL env var without touching this code.
"""

import os
from openai import OpenAI

_client = None

SYSTEM_PROMPT = (
    "You are the official AI Assistant for CodeAlpha's Cloud Computing Internship. "
    "You provide clear, friendly, and structured advice about cloud computing concepts, "
    "Docker, AWS, GCP, Azure, Python, databases, and general internship guidance.\n\n"
    "Guidelines:\n"
    "- Format responses in clean Markdown (use **bolding**, lists, and `code` snippets where appropriate).\n"
    "- Keep explanations concise (2 to 5 sentences or short bullet points), readable, and polite.\n"
    "- If a query is ambiguous, give a brief helpful answer and suggest how they can proceed.\n"
    "- If asked about CodeAlpha specifics not in your knowledge, honestly guide them to contact support at services@codealpha.tech."
)

# Pick any model slug from https://openrouter.ai/models
# Primary and fallback free-tier models:
MODEL_NAME = os.environ.get("OPENROUTER_MODEL", "meta-llama/llama-3.1-8b-instruct:free")
FALLBACK_MODELS = [
    MODEL_NAME,
    "google/gemma-2-9b-it:free",
    "mistralai/mistral-7b-instruct:free",
    "qwen/qwen-2.5-7b-instruct:free",
]

# Optional but recommended by OpenRouter for attribution/rankings
SITE_URL = os.environ.get("SITE_URL", "https://codealpha.tech")
SITE_NAME = os.environ.get("SITE_NAME", "CodeAlpha Chatbot")


def _get_client():
    global _client
    if _client is None:
        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            raise RuntimeError("OPENROUTER_API_KEY is not set in environment")
        _client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
        )
    return _client


def get_ai_response(user_message: str, history: list = None) -> str:
    """
    Sends the user message along with recent conversation history to OpenRouter.
    Attempts primary model and seamlessly falls back if rate-limited or busy.
    """
    client = _get_client()

    extra_headers = {}
    if SITE_URL:
        extra_headers["HTTP-Referer"] = SITE_URL
    if SITE_NAME:
        extra_headers["X-Title"] = SITE_NAME

    # Assemble message context with recent history (up to last 6 turns)
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    if history and isinstance(history, list):
        # Keep last 6 valid messages to stay well within token bounds
        for item in history[-6:]:
            role = item.get("role")
            content = item.get("content")
            if role in ("user", "assistant") and isinstance(content, str) and content.strip():
                messages.append({"role": role, "content": content.strip()[:600]})

    messages.append({"role": "user", "content": user_message})

    # Try models in order: configured model first, then fallbacks
    models_to_try = []
    for m in FALLBACK_MODELS:
        if m and m not in models_to_try:
            models_to_try.append(m)

    last_error = None
    for model in models_to_try:
        try:
            completion = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.6,
                max_tokens=450,
                extra_headers=extra_headers or None,
            )
            reply = completion.choices[0].message.content
            if reply and reply.strip():
                return reply.strip()
        except Exception as err:
            last_error = err
            continue

    if last_error:
        raise last_error

    return "I'm having a brief issue reaching the generative model. Please try asking again in a moment."
