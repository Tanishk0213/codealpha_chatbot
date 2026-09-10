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
        "👋 **Hello! Welcome to CodeAlpha Assistant!**\n\n"
        "I'm here to guide you through your **Cloud Computing Internship**. You can ask me about:\n"
        "- 📋 **Internship Tasks** (Task 1 to Task 4)\n"
        "- 📜 **Certificates & Verification**\n"
        "- 🚀 **Submission Guidelines & Deadlines**\n"
        "- 💡 **Cloud Tools & Architecture**\n\n"
        "How can I help you today?"
    ),
    (
        [r"how are you", r"how('s| is) it going"],
        "⚡ I'm running smoothly at full speed! Ready to help you ace your CodeAlpha internship projects. What's on your mind?"
    ),
    (
        [r"\bwho are you\b", r"\bwhat are you\b", r"about (you|yourself)"],
        "🤖 I am the **CodeAlpha AI Assistant**, an intelligent dual-engine chatbot built for the **Cloud Computing Internship (Task 4)**.\n\n"
        "I leverage an instant **Pattern-Matching FAQ Engine** for immediate answers, backed by a **Generative AI Fallback** for complex queries."
    ),
    (
        [r"about codealpha", r"what is codealpha", r"internship overview", r"domain"],
        "🌐 **CodeAlpha Internship Overview**\n\n"
        "CodeAlpha is a premier ed-tech and internship platform empowering students with practical skills.\n\n"
        "**Cloud Computing Domain Highlights:**\n"
        "- Hands-on deployment on **AWS, Azure, or GCP**\n"
        "- Virtualization, Containerization (**Docker**), and Serverless architectures\n"
        "- Identity, access management, and cloud security best practices."
    ),
    (
        [r"(all|what|list).*tasks", r"how many tasks", r"\btasks\b"],
        "📋 **CodeAlpha Cloud Computing Tasks Overview**\n\n"
        "To successfully complete your internship, you are required to finish at least **2 to 3 tasks**:\n\n"
        "1. **Task 1: Data Redundancy Removal** — Identify and eliminate duplicate data in cloud storage.\n"
        "2. **Task 2: SQL Injection Leak Detection** — Implement detection or mitigation of SQL injection in cloud databases.\n"
        "3. **Task 3: Cloud-Based Bus Pass System** — Full-stack cloud application for digital ticketing and verification.\n"
        "4. **Task 4: AI Chatbot** — Intelligent conversational assistant with instant FAQ + generative capabilities (This project!).\n\n"
        "Ask me about any specific task (e.g. *'Tell me about Task 1'* or *'How to do Task 4'*)!"
    ),
    (
        [r"task\s*1\b", r"data redundancy", r"deduplication"],
        "📂 **Task 1: Data Redundancy Removal**\n\n"
        "**Objective:** Build a solution that detects and eliminates duplicate records or files in cloud storage (e.g., AWS S3, Google Cloud Storage, or database tables).\n\n"
        "**Key Techniques:**\n"
        "- File hashing (MD5/SHA-256) to identify duplicate contents\n"
        "- Serverless functions (AWS Lambda / Google Cloud Functions) triggered upon file upload\n"
        "- Deduplication reports and automated cleanup."
    ),
    (
        [r"task\s*2\b", r"sql injection", r"leak detection", r"sqli"],
        "🛡️ **Task 2: SQL Injection Leak Detection**\n\n"
        "**Objective:** Create a cloud-based security monitoring or detection mechanism to flag SQL injection attempts and prevent data leaks.\n\n"
        "**Key Techniques:**\n"
        "- Input pattern validation & regex heuristic scanners\n"
        "- Cloud WAF (Web Application Firewall) configuration or logging interceptors\n"
        "- CloudWatch / Cloud Logging alerts for malicious database queries."
    ),
    (
        [r"task\s*3\b", r"bus pass", r"transit system"],
        "🚌 **Task 3: Cloud-Based Bus Pass System**\n\n"
        "**Objective:** Develop a cloud-hosted digital bus pass management portal for students/commuters.\n\n"
        "**Key Features:**\n"
        "- User authentication & profile management\n"
        "- Pass renewal, validation via unique QR codes\n"
        "- Cloud database (Firebase Firestore / AWS DynamoDB / PostgreSQL) hosting."
    ),
    (
        [r"task\s*4\b", r"chatbot task", r"ai chatbot project"],
        "🤖 **Task 4: AI-Powered Chatbot**\n\n"
        "**Objective:** Develop and deploy a dual-layer cloud-hosted chatbot.\n\n"
        "**Architecture of this Project:**\n"
        "- **Layer 1:** Fast regex/FAQ retrieval engine for zero-cost instant responses\n"
        "- **Layer 2:** Generative AI fallback powered by OpenRouter (Llama 3 / Mistral / Gemini)\n"
        "- **Frontend:** Modern responsive Web UI with dark/light mode, voice input, and markdown support\n"
        "- **Cloud Hosting:** Dockerized and deployable on Google Cloud Run, Render, or AWS ECS."
    ),
    (
        [r"certificate", r"completion letter", r"offer letter", r"perks"],
        "📜 **Certificates & Verification**\n\n"
        "Upon successfully completing your internship, you will receive:\n"
        "1. **Verified Completion Certificate** with a unique verifiable QR code & ID\n"
        "2. **Official Letter of Recommendation (LOR)** based on project quality\n"
        "3. **Offer Letter** (provided at the start of internship)\n\n"
        "*Requirement: Successfully complete and submit at least 2-3 assigned tasks.*"
    ),
    (
        [r"submission", r"how to submit", r"submit.*task", r"linkedin.*video"],
        "📤 **Task Submission Guidelines**\n\n"
        "Follow these steps for each completed task:\n\n"
        "1. **GitHub Repository:** Push your clean, well-documented code with a comprehensive `README.md`.\n"
        "2. **Video Demonstration:** Record a short video (1-3 mins) walking through your code and live running application.\n"
        "3. **Post on LinkedIn:** Share your video on LinkedIn, tag **CodeAlpha** and use relevant hashtags (`#CodeAlpha #CloudComputing #Internship`).\n"
        "4. **Submission Form:** Submit the GitHub link and LinkedIn post URL in the official CodeAlpha task submission form."
    ),
    (
        [r"stipend", r"paid", r"fees", r"cost"],
        "💰 **Internship Compensation & Fees**\n\n"
        "CodeAlpha internships are self-paced, project-driven learning opportunities designed to help students build production-grade portfolios. There are no mandatory upfront fees to build and submit your projects."
    ),
    (
        [r"deadline", r"duration", r"extension", r"how long"],
        "⏳ **Duration & Deadlines**\n\n"
        "- Standard internship duration is **1 month (4 weeks)**.\n"
        "- Check your official offer letter for your exact batch start and end dates.\n"
        "- If you need a brief extension due to exams or emergencies, reach out to support."
    ),
    (
        [r"contact", r"support", r"help.*human", r"whatsapp", r"email.*codealpha"],
        "📞 **CodeAlpha Support Channels**\n\n"
        "- **Email:** [services@codealpha.tech](mailto:services@codealpha.tech)\n"
        "- **WhatsApp Support:** +91 9336576683\n"
        "- **Official Website:** [codealpha.tech](https://codealpha.tech)\n"
        "- **LinkedIn:** [linkedin.com/company/codealpha](https://www.linkedin.com/company/codealpha/)"
    ),
    (
        [r"\bthanks\b", r"\bthank you\b", r"appreciate it"],
        "🙌 You're very welcome! Feel free to ask if you have more questions about tasks, code, or deployment. Best of luck with your internship!"
    ),
    (
        [r"\bbye\b", r"\bsee you\b", r"\bgoodbye\b", r"cya"],
        "👋 Goodbye! Have a productive coding session, and remember to push your code regularly to GitHub!"
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
