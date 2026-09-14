"""
Generative AI layer with multi-provider support:
- Groq (https://api.groq.com/openai/v1) -> Fast inference (Compound-mini, Qwen, etc.)
- OpenRouter (https://openrouter.ai/api/v1) -> Mistral 7B free, Llama, Gemma, etc.
- Mistral AI (https://api.mistral.ai/v1) -> Official open-mistral-7b
- Grok / xAI (https://api.x.ai/v1) -> grok-2-latest, grok-beta

Auto-detects provider based on API key prefix or explicit configuration.
"""

import os
from openai import OpenAI

_client = None
_detected_provider = None
_active_model = None

SYSTEM_PROMPT = (
    "You are a helpful, friendly AI Assistant. "
    "You provide clear, structured answers to general questions, technical topics, "
    "coding help, and everyday queries.\n\n"
    "Guidelines:\n"
    "- Format responses in clean Markdown (use **bolding**, lists, and `code` snippets where appropriate).\n"
    "- Keep explanations concise (2 to 5 sentences or short bullet points), readable, and polite.\n"
    "- If a query is ambiguous, give a brief helpful answer and suggest how they can proceed."
)

# Which env var(s) hold the key for each provider, in the order they should be checked.
PROVIDER_KEY_ENV = {
    "groq": ("GROQ_API_KEY",),
    "openrouter": ("OPENROUTER_API_KEY",),
    "mistral": ("MISTRAL_API_KEY",),
    "grok": ("GROK_API_KEY", "XAI_API_KEY"),
}

PROVIDER_CONFIGS = {
    "groq": {
        "name": "Groq",
        "base_url": "https://api.groq.com/openai/v1",
        "default_model": "groq/compound-mini",
        "fallbacks": ["groq/compound-mini", "qwen/qwen3.8-27b", "openai/gpt-oss-120b"],
    },
    "openrouter": {
        "name": "OpenRouter",
        "base_url": "https://openrouter.ai/api/v1",
        "default_model": "mistralai/mistral-7b-instruct:free",
        "fallbacks": [
            "mistralai/mistral-7b-instruct:free",
            "mistralai/mistral-7b-instruct",
            "google/gemma-2-9b-it:free",
            "qwen/qwen-2.5-7b-instruct:free",
        ],
    },
    "mistral": {
        "name": "Mistral AI",
        "base_url": "https://api.mistral.ai/v1",
        "default_model": "open-mistral-7b",
        "fallbacks": ["open-mistral-7b", "mistral-small-latest"],
    },
    "grok": {
        "name": "xAI Grok",
        "base_url": "https://api.x.ai/v1",
        "default_model": "grok-2-latest",
        "fallbacks": ["grok-2-latest", "grok-beta"],
    },
}


def _clean_key(val):
    """Strips whitespace and accidental surrounding quotes some .env parsers leave in."""
    if val is None:
        return None
    val = val.strip()
    if len(val) >= 2 and val[0] == val[-1] and val[0] in ("'", '"'):
        val = val[1:-1].strip()
    return val or None


def _key_for_provider(provider):
    """Looks up a provider's own key env var(s) only - never another provider's."""
    for env_name in PROVIDER_KEY_ENV.get(provider, ()):
        val = _clean_key(os.environ.get(env_name))
        if val:
            return val
    return None


def _detect_provider_from_key(key):
    if not key:
        return None
    if key.startswith("gsk_"):
        return "groq"
    if key.startswith("sk-or-"):
        return "openrouter"
    if key.startswith("xai-"):
        return "grok"
    return None


def resolve_config():
    """
    Determines provider, base_url, api_key, and models based on environment variables.

    Provider and API key are resolved together with key-prefix auto-detection so a key
    never gets sent to the wrong provider's endpoint (e.g. a Groq gsk_ key being used
    against openrouter.ai).
    """
    explicit_provider = os.environ.get("AI_PROVIDER", "").strip().lower()
    base_url = os.environ.get("AI_BASE_URL", "").strip()
    custom_model = os.environ.get("AI_MODEL") or os.environ.get("OPENROUTER_MODEL")
    generic_key = _clean_key(os.environ.get("AI_API_KEY"))

    provider = None
    api_key = None

    if explicit_provider:
        if explicit_provider not in PROVIDER_CONFIGS:
            return None, None, None, [], (
                f"Unknown AI_PROVIDER '{explicit_provider}'. Choose one of: "
                f"{', '.join(PROVIDER_CONFIGS)}."
            )
        api_key = _key_for_provider(explicit_provider) or generic_key
        # If no key found for explicit provider, check other env vars before giving up
        if not api_key:
            for cand in ("groq", "openrouter", "mistral", "grok"):
                k = _key_for_provider(cand)
                if k:
                    api_key = k
                    break

        # Check if the key's prefix indicates a different provider (e.g. gsk_ with openrouter)
        sniffed = _detect_provider_from_key(api_key)
        if sniffed and sniffed != explicit_provider:
            provider = sniffed
        else:
            provider = explicit_provider

        if not api_key:
            env_hint = " or ".join(PROVIDER_KEY_ENV[explicit_provider])
            return None, None, None, [], (
                f"AI_PROVIDER is set to '{explicit_provider}' but no matching key was found. "
                f"Set {env_hint} (or AI_API_KEY) in .env."
            )
    else:
        # 1. Prefer a provider-specific key, checked in priority order.
        for candidate in ("groq", "openrouter", "mistral", "grok"):
            key = _key_for_provider(candidate)
            if key:
                # Validate if the key prefix points to another provider
                sniffed = _detect_provider_from_key(key)
                provider = sniffed if sniffed else candidate
                api_key = key
                break

        # 2. Fall back to a generic key, sniffing its prefix to guess the provider.
        if not provider and generic_key:
            provider = _detect_provider_from_key(generic_key) or "groq"
            api_key = generic_key

    if not api_key:
        return None, None, None, [], (
            "No API key configured. Set GROQ_API_KEY, OPENROUTER_API_KEY, MISTRAL_API_KEY, "
            "GROK_API_KEY/XAI_API_KEY, or a generic AI_API_KEY in .env."
        )

    conf = PROVIDER_CONFIGS.get(provider, PROVIDER_CONFIGS["groq"])
    target_base_url = base_url or conf["base_url"]

    # 3. Determine models
    models_to_try = []
    if custom_model:
        # Handle shorthand alias like 'mistral-7b' -> full slug on openrouter
        if provider == "openrouter" and custom_model in ("mistral-7b", "mistral-7b-instruct"):
            custom_model = "mistralai/mistral-7b-instruct:free"
        models_to_try.append(custom_model)

    for m in conf["fallbacks"]:
        if m not in models_to_try:
            models_to_try.append(m)

    return provider, target_base_url, api_key, models_to_try, None


def debug_config():
    """
    Returns a human-readable, secret-safe summary of what resolve_config() picked.
    Call this manually (e.g. `python -c "import ai; print(ai.debug_config())"`)
    to check which provider/key/model the app will actually use, without ever
    printing the real key.
    """
    provider, base_url, api_key, models, err = resolve_config()
    if err:
        return f"[ai.debug_config] ERROR: {err}"
    masked = f"{api_key[:4]}...{api_key[-4:]}" if api_key and len(api_key) > 8 else "(too short to mask safely)"
    return (
        f"[ai.debug_config] provider={provider} base_url={base_url} "
        f"key={masked} (len={len(api_key) if api_key else 0}) "
        f"models={models}"
    )


_cached_key = None
_cached_base_url = None

def _get_client_and_models():
    global _client, _detected_provider, _active_model, _cached_key, _cached_base_url

    provider, base_url, api_key, models, err = resolve_config()
    if err:
        raise RuntimeError(err)

    if _client is None or _detected_provider != provider or _cached_key != api_key or _cached_base_url != base_url:
        _client = OpenAI(
            base_url=base_url,
            api_key=api_key,
        )
        _detected_provider = provider
        _cached_key = api_key
        _cached_base_url = base_url
        _active_model = models[0] if models else "default"

    return _client, provider, models


def get_ai_response(user_message: str, history: list = None) -> str:
    """
    Sends the user message along with recent conversation history to the active AI provider.
    Tries the primary model and falls back if rate-limited or busy.
    """
    client, provider, models = _get_client_and_models()

    extra_headers = {}
    site_url = os.environ.get("SITE_URL", "http://localhost:5000")
    site_name = os.environ.get("SITE_NAME", "AI Assistant")
    if provider == "openrouter":
        if site_url:
            extra_headers["HTTP-Referer"] = site_url
        if site_name:
            extra_headers["X-Title"] = site_name

    # Assemble message context with recent history (up to last 6 turns)
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    if history and isinstance(history, list):
        for item in history[-6:]:
            role = item.get("role")
            content = item.get("content")
            if role in ("user", "assistant") and isinstance(content, str) and content.strip():
                messages.append({"role": role, "content": content.strip()[:600]})

    messages.append({"role": "user", "content": user_message})

    last_error = None
    for model in models:
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

    return "I'm having a brief issue reaching the AI backend. Please try asking again in a moment."