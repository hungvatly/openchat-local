/**
 * OpenChat Local — Frontend
 */

const state = {
    messages: [],
    model: null,
    models: [],
    mode: "docs",  // "docs" | "web" | "plain"
    isStreaming: false,
    uploadedFiles: [],
    profile: "medium",
    recommendedModels: [],
};

// ── DOM refs ───────────────────────

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

const welcomeEl = $(".welcome");
const chatAreaEl = $(".chat-area");
const textareaEl = $("#chat-input");
const sendBtn = $("#send-btn");
const modelSelect = $("#model-select");
const charCount = $(".char-count");
const statusDot = $(".status-dot");
const modeSelect = $("#mode-select");

// ── Init ───────────────────────────

async function init() {
    await checkHealth();
    await loadModels();
    setupListeners();
    textareaEl.focus();
}

async function checkHealth() {
    try {
        const res = await fetch("/api/health");
        const data = await res.json();
        statusDot.classList.toggle("connected", data.ollama_connected);
        state.profile = data.profile || "medium";
        state.recommendedModels = data.recommended_models || [];
        if (data.rag) {
            const statsEl = $("#rag-stats");
            if (statsEl) statsEl.textContent = `${data.rag.total_chunks} chunks`;
        }
        const profileEl = $("#hw-profile");
        if (profileEl) profileEl.textContent = state.profile;
    } catch {
        statusDot.classList.remove("connected");
    }
}

async function loadModels() {
    try {
        const res = await fetch("/api/models");
        const data = await res.json();
        state.models = data.models || [];
        state.model = data.default;

        modelSelect.innerHTML = "";
        if (state.models.length === 0) {
            const opt = document.createElement("option");
            opt.value = "";
            opt.textContent = "No models found";
            modelSelect.appendChild(opt);
            return;
        }

        state.models.forEach((m) => {
            const opt = document.createElement("option");
            opt.value = m.name;
            opt.textContent = m.name;
            if (m.name === state.model) opt.selected = true;
            modelSelect.appendChild(opt);
        });
    } catch {
        modelSelect.innerHTML = '<option value="">Ollama offline</option>';
    }
}

// ── Listeners ──────────────────────

function setupListeners() {
    textareaEl.addEventListener("input", () => {
        textareaEl.style.height = "auto";
        textareaEl.style.height = Math.min(textareaEl.scrollHeight, 160) + "px";
        charCount.textContent = `${textareaEl.value.length}/1000`;
    });

    textareaEl.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    sendBtn.addEventListener("click", sendMessage);
    modelSelect.addEventListener("change", (e) => (state.model = e.target.value));

    if (modeSelect) {
        modeSelect.addEventListener("change", (e) => {
            state.mode = e.target.value;
        });
    }

    $$(".prompt-card").forEach((card) => {
        card.addEventListener("click", () => {
            textareaEl.value = card.querySelector(".prompt-card-text").textContent;
            textareaEl.dispatchEvent(new Event("input"));
            sendMessage();
        });
    });

    $(".refresh-btn").addEventListener("click", shufflePrompts);

    // Sidebar buttons
    $("#btn-new-chat").addEventListener("click", clearChat);
    $("#btn-upload").addEventListener("click", openUploadPanel);
    $("#btn-settings").addEventListener("click", openSettingsPanel);

    // Panels
    $$(".panel-overlay").forEach((overlay) => {
        overlay.addEventListener("click", (e) => {
            if (e.target === overlay) overlay.classList.remove("active");
        });
    });
}

// ── Chat ───────────────────────────

async function sendMessage() {
    const text = textareaEl.value.trim();
    if (!text || state.isStreaming) return;

    state.isStreaming = true;
    sendBtn.disabled = true;

    // Show chat area, hide welcome
    welcomeEl.classList.add("hidden");
    chatAreaEl.classList.add("active");

    // Add user message
    appendMessage("user", text);
    state.messages.push({ role: "user", content: text });

    textareaEl.value = "";
    textareaEl.style.height = "auto";
    charCount.textContent = "0/1000";

    // Create AI message placeholder
    const aiMsgEl = appendMessage("ai", "");
    const contentEl = aiMsgEl.querySelector(".message-content");
    contentEl.innerHTML = '<div class="typing-indicator"><span></span><span></span><span></span></div>';

    try {
        const res = await fetch("/api/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                message: text,
                model: state.model,
                mode: state.mode,
                history: state.messages.slice(-10),
            }),
        });

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let fullText = "";
        let sources = [];

        contentEl.innerHTML = "";

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value, { stream: true });
            const lines = chunk.split("\n");

            for (const line of lines) {
                if (!line.startsWith("data: ")) continue;
                try {
                    const data = JSON.parse(line.slice(6));
                    if (data.token) {
                        fullText += data.token;
                        contentEl.innerHTML = renderMarkdown(fullText);
                        chatAreaEl.scrollTop = chatAreaEl.scrollHeight;
                    }
                    if (data.done) {
                        sources = data.sources || [];
                    }
                } catch {}
            }
        }

        // Add sources if available
        if (sources.length > 0) {
            const srcDiv = document.createElement("div");
            srcDiv.className = "sources";
            const seen = new Set();
            sources.forEach((s) => {
                if (seen.has(s.source)) return;
                seen.add(s.source);
                if (s.url) {
                    const link = document.createElement("a");
                    link.className = "source-tag source-link";
                    link.href = s.url;
                    link.target = "_blank";
                    link.rel = "noopener";
                    link.textContent = s.source;
                    srcDiv.appendChild(link);
                } else {
                    const tag = document.createElement("span");
                    tag.className = "source-tag";
                    tag.textContent = s.source;
                    srcDiv.appendChild(tag);
                }
            });
            aiMsgEl.appendChild(srcDiv);
        }

        state.messages.push({ role: "assistant", content: fullText });
    } catch (err) {
        contentEl.innerHTML = `<p style="color:var(--error)">Error: ${err.message}. Is Ollama running?</p>`;
    }

    state.isStreaming = false;
    sendBtn.disabled = false;
    textareaEl.focus();
}

function appendMessage(role, text) {
    const div = document.createElement("div");
    div.className = `message message-${role}`;
    div.innerHTML = `<div class="message-content">${role === "user" ? escapeHtml(text) : renderMarkdown(text)}</div>`;
    chatAreaEl.appendChild(div);
    chatAreaEl.scrollTop = chatAreaEl.scrollHeight;
    return div;
}

function clearChat() {
    state.messages = [];
    chatAreaEl.innerHTML = "";
    chatAreaEl.classList.remove("active");
    welcomeEl.classList.remove("hidden");
    textareaEl.focus();
}

// ── Markdown (minimal) ─────────────

function renderMarkdown(text) {
    if (!text) return "";
    let html = escapeHtml(text);

    // Code blocks
    html = html.replace(/```(\w*)\n([\s\S]*?)```/g, (_, lang, code) => {
        return `<pre><code class="language-${lang}">${code.trim()}</code></pre>`;
    });

    // Inline code
    html = html.replace(/`([^`]+)`/g, "<code>$1</code>");

    // Bold
    html = html.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");

    // Italic
    html = html.replace(/\*(.+?)\*/g, "<em>$1</em>");

    // Headers
    html = html.replace(/^### (.+)$/gm, "<h4>$1</h4>");
    html = html.replace(/^## (.+)$/gm, "<h3>$1</h3>");
    html = html.replace(/^# (.+)$/gm, "<h2>$1</h2>");

    // Lists
    html = html.replace(/^- (.+)$/gm, "<li>$1</li>");
    html = html.replace(/(<li>.*<\/li>)/gs, "<ul>$1</ul>");

    // Paragraphs
    html = html
        .split("\n\n")
        .map((p) => {
            p = p.trim();
            if (!p) return "";
            if (p.startsWith("<")) return p;
            return `<p>${p}</p>`;
        })
        .join("");

    // Clean up single newlines within paragraphs
    html = html.replace(/(?<!>)\n(?!<)/g, "<br>");

    return html;
}

function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}

// ── Prompt cards ───────────────────

const PROMPTS = [
    "Summarize the key points from my documents",
    "What are the main topics covered in my files?",
    "Generate a to-do list from my notes",
    "Write an email reply based on my documents",
    "Find any dates or deadlines mentioned in my files",
    "Explain the technical concepts in my documents",
    "Compare the ideas across my uploaded files",
    "Create a study guide from my materials",
    "What questions do my documents leave unanswered?",
    "Extract all names and entities from my files",
    "Summarize each uploaded document in one sentence",
    "What are the action items from my meeting notes?",
];

function shufflePrompts() {
    const cards = $$(".prompt-card-text");
    const shuffled = [...PROMPTS].sort(() => Math.random() - 0.5);
    cards.forEach((card, i) => {
        if (shuffled[i]) card.textContent = shuffled[i];
    });
}

// ── Upload Panel ───────────────────

function openUploadPanel() {
    $("#upload-panel").classList.add("active");
    loadWatcherStatus();
}

async function uploadFile() {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = ".txt,.pdf,.docx,.md,.csv,.xml";
    input.multiple = true;

    input.onchange = async () => {
        const statusEl = $("#upload-status");
        const listEl = $("#file-list");

        for (const file of input.files) {
            statusEl.textContent = `Uploading ${file.name}...`;
            const formData = new FormData();
            formData.append("file", file);

            try {
                const res = await fetch("/api/documents/upload", {
                    method: "POST",
                    body: formData,
                });
                const data = await res.json();

                if (data.status === "ok") {
                    const item = document.createElement("div");
                    item.className = "file-item";
                    item.innerHTML = `
                        <span class="file-name">${data.filename}</span>
                        <span class="file-chunks">${data.chunks} chunks</span>
                    `;
                    listEl.appendChild(item);
                    state.uploadedFiles.push(data.filename);
                    statusEl.textContent = `${data.filename} indexed (${data.chunks} chunks)`;
                } else {
                    statusEl.textContent = `Error: ${data.error || data.message}`;
                }
            } catch (err) {
                statusEl.textContent = `Upload failed: ${err.message}`;
            }
        }

        await checkHealth();
    };

    input.click();
}

async function ingestFolder() {
    const folderInput = $("#folder-path");
    const path = folderInput.value.trim();
    if (!path) return;

    const statusEl = $("#upload-status");
    statusEl.textContent = "Indexing folder...";

    try {
        const res = await fetch("/api/documents/folder", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ folder_path: path }),
        });
        const data = await res.json();

        if (data.status === "ok") {
            statusEl.textContent = `Indexed ${data.files_processed} files`;
            const listEl = $("#file-list");
            data.details.forEach((f) => {
                const item = document.createElement("div");
                item.className = "file-item";
                item.innerHTML = `
                    <span class="file-name">${f.filename}</span>
                    <span class="file-chunks">${f.chunks} chunks</span>
                `;
                listEl.appendChild(item);
            });
        } else {
            statusEl.textContent = `Error: ${data.error}`;
        }
    } catch (err) {
        statusEl.textContent = `Error: ${err.message}`;
    }

    await checkHealth();
}

async function ingestYouTube() {
    const urlInput = $("#youtube-url");
    const url = urlInput.value.trim();
    if (!url) return;

    const statusEl = $("#upload-status");
    statusEl.textContent = "Extracting transcript...";

    try {
        const res = await fetch("/api/documents/youtube", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ url }),
        });
        const data = await res.json();
        statusEl.textContent = data.status === "ok"
            ? `YouTube video indexed (${data.chunks} chunks)`
            : `Error: ${data.error}`;
    } catch (err) {
        statusEl.textContent = `Error: ${err.message}`;
    }

    urlInput.value = "";
    await checkHealth();
}

async function clearDocuments() {
    if (!confirm("Clear all indexed documents?")) return;
    await fetch("/api/documents/clear", { method: "POST" });
    $("#file-list").innerHTML = "";
    $("#upload-status").textContent = "All documents cleared";
    state.uploadedFiles = [];
    await checkHealth();
}

// ── Watch Folder ───────────────────

async function addWatchFolder() {
    const input = $("#watch-folder-path");
    const folder = input.value.trim();
    if (!folder) return;

    const statusEl = $("#watch-status");
    statusEl.textContent = "Adding watch folder...";

    try {
        const res = await fetch("/api/watcher/add", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ folder }),
        });
        const data = await res.json();

        if (data.status === "ok") {
            const scan = data.initial_scan || {};
            const count = (scan.indexed || []).length;
            statusEl.textContent = count > 0
                ? `Watching! Indexed ${count} file(s) on first scan.`
                : `Watching! No new files found yet.`;
            input.value = "";
            await loadWatcherStatus();
        } else {
            statusEl.textContent = `Error: ${data.message || data.error}`;
        }
    } catch (err) {
        statusEl.textContent = `Error: ${err.message}`;
    }

    await checkHealth();
}

async function removeWatchFolder(folder) {
    try {
        await fetch("/api/watcher/remove", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ folder }),
        });
        await loadWatcherStatus();
    } catch {}
}

async function forceScan() {
    const statusEl = $("#watch-status");
    statusEl.textContent = "Scanning...";

    try {
        const res = await fetch("/api/watcher/scan", { method: "POST" });
        const data = await res.json();
        const count = (data.indexed || []).length;
        if (count > 0) {
            const names = data.indexed.map((f) => f.filename).join(", ");
            statusEl.textContent = `Found and indexed ${count} new file(s): ${names}`;
        } else {
            statusEl.textContent = "No new or changed files found.";
        }
    } catch (err) {
        statusEl.textContent = `Scan error: ${err.message}`;
    }

    await checkHealth();
    await loadWatcherStatus();
}

async function loadWatcherStatus() {
    try {
        const res = await fetch("/api/watcher/status");
        const data = await res.json();
        const container = $("#watch-folders");
        if (!container) return;

        container.innerHTML = "";
        if (data.watch_dirs && data.watch_dirs.length > 0) {
            data.watch_dirs.forEach((dir) => {
                const item = document.createElement("div");
                item.style.cssText = "display:flex;align-items:center;justify-content:space-between;padding:6px 0;border-bottom:1px solid var(--border);font-size:13px";
                item.innerHTML = `
                    <span style="color:var(--text-secondary);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:320px" title="${dir}">${dir}</span>
                    <button onclick="removeWatchFolder('${dir.replace(/'/g, "\\'")}')" style="background:none;border:none;color:var(--text-muted);cursor:pointer;font-size:12px;padding:2px 6px">remove</button>
                `;
                container.appendChild(item);
            });

            const info = document.createElement("div");
            info.style.cssText = "font-size:11px;color:var(--text-muted);margin-top:6px";
            const mins = Math.round(data.poll_interval / 60);
            const intervalLabel = mins >= 1 ? `${mins} min` : `${data.poll_interval}s`;
            info.textContent = `${data.total_files_tracked} files tracked · ${data.total_auto_indexed} auto-indexed · auto-scan every ${intervalLabel}`;
            container.appendChild(info);
        }
    } catch {}
}

// ── Settings Panel ─────────────────

function openSettingsPanel() {
    $("#settings-panel").classList.add("active");
}

// ── Boot ───────────────────────────

document.addEventListener("DOMContentLoaded", init);
