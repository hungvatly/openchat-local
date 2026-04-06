/**
 * OpenChat Local — Frontend
 */

const state = {
    messages: [],
    model: null,
    models: [],
    mode: "docs",
    isStreaming: false,
    uploadedFiles: [],
    profile: "medium",
    recommendedModels: [],
    conversationId: null,
    pendingImages: [],  // base64 images for vision
    isRecording: false,
    mediaRecorder: null,
    personaId: "default",
    ttsEnabled: false,
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
    // Configure marked.js for rich rendering
    if (typeof marked !== 'undefined') {
        marked.setOptions({
            highlight: function(code, lang) {
                if (typeof hljs !== 'undefined' && lang && hljs.getLanguage(lang)) {
                    return hljs.highlight(code, { language: lang }).value;
                }
                return typeof hljs !== 'undefined' ? hljs.highlightAuto(code).value : code;
            },
            breaks: true,
            gfm: true,
        });
    }
    if (typeof mermaid !== 'undefined') {
        mermaid.initialize({ startOnLoad: false, theme: 'dark' });
    }

    await checkHealth();
    await loadModels();
    await loadPersonas();
    await loadConversations();
    await loadFolders();
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

    // Sidebar
    $("#btn-new-chat").addEventListener("click", clearChat);
    const toggle = $("#sidebar-toggle");
    if (toggle) {
        toggle.addEventListener("click", () => {
            $(".sidebar").classList.toggle("collapsed");
        });
    }

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

    welcomeEl.classList.add("hidden");
    chatAreaEl.classList.add("active");

    // Show image previews if attached
    if (state.pendingImages.length > 0) {
        const imgPreview = document.createElement("div");
        imgPreview.className = "message message-user";
        imgPreview.innerHTML = `<div class="message-content"><img src="data:image/jpeg;base64,${state.pendingImages[0]}" style="max-width:200px;border-radius:8px;margin-bottom:4px"><br>${escapeHtml(text)}</div>`;
        chatAreaEl.appendChild(imgPreview);
    } else {
        appendMessage("user", text);
    }
    state.messages.push({ role: "user", content: text });

    textareaEl.value = "";
    textareaEl.style.height = "auto";
    charCount.textContent = "0/1000";

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
                conversation_id: state.conversationId,
                images: state.pendingImages,
                persona_id: state.personaId,
            }),
        });

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let fullText = "";
        let sources = [];
        let fileInfo = null;

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
                        if (data.conversation_id) {
                            state.conversationId = data.conversation_id;
                        }
                        fileInfo = data.file || null;
                    }
                } catch {}
            }
        }

        // Show sources
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

        // Show download link if a file was generated
        if (fileInfo) {
            const dlDiv = document.createElement("div");
            dlDiv.style.cssText = "margin-top:10px";
            dlDiv.innerHTML = `<a href="${fileInfo.url}" download="${fileInfo.filename}" class="source-tag source-link" style="padding:6px 14px;font-size:13px">Download ${fileInfo.filename}</a>`;
            aiMsgEl.appendChild(dlDiv);
        }

        state.messages.push({ role: "assistant", content: fullText });
        state.pendingImages = [];
        clearImagePreview();
        postRenderEnhance();
        if (state.ttsEnabled && fullText) speakText(fullText);
        loadConversations();
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
    state.conversationId = null;
    state.pendingImages = [];
    chatAreaEl.innerHTML = "";
    chatAreaEl.classList.remove("active");
    welcomeEl.classList.remove("hidden");
    clearImagePreview();
    textareaEl.focus();
}

// ── Markdown (rich rendering) ─────

function renderMarkdown(text) {
    if (!text) return "";

    // Use marked.js if available
    if (typeof marked !== 'undefined') {
        try {
            // Custom renderer for code blocks with copy button
            const renderer = new marked.Renderer();
            const origCode = renderer.code;
            renderer.code = function(code, lang) {
                // Mermaid diagrams
                if (lang === 'mermaid') {
                    return `<div class="mermaid">${escapeHtml(typeof code === 'object' ? code.text || '' : code)}</div>`;
                }
                const codeText = typeof code === 'object' ? code.text || '' : code;
                const codeLang = typeof code === 'object' ? code.lang || '' : (lang || '');
                let highlighted = escapeHtml(codeText);
                if (typeof hljs !== 'undefined') {
                    try {
                        highlighted = codeLang && hljs.getLanguage(codeLang)
                            ? hljs.highlight(codeText, { language: codeLang }).value
                            : hljs.highlightAuto(codeText).value;
                    } catch(e) {}
                }
                const langLabel = codeLang ? `<span class="code-lang">${codeLang}</span>` : '';
                return `<div class="code-block">${langLabel}<button class="code-copy-btn" onclick="copyCode(this)">Copy</button><pre><code class="hljs language-${codeLang}">${highlighted}</code></pre></div>`;
            };

            return marked.parse(text, { renderer: renderer, breaks: true, gfm: true });
        } catch(e) {
            console.error('marked.js error:', e);
        }
    }

    // Fallback: basic markdown
    let html = escapeHtml(text);
    html = html.replace(/```(\w*)\n([\s\S]*?)```/g, (_, lang, code) => `<pre><code>${code.trim()}</code></pre>`);
    html = html.replace(/`([^`]+)`/g, "<code>$1</code>");
    html = html.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
    html = html.replace(/\*(.+?)\*/g, "<em>$1</em>");
    html = html.replace(/^### (.+)$/gm, "<h4>$1</h4>");
    html = html.replace(/^## (.+)$/gm, "<h3>$1</h3>");
    html = html.replace(/^# (.+)$/gm, "<h2>$1</h2>");
    html = html.split("\n\n").map(p => { p=p.trim(); if(!p) return ""; if(p.startsWith("<")) return p; return `<p>${p}</p>`; }).join("");
    return html;
}

function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}

function copyCode(btn) {
    const code = btn.closest('.code-block').querySelector('code');
    navigator.clipboard.writeText(code.textContent).then(() => {
        btn.textContent = 'Copied!';
        setTimeout(() => btn.textContent = 'Copy', 1500);
    });
}

function postRenderEnhance() {
    // Render mermaid diagrams
    if (typeof mermaid !== 'undefined') {
        try {
            document.querySelectorAll('.mermaid:not([data-processed])').forEach(el => {
                el.setAttribute('data-processed', 'true');
                const id = 'mermaid-' + Math.random().toString(36).substr(2, 9);
                mermaid.render(id, el.textContent).then(({svg}) => {
                    el.innerHTML = svg;
                }).catch(() => {});
            });
        } catch(e) {}
    }

    // Render KaTeX math: $...$ and $$...$$
    if (typeof katex !== 'undefined') {
        document.querySelectorAll('.message-ai .message-content').forEach(el => {
            // Block math: $$...$$
            el.innerHTML = el.innerHTML.replace(/\$\$([\s\S]+?)\$\$/g, (_, tex) => {
                try { return katex.renderToString(tex.trim(), { displayMode: true }); }
                catch(e) { return `<code>${tex}</code>`; }
            });
            // Inline math: $...$
            el.innerHTML = el.innerHTML.replace(/\$([^\$\n]+?)\$/g, (_, tex) => {
                try { return katex.renderToString(tex.trim(), { displayMode: false }); }
                catch(e) { return `<code>${tex}</code>`; }
            });
        });
    }
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

// ── Conversation History ──────────

async function loadConversations(folderFilter) {
    try {
        let url = "/api/conversations";
        if (folderFilter) url += `?folder=${encodeURIComponent(folderFilter)}`;
        const res = await fetch(url);
        const data = await res.json();
        const container = $("#sidebar-sessions");
        if (!container) return;

        container.innerHTML = "";
        const convs = data.conversations || [];

        if (convs.length === 0) {
            container.innerHTML = '<div style="padding:12px 6px;font-size:12px;color:var(--text-muted)">No conversations yet</div>';
            return;
        }

        // Group by date
        const today = new Date().toDateString();
        const yesterday = new Date(Date.now() - 86400000).toDateString();
        let lastGroup = "";

        convs.forEach((c) => {
            const d = new Date(c.updated_at * 1000).toDateString();
            let group = "Older";
            if (d === today) group = "Today";
            else if (d === yesterday) group = "Yesterday";
            else {
                const days = Math.floor((Date.now() - c.updated_at * 1000) / 86400000);
                if (days <= 7) group = "This week";
                else if (days <= 30) group = "This month";
            }

            if (group !== lastGroup) {
                const label = document.createElement("div");
                label.className = "sidebar-label";
                label.textContent = group;
                container.appendChild(label);
                lastGroup = group;
            }

            const folderBadge = c.folder ? `<span style="font-size:10px;color:var(--text-muted);background:var(--bg-tertiary);padding:1px 6px;border-radius:3px;margin-left:4px">${escapeHtml(c.folder)}</span>` : '';

            const item = document.createElement("div");
            item.className = "session-item" + (c.id === state.conversationId ? " active" : "");
            item.innerHTML = `
                <span class="session-title" onclick="loadConversation('${c.id}')">${escapeHtml(c.title || 'New Chat')}${folderBadge}</span>
                <div class="session-actions">
                    <button class="session-action-btn" onclick="event.stopPropagation();setFolder('${c.id}')" title="Set folder">
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>
                    </button>
                    <button class="session-action-btn" onclick="event.stopPropagation();renameSession('${c.id}', this)" title="Rename">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
                    </button>
                    <button class="session-action-btn delete" onclick="event.stopPropagation();deleteConversation('${c.id}')" title="Delete">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
                    </button>
                </div>
            `;
            container.appendChild(item);
        });
    } catch {}
}

async function loadConversation(convId) {
    try {
        const res = await fetch(`/api/conversations/${convId}`);
        const conv = await res.json();
        if (!conv || !conv.messages) return;

        state.conversationId = convId;
        state.messages = [];
        chatAreaEl.innerHTML = "";
        welcomeEl.classList.add("hidden");
        chatAreaEl.classList.add("active");

        conv.messages.forEach((m) => {
            appendMessage(m.role === "user" ? "user" : "ai", m.content);
            state.messages.push({ role: m.role, content: m.content });
        });

        chatAreaEl.scrollTop = chatAreaEl.scrollHeight;
        loadConversations();
    } catch {}
}

async function deleteConversation(convId) {
    if (!confirm("Delete this conversation?")) return;
    await fetch(`/api/conversations/${convId}`, { method: "DELETE" });
    if (state.conversationId === convId) clearChat();
    loadConversations();
}

async function renameSession(convId, btnEl) {
    const sessionItem = btnEl.closest(".session-item");
    const titleEl = sessionItem.querySelector(".session-title");
    const currentTitle = titleEl.textContent;

    // Replace title with input
    const input = document.createElement("input");
    input.type = "text";
    input.className = "session-rename-input";
    input.value = currentTitle;
    titleEl.replaceWith(input);
    input.focus();
    input.select();

    const save = async () => {
        const newTitle = input.value.trim();
        if (newTitle && newTitle !== currentTitle) {
            await fetch(`/api/conversations/${convId}`, {
                method: "PATCH",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ title: newTitle }),
            });
        }
        loadConversations();
    };

    input.addEventListener("blur", save);
    input.addEventListener("keydown", (e) => {
        if (e.key === "Enter") { e.preventDefault(); input.blur(); }
        if (e.key === "Escape") { input.value = currentTitle; input.blur(); }
    });
}

async function exportConversation(format) {
    if (!state.conversationId) return;
    if (format === "md") {
        const res = await fetch(`/api/conversations/${state.conversationId}/export?format=md`);
        const data = await res.json();
        if (data.markdown) {
            const blob = new Blob([data.markdown], { type: "text/markdown" });
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = `chat_${state.conversationId}.md`;
            a.click();
            URL.revokeObjectURL(url);
        }
    } else if (format === "pdf") {
        window.open(`/api/conversations/${state.conversationId}/export?format=pdf`, "_blank");
    }
}

// ── Image Upload (Vision) ─────────

async function attachImage() {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = "image/*";

    input.onchange = async () => {
        const file = input.files[0];
        if (!file) return;

        const formData = new FormData();
        formData.append("file", file);

        try {
            const res = await fetch("/api/upload/image", { method: "POST", body: formData });
            const data = await res.json();
            if (data.status === "ok") {
                state.pendingImages = [data.base64];
                showImagePreview(data.base64, data.filename);
            }
        } catch (err) {
            console.error("Image upload failed:", err);
        }
    };
    input.click();
}

function showImagePreview(b64, filename) {
    let preview = $("#image-preview");
    if (!preview) {
        preview = document.createElement("div");
        preview.id = "image-preview";
        preview.style.cssText = "padding:4px 16px;display:flex;align-items:center;gap:8px";
        $(".input-box").prepend(preview);
    }
    preview.innerHTML = `
        <img src="data:image/jpeg;base64,${b64}" style="height:40px;border-radius:6px;border:1px solid var(--border)">
        <span style="font-size:12px;color:var(--text-muted)">${filename}</span>
        <button onclick="clearImagePreview()" style="background:none;border:none;color:var(--text-muted);cursor:pointer;font-size:14px">x</button>
    `;
}

function clearImagePreview() {
    state.pendingImages = [];
    const preview = $("#image-preview");
    if (preview) preview.remove();
}

// ── Voice Input ───────────────────

async function toggleVoice() {
    if (state.isRecording) {
        stopRecording();
    } else {
        startRecording();
    }
}

async function startRecording() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        const chunks = [];
        const recorder = new MediaRecorder(stream, { mimeType: "audio/webm" });

        recorder.ondataavailable = (e) => chunks.push(e.data);
        recorder.onstop = async () => {
            stream.getTracks().forEach((t) => t.stop());
            const blob = new Blob(chunks, { type: "audio/webm" });

            const voiceBtn = $("#voice-btn");
            if (voiceBtn) voiceBtn.textContent = "...";

            const formData = new FormData();
            formData.append("file", blob, "recording.webm");

            try {
                const res = await fetch("/api/voice/transcribe", { method: "POST", body: formData });
                const data = await res.json();
                if (data.status === "ok" && data.text) {
                    textareaEl.value = data.text;
                    textareaEl.dispatchEvent(new Event("input"));
                }
            } catch (err) {
                console.error("Transcription failed:", err);
            }

            if (voiceBtn) {
                voiceBtn.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="23"/></svg>';
            }
        };

        recorder.start();
        state.mediaRecorder = recorder;
        state.isRecording = true;

        const voiceBtn = $("#voice-btn");
        if (voiceBtn) {
            voiceBtn.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--error)" stroke-width="2"><rect x="6" y="4" width="12" height="16" rx="2"/></svg>';
        }
    } catch (err) {
        console.error("Microphone access denied:", err);
    }
}

function stopRecording() {
    if (state.mediaRecorder && state.isRecording) {
        state.mediaRecorder.stop();
        state.isRecording = false;
    }
}

// ── Templates ─────────────────────

async function openTemplatesPanel() {
    $("#templates-panel").classList.add("active");
    await loadTemplateList();
}

async function loadTemplateList() {
    try {
        const res = await fetch("/api/templates");
        const data = await res.json();
        const list = $("#template-list");
        const select = $("#template-select");
        if (!list || !select) return;

        list.innerHTML = "";
        // Keep first option
        select.innerHTML = '<option value="">Select a template...</option>';

        (data.templates || []).forEach((t) => {
            const item = document.createElement("div");
            item.className = "file-item";
            item.innerHTML = `
                <span class="file-name">${escapeHtml(t.name)} <span style="color:var(--text-muted);font-size:11px">(${t.fields} fields)</span></span>
                <button onclick="deleteTemplate('${t.id}')" style="background:none;border:none;color:var(--text-muted);cursor:pointer;font-size:12px">delete</button>
            `;
            list.appendChild(item);

            const opt = document.createElement("option");
            opt.value = t.id;
            opt.textContent = t.name;
            select.appendChild(opt);
        });
    } catch {}
}

async function uploadTemplate() {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = ".docx,.pdf,.txt,.md";

    input.onchange = async () => {
        const file = input.files[0];
        if (!file) return;

        const statusEl = $("#template-status");
        statusEl.textContent = `Analyzing ${file.name}...`;

        const formData = new FormData();
        formData.append("file", file);

        try {
            const res = await fetch("/api/templates/upload", { method: "POST", body: formData });
            const data = await res.json();

            if (data.status === "ok") {
                statusEl.textContent = `Template saved! Detected ${data.fields} fillable fields.`;
                await loadTemplateList();
            } else {
                statusEl.textContent = `Error: ${data.error}`;
            }
        } catch (err) {
            statusEl.textContent = `Upload failed: ${err.message}`;
        }
    };
    input.click();
}

async function deleteTemplate(templateId) {
    await fetch(`/api/templates/${templateId}`, { method: "DELETE" });
    await loadTemplateList();
}

async function fillTemplate(format) {
    const templateId = $("#template-select").value;
    const instructions = $("#fill-instructions").value.trim();
    const statusEl = $("#fill-status");

    if (!templateId) {
        statusEl.textContent = "Please select a template first.";
        return;
    }
    if (!instructions) {
        statusEl.textContent = "Please enter the information to fill in.";
        return;
    }

    statusEl.textContent = "AI is filling the template... (this may take a moment)";

    try {
        const res = await fetch(`/api/templates/${templateId}/fill`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                instructions: instructions,
                model: state.model,
                output_format: format === "pdf" ? ".pdf" : ".docx",
            }),
        });
        const data = await res.json();

        if (data.status === "ok" && data.url) {
            statusEl.innerHTML = `Done! <a href="${data.url}" download="${data.filename}" style="color:var(--accent);text-decoration:underline">Download ${data.filename}</a>`;
        } else {
            statusEl.textContent = `Error: ${data.message || "Generation failed"}`;
        }
    } catch (err) {
        statusEl.textContent = `Error: ${err.message}`;
    }
}

// ── Personas ──────────────────────

async function loadPersonas() {
    try {
        const res = await fetch("/api/personas");
        const data = await res.json();
        const select = $("#persona-select");
        if (!select) return;

        select.innerHTML = "";
        (data.personas || []).forEach((p) => {
            const opt = document.createElement("option");
            opt.value = p.id;
            opt.textContent = p.name;
            if (p.id === state.personaId) opt.selected = true;
            select.appendChild(opt);
        });

        select.addEventListener("change", (e) => {
            state.personaId = e.target.value;
        });
    } catch {}
}

// ── Search ────────────────────────

let searchTimeout = null;
async function searchConversations(query) {
    clearTimeout(searchTimeout);
    if (!query || query.length < 2) {
        loadConversations();
        return;
    }
    searchTimeout = setTimeout(async () => {
        try {
            const res = await fetch(`/api/conversations/search/${encodeURIComponent(query)}`);
            const data = await res.json();
            const container = $("#sidebar-sessions");
            if (!container) return;

            container.innerHTML = "";
            if (!data.results || data.results.length === 0) {
                container.innerHTML = '<div style="padding:12px 6px;font-size:12px;color:var(--text-muted)">No results found</div>';
                return;
            }

            const label = document.createElement("div");
            label.className = "sidebar-label";
            label.textContent = `${data.results.length} results`;
            container.appendChild(label);

            const seen = new Set();
            data.results.forEach((r) => {
                if (seen.has(r.conversation_id)) return;
                seen.add(r.conversation_id);
                const item = document.createElement("div");
                item.className = "session-item";
                item.innerHTML = `
                    <span class="session-title" onclick="loadConversation('${r.conversation_id}')">
                        ${escapeHtml(r.conversation_title || 'Chat')}
                        <span style="display:block;font-size:11px;color:var(--text-muted);margin-top:2px">${escapeHtml(r.content)}</span>
                    </span>
                `;
                container.appendChild(item);
            });
        } catch {}
    }, 300);
}

// ── Folders / Tags ────────────────

async function loadFolders() {
    try {
        const res = await fetch("/api/folders");
        const data = await res.json();
        const select = $("#folder-filter");
        if (!select) return;

        // Keep "All folders" option
        select.innerHTML = '<option value="">All folders</option>';
        (data.folders || []).forEach((f) => {
            const opt = document.createElement("option");
            opt.value = f;
            opt.textContent = f;
            select.appendChild(opt);
        });
    } catch {}
}

function filterByFolder(folder) {
    loadConversations(folder);
}

async function setFolder(convId) {
    const folder = prompt("Enter folder name (or leave empty to remove):", "");
    if (folder === null) return;
    try {
        await fetch(`/api/conversations/${convId}/meta`, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ folder: folder }),
        });
        loadConversations();
        loadFolders();
    } catch {}
}

async function setTags(convId) {
    const tags = prompt("Enter tags separated by commas:", "");
    if (tags === null) return;
    try {
        await fetch(`/api/conversations/${convId}/meta`, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ tags: tags }),
        });
        loadConversations();
    } catch {}
}

// ── Text-to-Speech ────────────────

function toggleTTS() {
    state.ttsEnabled = !state.ttsEnabled;
    const btn = $("#tts-btn");
    if (btn) {
        btn.style.background = state.ttsEnabled ? "var(--bg-tertiary)" : "transparent";
        btn.title = state.ttsEnabled ? "TTS On (click to turn off)" : "Read aloud";
    }
    if (!state.ttsEnabled) {
        window.speechSynthesis.cancel();
    }
}

function speakText(text) {
    if (!('speechSynthesis' in window)) return;
    window.speechSynthesis.cancel();

    // Clean markdown/code for speech
    let clean = text
        .replace(/```[\s\S]*?```/g, ' (code block) ')
        .replace(/`[^`]+`/g, '')
        .replace(/\*\*(.+?)\*\*/g, '$1')
        .replace(/\*(.+?)\*/g, '$1')
        .replace(/^#+\s*/gm, '')
        .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
        .replace(/[|_\-]{3,}/g, '')
        .trim();

    if (!clean) return;

    // Split into chunks (speechSynthesis has a ~200 char limit in some browsers)
    const chunks = clean.match(/[^.!?\n]{1,200}[.!?\n]?/g) || [clean];

    chunks.forEach((chunk, i) => {
        const utterance = new SpeechSynthesisUtterance(chunk.trim());
        utterance.rate = 1.0;
        utterance.pitch = 1.0;
        window.speechSynthesis.speak(utterance);
    });
}

// ── Boot ───────────────────────────

document.addEventListener("DOMContentLoaded", init);
