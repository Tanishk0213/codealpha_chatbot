"""
Retrieval-based layer: matches user input against predefined patterns.
Runs before the generative AI call so common questions get instant,
predictable, zero-cost answers formatted in clean Markdown.
"""

import re

# Each entry: (list of regex patterns, response string with Markdown)
FAQ_PATTERNS = [
    (
        [r"\bhi\b", r"\bhello\b", r"\bhey\b", r"\bgreetings\b", r"good\s+(morning|afternoon|evening)"],
        "👋 **Hello! Welcome to AI Assistant!**\n\n"
        "I'm here to help answer your questions. You can ask me about:\n"
        "- 💡 **General knowledge & explanations**\n"
        "- 💻 **Code & technical help**\n"
        "- ✍️ **Writing & brainstorming**\n\n"
        "How can I help you today?"
    ),
    (
        [r"how are you", r"how('s| is) it going"],
        "⚡ I'm running smoothly and ready to help! What's on your mind?"
    ),
    (
        [r"\bwho are you\b", r"\bwhat are you\b", r"about (you|yourself)"],
        "🤖 I am your **AI Assistant**, a dual-engine chatbot.\n\n"
        "I use an instant **Pattern-Matching FAQ Engine** for common questions, backed by a "
        "**Generative AI Fallback** for more complex or open-ended queries."
    ),
    (
        [r"what can you do", r"your capabilities", r"help me with"],
        "💡 **What I can help with**\n\n"
        "- Answering general questions\n"
        "- Explaining concepts in plain language\n"
        "- Helping with code, debugging, and technical topics\n"
        "- Brainstorming and writing assistance\n\n"
        "Just ask away!"
    ),
    (
        [r"\bthanks\b", r"\bthank you\b", r"appreciate it"],
        "🙌 You're very welcome! Feel free to ask if you have more questions."
    ),
    (
        [r"\bbye\b", r"\bsee you\b", r"\bgoodbye\b", r"cya"],
        "👋 Goodbye! Have a great day."
    ),
]

_COMPILED = [
    ([re.compile(p, re.IGNORECASE) for p in patterns], response)
    for patterns, response in FAQ_PATTERNS
]


def match_faq(message: str):
    """
    Returns a matching FAQ response string if the message matches a known
    pattern, otherwise returns None so the caller can fall back to the AI model.
    """
    cleaned = message.strip()
    for patterns, response in _COMPILED:
        for pattern in patterns:
            if pattern.search(cleaned):
                return response
    return None
