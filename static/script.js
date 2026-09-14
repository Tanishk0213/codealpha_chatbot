/**
 * AI Assistant - Modern Interactive Client
 * Features:
 * - Multi-turn conversation memory
 * - Markdown & code syntax formatting via marked + DOMPurify
 * - Dark / Light Theme switching with localStorage persistence
 * - Speech-to-Text Voice Recognition (Web Speech API)
 * - Quick Suggestion Chips
 * - Auto-expanding multiline input & char counter
 * - Real 3-dot bouncing typing indicator
 * - Chat export (.txt) and Clear conversation
 * - Dynamic server health status indicator
 */

// DOM Elements
const chatWindow = document.getElementById("chatWindow");
const chatInput = document.getElementById("chatInput");
const sendBtn = document.getElementById("sendBtn");
const micBtn = document.getElementById("micBtn");
const charCounter = document.getElementById("charCounter");
const themeToggleBtn = document.getElementById("themeToggleBtn");
const clearBtn = document.getElementById("clearBtn");
const exportBtn = document.getElementById("exportBtn");
const statusDot = document.getElementById("statusDot");
const statusText = document.getElementById("statusText");
const welcomeCard = document.getElementById("welcomeCard");

// Application State
let sessionId = localStorage.getItem("chat_session_id");
if (!sessionId) {
  sessionId = "sess_" + Math.random().toString(36).substring(2, 11) + "_" + Date.now();
  localStorage.setItem("chat_session_id", sessionId);
}
let conversationHistory = []; // Stores { role: "user" | "assistant", content: string }
let isProcessing = false;
let recognition = null;
let isListening = false;

// ============================================================
// 1. Theme Management (Dark / Light)
// ============================================================
function initTheme() {
  const savedTheme = localStorage.getItem("chat_theme") || "dark";
  document.documentElement.setAttribute("data-theme", savedTheme);
}

themeToggleBtn.addEventListener("click", () => {
  const currentTheme = document.documentElement.getAttribute("data-theme") || "dark";
  const newTheme = currentTheme === "dark" ? "light" : "dark";
  document.documentElement.setAttribute("data-theme", newTheme);
  localStorage.setItem("chat_theme", newTheme);
});

// ============================================================
// 2. Server Health Check
// ============================================================
async function checkHealth() {
  try {
    const res = await fetch("/health");
    if (res.ok) {
      const data = await res.json();
      statusDot.className = "status-indicator online";
      if (data.database === "connected") {
        statusDot.title = "Connected to Flask Backend & MongoDB Atlas Cloud DB";
        statusText.textContent = "Dual-Engine • Cloud DB Active";
      } else {
        statusDot.title = "Connected to Flask Backend";
        statusText.textContent = "Dual-Engine • Online";
      }
    } else {
      throw new Error("Bad status");
    }
  } catch {
    statusDot.className = "status-indicator offline";
    statusDot.title = "Backend unreachable";
    statusText.textContent = "Server Offline";
  }
}

// ============================================================
// 3. UI Helpers & Formatting
// ============================================================
function formatTime() {
  const now = new Date();
  return now.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function escapeHtml(str) {
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function renderContent(rawText, isBot) {
  if (!isBot) {
    return `<p>${escapeHtml(rawText)}</p>`;
  }

  // Use marked.js + DOMPurify if available for rich Markdown
  if (typeof marked !== "undefined" && typeof DOMPurify !== "undefined") {
    try {
      const parsed = marked.parse(rawText, { gfm: true, breaks: true });
      return DOMPurify.sanitize(parsed);
    } catch (e) {
      console.error("Markdown parse error:", e);
    }
  }

  // Fallback if CDN failed
  return `<p>${escapeHtml(rawText).replace(/\n/g, "<br>")}</p>`;
}

function scrollChatToBottom() {
  chatWindow.scrollTo({
    top: chatWindow.scrollHeight,
    behavior: "smooth"
  });
}

// ============================================================
// 4. Message Rendering
// ============================================================
function appendMessage(text, sender, source = null) {
  // Hide welcome hero if still visible
  if (welcomeCard && welcomeCard.parentNode) {
    welcomeCard.style.display = "none";
  }

  const isBot = sender === "bot";
  const row = document.createElement("div");
  row.className = `message-row ${sender}`;

  // Avatar
  const avatar = document.createElement("div");
  avatar.className = "message-avatar";
  avatar.textContent = isBot ? "🤖" : "👤";

  // Content wrapper
  const contentWrapper = document.createElement("div");
  contentWrapper.className = "message-content-wrapper";

  // Bubble
  const bubble = document.createElement("div");
  bubble.className = "message-bubble";
  bubble.innerHTML = renderContent(text, isBot);

  // Metadata (time, source badge, copy button)
  const meta = document.createElement("div");
  meta.className = "message-meta";

  const timeSpan = document.createElement("span");
  timeSpan.className = "time-stamp";
  timeSpan.textContent = formatTime();
  meta.appendChild(timeSpan);

  if (isBot && source) {
    const badge = document.createElement("span");
    if (source === "faq") {
      badge.className = "source-badge faq";
      badge.innerHTML = "⚡ Instant FAQ";
      badge.title = "Pattern-matched zero latency answer";
    } else if (source === "ai") {
      badge.className = "source-badge ai";
      badge.innerHTML = "🤖 AI";
      badge.title = "Generative LLM answer";
    } else if (source === "warning" || source === "error") {
      badge.className = "source-badge";
      badge.style.borderColor = "#f59e0b";
      badge.style.color = "#f59e0b";
      badge.innerHTML = "⚠️ Notice";
    }
    meta.appendChild(badge);
  }

  // Copy button
  const copyBtn = document.createElement("button");
  copyBtn.className = "copy-btn";
  copyBtn.innerHTML = `
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <rect width="14" height="14" x="8" y="8" rx="2" ry="2"></rect>
      <path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"></path>
    </svg>
    <span>Copy</span>
  `;
  copyBtn.addEventListener("click", () => {
    navigator.clipboard.writeText(text).then(() => {
      copyBtn.querySelector("span").textContent = "Copied!";
      setTimeout(() => {
        copyBtn.querySelector("span").textContent = "Copy";
      }, 2000);
    });
  });
  meta.appendChild(copyBtn);

  contentWrapper.appendChild(bubble);
  contentWrapper.appendChild(meta);

  row.appendChild(avatar);
  row.appendChild(contentWrapper);

  chatWindow.appendChild(row);
  scrollChatToBottom();
  return row;
}

// Typing Indicator
let currentTypingEl = null;

function showTyping() {
  if (currentTypingEl) return;
  const row = document.createElement("div");
  row.className = "message-row bot";
  row.id = "typingIndicator";

  const avatar = document.createElement("div");
  avatar.className = "message-avatar";
  avatar.textContent = "🤖";

  const contentWrapper = document.createElement("div");
  contentWrapper.className = "message-content-wrapper";

  const bubble = document.createElement("div");
  bubble.className = "message-bubble";
  bubble.innerHTML = `
    <div class="typing-dots">
      <div class="typing-dot"></div>
      <div class="typing-dot"></div>
      <div class="typing-dot"></div>
    </div>
  `;

  contentWrapper.appendChild(bubble);
  row.appendChild(avatar);
  row.appendChild(contentWrapper);

  chatWindow.appendChild(row);
  currentTypingEl = row;
  scrollChatToBottom();
}

function hideTyping() {
  if (currentTypingEl) {
    currentTypingEl.remove();
    currentTypingEl = null;
  }
}

// ============================================================
// 5. Send Message & Multi-Turn History
// ============================================================
async function sendMessage(textToSend = null) {
  if (isProcessing) return;

  const rawText = textToSend !== null ? textToSend : chatInput.value;
  const text = rawText.trim();
  if (!text) return;

  // Clear input & reset height
  chatInput.value = "";
  chatInput.style.height = "auto";
  updateCharCounter();

  // Render user message in UI
  appendMessage(text, "user");

  // Keep client-side conversation history for contextual memory
  conversationHistory.push({ role: "user", content: text });

  isProcessing = true;
  sendBtn.disabled = true;
  showTyping();

  try {
    const response = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: text,
        session_id: sessionId,
        // Send last 6 turns as conversation context
        history: conversationHistory.slice(-6),
      }),
    });

    const data = await response.json();
    hideTyping();

    if (!response.ok) {
      appendMessage(data.error || "An error occurred while processing your request.", "bot", "error");
    } else {
      appendMessage(data.reply, "bot", data.source);
      conversationHistory.push({ role: "assistant", content: data.reply });
    }
  } catch (err) {
    console.error("Fetch error:", err);
    hideTyping();
    appendMessage(
      "Network connection issue. Please make sure the server is running and try again.",
      "bot",
      "error"
    );
  } finally {
    isProcessing = false;
    sendBtn.disabled = false;
    chatInput.focus();
  }
}

// ============================================================
// 6. Input Handling, Auto-Growth & Char Counter
// ============================================================
function updateCharCounter() {
  const len = chatInput.value.length;
  charCounter.textContent = `${len}/500`;
  if (len >= 450) {
    charCounter.style.color = "#ef4444";
  } else {
    charCounter.style.color = "var(--text-muted)";
  }
}

chatInput.addEventListener("input", () => {
  chatInput.style.height = "auto";
  chatInput.style.height = Math.min(chatInput.scrollHeight, 120) + "px";
  updateCharCounter();
});

chatInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});

sendBtn.addEventListener("click", () => {
  sendMessage();
});

// ============================================================
// 7. Quick Suggestion Chips
// ============================================================
document.querySelectorAll(".suggestion-chip").forEach((chip) => {
  chip.addEventListener("click", () => {
    const prompt = chip.getAttribute("data-prompt");
    if (prompt) {
      sendMessage(prompt);
    }
  });
});

// ============================================================
// 8. Clear & Export Features
// ============================================================
clearBtn.addEventListener("click", () => {
  if (conversationHistory.length === 0) return;
  if (confirm("Are you sure you want to clear this conversation?")) {
    conversationHistory = [];
    sessionId = "sess_" + Math.random().toString(36).substring(2, 11) + "_" + Date.now();
    localStorage.setItem("chat_session_id", sessionId);
    // Remove all message rows except welcome card
    const rows = chatWindow.querySelectorAll(".message-row");
    rows.forEach((r) => r.remove());
    if (welcomeCard) {
      welcomeCard.style.display = "block";
    }
    chatInput.value = "";
    chatInput.style.height = "auto";
    updateCharCounter();
  }
});

exportBtn.addEventListener("click", () => {
  if (conversationHistory.length === 0) {
    alert("No messages to export yet!");
    return;
  }

  let exportText = "=== AI Assistant Conversation ===\n";
  exportText += `Date: ${new Date().toLocaleString()}\n`;
  exportText += "===========================================\n\n";

  conversationHistory.forEach((item) => {
    const speaker = item.role === "user" ? "You" : "AI Assistant";
    exportText += `[${speaker}]:\n${item.content}\n\n`;
  });

  const blob = new Blob([exportText], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `Chat_${new Date().toISOString().slice(0, 10)}.txt`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
});

// ============================================================
// 9. Speech-to-Text (Voice Recognition)
// ============================================================
function setupVoiceRecognition() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    micBtn.style.opacity = "0.4";
    micBtn.title = "Voice recognition not supported in this browser";
    return;
  }

  recognition = new SpeechRecognition();
  recognition.continuous = false;
  recognition.interimResults = false;
  recognition.lang = "en-US";

  recognition.onstart = () => {
    isListening = true;
    micBtn.classList.add("listening");
    chatInput.setAttribute("placeholder", "Listening... Speak now");
  };

  recognition.onresult = (event) => {
    const transcript = event.results[0][0].transcript;
    chatInput.value = (chatInput.value + " " + transcript).trim();
    chatInput.style.height = "auto";
    chatInput.style.height = Math.min(chatInput.scrollHeight, 120) + "px";
    updateCharCounter();
  };

  recognition.onerror = (event) => {
    console.warn("Speech recognition error:", event.error);
    stopListening();
  };

  recognition.onend = () => {
    stopListening();
  };
}

function stopListening() {
  isListening = false;
  micBtn.classList.remove("listening");
  chatInput.setAttribute("placeholder", "Ask a question or select a topic above...");
}

micBtn.addEventListener("click", () => {
  if (!recognition) {
    alert("Speech recognition is not supported in this browser. Please use Chrome or Edge.");
    return;
  }

  if (isListening) {
    recognition.stop();
  } else {
    try {
      recognition.start();
    } catch (e) {
      console.error(e);
    }
  }
});

// ============================================================
// 10. Initialization
// ============================================================
document.addEventListener("DOMContentLoaded", () => {
  initTheme();
  checkHealth();
  setupVoiceRecognition();
  updateCharCounter();
  chatInput.focus();

  // Periodic health check every 45s
  setInterval(checkHealth, 45000);
});

