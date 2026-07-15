// Forge Web — frontend logic (vanilla JS, no build step).
// Markdown via marked + DOMPurify; syntax highlight via highlight.js; diagrams via mermaid.

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => Array.from(document.querySelectorAll(sel));
const api = async (method, path, body) => {
  const res = await fetch(path, {
    method,
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    const err = new Error(await res.text());
    err.status = res.status;
    throw err;
  }
  return res.json();
};

// ---- Global client state (Phase 0) ----
const state = {
  streaming: false,
  canStop: false,
  fontSize: 15,
};

// Element being regenerated (so streaming updates it in place, no new bubble).
let regenTargetEl = null;

// Configure Markdown renderer.
if (window.marked) {
  marked.setOptions({ breaks: true, gfm: true });
}
if (window.mermaid) {
  mermaid.initialize({ startOnLoad: false, theme: "dark", securityLevel: "strict" });
}
function renderMarkdown(text) {
  const raw = window.marked ? marked.parse(text || "") : text || "";
  const clean = window.DOMPurify ? DOMPurify.sanitize(raw) : raw;
  const tmp = document.createElement("div");
  tmp.innerHTML = clean;
  tmp.querySelectorAll("pre code").forEach((block) => {
    if (window.hljs) hljs.highlightElement(block);
  });
  // Render mermaid blocks.
  tmp.querySelectorAll("code.language-mermaid").forEach((block) => {
    const pre = block.parentElement;
    const div = document.createElement("div");
    div.className = "mermaid";
    div.textContent = block.textContent;
    pre.replaceWith(div);
    try { if (window.mermaid) mermaid.run({ nodes: [div] }); } catch {}
  });
  // Add an "open in artifact" action to fenced code blocks (Artifacts / Canvas).
  // Use data attributes + event delegation (set via innerHTML, so listeners
  // wouldn't survive otherwise).
  tmp.querySelectorAll("pre code").forEach((block) => {
    const pre = block.parentElement;
    const lang = (block.className.match(/language-(\w+)/) || [])[1] || "";
    const code = block.textContent;
    const btn = document.createElement("button");
    btn.className = "artifact-open-btn";
    btn.title = "Open in artifact panel";
    btn.textContent = "⧉ Open";
    btn.dataset.lang = lang;
    btn.dataset.code = code;
    pre.style.position = "relative";
    pre.appendChild(btn);
  });
  return tmp.innerHTML;
}

let ws = null;
let currentSession = null;
let assistantEl = null; // current streaming assistant bubble
let assistantText = ""; // accumulated raw markdown
let managerProvider = null; // current backend provider (from /api/provider)
let managerModel = null;     // current backend model
let managerCapabilities = {}; // active provider capabilities (from /api/provider)
// Settings chosen before a session exists (applied when the session is created).
let pendingSettings = { mode: "chat", reasoning_effort: null, thinking_enabled: false };
let msgCounter = 0; // assigns data-msg-id to rendered messages

function hideEmpty() {
  const e = $("#empty-state");
  if (e) e.classList.add("hidden");
}

// ---- Toasts (Phase 0) ----
function showToast(msg, type = "info") {
  const t = document.createElement("div");
  t.className = "toast " + type;
  t.textContent = msg;
  $("#toasts").appendChild(t);
  setTimeout(() => t.classList.add("show"), 10);
  setTimeout(() => {
    t.classList.remove("show");
    setTimeout(() => t.remove(), 250);
  }, 2600);
}

// ---- Sidebar nav ----
$$(".nav-btn").forEach((b) =>
  b.addEventListener("click", () => {
    $$(".nav-btn").forEach((x) => x.classList.remove("active"));
    $$(".panel").forEach((x) => x.classList.remove("active"));
    b.classList.add("active");
    $("#panel-" + b.dataset.panel).classList.add("active");
  })
);

// ---- Sessions ----
let sessionMeta = {}; // session_id -> { name, project, mode }
let totalSessionCount = 0; // all sessions, regardless of search filter

async function loadSessions(selectId = null, q = "") {
  const sessions = await api("GET", "/api/sessions" + (q ? "?q=" + encodeURIComponent(q) : ""));
  // Only track the unfiltered total so the rail stays visible during searches
  // that match nothing (keeping the search box usable).
  if (!q) totalSessionCount = sessions.length;
  const list = $("#session-list");
  list.innerHTML = "";
  sessionMeta = {};
  // Split into pinned (top) and the rest, preserving backend order within each.
  const pinned = sessions.filter((s) => s.pinned);
  const others = sessions.filter((s) => !s.pinned);

  const buildItem = (s) => {
    sessionMeta[s.session_id] = {
      name: s.name,
      project: s.project,
      mode: s.mode || "chat",
      reasoning_effort: s.reasoning_effort || null,
      thinking_enabled: !!s.thinking_enabled,
      pinned: !!s.pinned,
    };
    const li = document.createElement("li");
    li.dataset.id = s.session_id;
    li.title = s.name;
    if (s.session_id === currentSession) li.classList.add("active");
    if (s.pinned) li.classList.add("pinned");
    const nameSpan = document.createElement("span");
    nameSpan.className = "session-name";
    nameSpan.textContent = s.name;
    nameSpan.addEventListener("click", () => selectSession(s.session_id));
    const actions = document.createElement("span");
    actions.className = "sess-actions";
    const pin = document.createElement("button");
    pin.className = "session-pin" + (s.pinned ? " pinned" : "");
    pin.title = "Pin / unpin";
    pin.innerHTML = '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 17v5"/><path d="M9 10.76a2 2 0 0 1-1.11 1.79l-1.78.9A2 2 0 0 0 5 15.24V16a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-.76a2 2 0 0 0-1.11-1.79l-1.78-.9A2 2 0 0 1 15 10.76V7a1 1 0 0 1 1-1 2 2 0 0 0 0-4H8a2 2 0 0 0 0 4 1 1 0 0 1 1 1z"/></svg>';
    pin.addEventListener("click", (e) => {
      e.stopPropagation();
      api("POST", `/api/sessions/${s.session_id}/pin`, { pinned: !s.pinned }).then(() => loadSessions(currentSession));
    });
    const del = document.createElement("button");
    del.className = "session-del";
    del.title = "Delete chat";
    del.innerHTML = '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 6h18"/><path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/></svg>';
    del.addEventListener("click", (e) => {
      e.stopPropagation();
      deleteSession(s.session_id);
    });
    actions.appendChild(pin);
    actions.appendChild(del);
    li.appendChild(nameSpan);
    li.appendChild(actions);
    return li;
  };

  const addSection = (title, items) => {
    if (!items.length) return;
    const head = document.createElement("li");
    head.className = "session-section";
    head.textContent = title;
    list.appendChild(head);
    items.forEach((s) => list.appendChild(buildItem(s)));
  };

  addSection("Pinned chats", pinned);
  addSection("Chats", others);
  if (selectId) currentSession = selectId;
  if (!currentSession && sessions.length) currentSession = sessions[0].session_id;
  highlightActiveSession();
  syncSettingsToggle();
  // Keep the rail visible whenever sessions exist at all (so search stays
  // usable even when a query matches nothing). Only hide it on the unfiltered
  // view when there are genuinely no sessions.
  $("#session-rail").classList.toggle("hidden", totalSessionCount === 0);
}

function highlightActiveSession() {
  $$("#session-list li").forEach((li) => {
    li.classList.toggle("active", li.dataset.id === currentSession);
  });
}

async function selectSession(id) {
  if (id === currentSession) return;
  currentSession = id;
  highlightActiveSession();
  syncModeToggle();
  syncSettingsToggle();
  connectWs();
  await loadHistory();
}

async function deleteSession(id) {
  if (!confirm("Delete this chat? This cannot be undone.")) return;
  try {
    await api("DELETE", `/api/sessions/${id}`);
  } catch (e) {
    addMsg("system", "Error deleting chat: " + e.message);
    return;
  }
  delete sessionMeta[id];
  if (currentSession === id) {
    currentSession = null;
    if (ws) ws.close();
    $("#messages").innerHTML = "";
    $("#empty-state").classList.remove("hidden");
  }
  await loadSessions();
}

function currentMode() {
  if (currentSession && sessionMeta[currentSession]) return sessionMeta[currentSession].mode || "chat";
  return pendingSettings.mode || "chat";
}
function currentEffort() {
  if (currentSession && sessionMeta[currentSession]) return sessionMeta[currentSession].reasoning_effort || null;
  return pendingSettings.reasoning_effort || null;
}
function currentThinking() {
  if (currentSession && sessionMeta[currentSession]) return !!sessionMeta[currentSession].thinking_enabled;
  return !!pendingSettings.thinking_enabled;
}

function syncModeToggle() {
  const mode = currentMode();
  const label = $("#settings-trigger-label");
  if (label) label.textContent = mode === "plan" ? "Plan" : "Chat";
  document.querySelectorAll('.menu-item[data-menu="mode"]').forEach((b) => {
    b.setAttribute("aria-checked", String(b.dataset.value === mode));
  });
  syncStatusDisplay();
}


function syncSettingsToggle() {
  // Effort: "off" maps to null.
  const effort = currentEffort();
  const effortVal = effort || "off";
  document.querySelectorAll('.menu-item[data-menu="effort"]').forEach((b) => {
    b.setAttribute("aria-checked", String(b.dataset.value === effortVal));
  });
  // Thinking toggle.
  const on = currentThinking();
  const t = $('.menu-item[data-menu="thinking"]');
  if (t) t.setAttribute("aria-checked", String(on));
  syncThinkingAvailability();
  syncStatusDisplay();
}

// Disable the thinking toggle when the active provider doesn't support
// reasoning (e.g. groq). When unsupported, force thinking off.
function syncThinkingAvailability() {
  const supported = !!managerCapabilities.reasoning;
  const t = $('.menu-item[data-menu="thinking"]');
  if (!t) return;
  t.classList.toggle("disabled", !supported);
  t.setAttribute("aria-disabled", String(!supported));
  const hint = $("#thinking-hint");
  if (hint) hint.textContent = supported ? "" : "Not supported";
  if (!supported && currentThinking()) {
    // Force off so the indicator stays consistent with capability.
    if (currentSession) {
      setSessionSettings({ thinking_enabled: false });
    } else {
      pendingSettings.thinking_enabled = false;
    }
  }
}

async function setSessionSettings(patch) {
  // No session yet — buffer the choice and reflect it in the UI immediately.
  if (!currentSession) {
    if (patch.reasoning_effort !== undefined) pendingSettings.reasoning_effort = patch.reasoning_effort;
    if (patch.thinking_enabled !== undefined) pendingSettings.thinking_enabled = patch.thinking_enabled;
    syncSettingsToggle();
    return;
  }
  try {
    const res = await api("POST", `/api/sessions/${currentSession}/settings`, patch);
    if (sessionMeta[currentSession]) {
      if (res.reasoning_effort !== undefined)
        sessionMeta[currentSession].reasoning_effort = res.reasoning_effort;
      if (res.thinking_enabled !== undefined)
        sessionMeta[currentSession].thinking_enabled = res.thinking_enabled;
    }
    syncSettingsToggle();
  } catch {}
}

async function setMode(mode) {
  // No session yet — buffer the choice and reflect it in the UI immediately.
  if (!currentSession) {
    pendingSettings.mode = mode;
    syncModeToggle();
    return;
  }
  if (sessionMeta[currentSession]) sessionMeta[currentSession].mode = mode;
  syncModeToggle();
  try {
    await api("POST", `/api/sessions/${currentSession}/mode`, { mode });
  } catch {}
}

async function loadHistory() {
  const data = await api("GET", `/api/sessions/${currentSession}/history`);
  $("#messages").innerHTML = "";
  const msgs = data.history || [];
  if (!msgs.length) {
    $("#empty-state").classList.remove("hidden");
    return;
  }
  $("#empty-state").classList.add("hidden");
  msgs.forEach((m, idx) => renderHistoryEvent(normalizeHistoryEntry(m), idx));
}

// Map a persisted history entry (new `type`-based or legacy `role`-based)
// into the canonical event shape used by the renderer.
function normalizeHistoryEntry(m) {
  if (m && m.type) return m;
  if (!m) return { type: "text", content: "" };
  if (m.role === "user") return { type: "user", content: m.content };
  if (m.plan) return { type: "plan", content: m.content };
  return { type: "text", content: m.content };
}

// Render a single history event with the appropriate UI for its type.
// `hidx` is the entry's index in the persisted history (used for feedback).
function renderHistoryEvent(e, hidx = null) {
  if (!e) return;
  switch (e.type) {
    case "user":
      addMsg("user", e.content);
      break;
    case "text":
      addMsg("assistant", e.content, true, hidx, {
        versions: e.versions || [],
        regenerated: !!e.regenerated,
        version_index: typeof e.version_index === "number" ? e.version_index : (e.versions ? e.versions.length : 0),
      });
      break;
    case "plan":
      addPlan(e.content);
      break;
    case "thinking":
      $("#messages").appendChild(buildThinkingBlock(e.content || ""));
      break;
    case "tool_call":
      (e.calls || []).forEach((c) => $("#messages").appendChild(buildToolCallCard(c)));
      break;
    case "tool_result":
      $("#messages").appendChild(buildToolResultCard(e));
      break;
    case "usage":
      addUsageMsg(e.usage || {});
      break;
    case "error":
      addMsg("system", "Error: " + (e.error || ""));
      break;
    default:
      if (e.content != null) addMsg("assistant", e.content, true);
  }
}

async function newSession(project = "default") {
  // Guard against a click Event being passed as the argument.
  if (typeof project !== "string") project = "default";
  // The backend auto-creates the project from the configured default root
  // when it doesn't already exist, so no prompt is needed.
  // Carry over any settings the user picked before the session existed.
  const s = await api("POST", "/api/sessions", {
    project,
    mode: pendingSettings.mode,
    reasoning_effort: pendingSettings.reasoning_effort,
    thinking_enabled: pendingSettings.thinking_enabled,
  });
  currentSession = s.session_id;
  // Seed the session meta from the buffered settings so the UI stays in sync.
  sessionMeta[currentSession] = {
    name: "New chat",
    project,
    mode: pendingSettings.mode,
    reasoning_effort: pendingSettings.reasoning_effort,
    thinking_enabled: pendingSettings.thinking_enabled,
  };
  await loadSessions(s.session_id);
  connectWs();
  $("#messages").innerHTML = "";
  $("#empty-state").classList.remove("hidden");
  syncModeToggle();
  syncSettingsToggle();
}

// Auto-name a session from its first user message.
async function maybeNameSession(text) {
  const meta = sessionMeta[currentSession];
  if (meta && meta.name && meta.name !== "New chat") return;
  const name = text.trim().split("\n")[0].slice(0, 40) || "New chat";
  try {
    await api("POST", `/api/sessions/${currentSession}/rename`, { name });
    if (sessionMeta[currentSession]) sessionMeta[currentSession].name = name;
    const li = document.querySelector(`#session-list li[data-id="${currentSession}"]`);
    if (li) li.textContent = name;
  } catch {}
}

// ---- WebSocket streaming ----
function connectWs() {
  if (ws) ws.close();
  if (!currentSession) return;
  ws = new WebSocket(`ws://${location.host}/ws/${currentSession}`);
  ws.onmessage = (ev) => {
    let data;
    try {
      data = JSON.parse(ev.data);
    } catch {
      return;
    }
    // If this turn is a regeneration, target the existing assistant bubble so
    // the new response replaces it in place (no extra message bubble). Capture
    // the version list BEFORE finalizeAssistant runs so it can render the < > nav.
    if (data._action === "regenerate" && data._target != null) {
      let t = document.querySelector(`.msg[data-hidx="${data._target}"]`);
      if (!t || !t.classList.contains("assistant")) {
        // Streamed messages have no hidx; fall back to the last assistant bubble.
        t = [...document.querySelectorAll('#messages .msg.assistant:not(.plan)')].pop() || null;
      }
      regenTargetEl = t && t.classList.contains("assistant") ? t : null;
      if (regenTargetEl) {
        regenTargetEl._versions = Array.isArray(data.versions) ? data.versions.slice() : [];
        regenTargetEl._vIndex = typeof data.version_index === "number" ? data.version_index : regenTargetEl._versions.length;
      }
    }
    if (data.type === "error") {
      if (data.kind === "rate_limit") {
        showRateLimit(data);
      } else {
        addMsg("system", "Error: " + (data.error || data.message || "unknown error"));
      }
    } else if (data.type === "plan") {
      const msgs = $("#messages");
      let last = msgs.lastElementChild;
      while (last && (!last.classList.contains("assistant") || last.id === "thinking-box")) {
        last = last.previousElementSibling;
      }
      if (last) last.remove();
      finalizeAssistant();
      setStreaming(false);
      addPlan(data.plan);
    } else if (data.type === "done") {
      finalizeAssistant();
      setStreaming(false);
    } else if (data.type === "stopped") {
      finalizeAssistant();
      setStreaming(false);
      showToast("Generation stopped", "info");
    } else {
      handleEvent(data);
    }
  };
  ws.onclose = () => setStreaming(false);
}

function setStreaming(on) {
  state.streaming = on;
  state.canStop = on;
  $("#stop").classList.toggle("hidden", !on);
  $("#send").classList.toggle("hidden", on);
  updateSendState();
}

// Enable the send button only when there is text to send (and the composer
// is not disabled by a rate limit or an active stream).
function updateSendState() {
  if (state.streaming) return;
  const input = $("#input");
  const send = $("#send");
  if (!input || !send) return;
  const composer = document.querySelector(".composer");
  const rateLimited = composer && composer.classList.contains("disabled");
  const hasText = input.value.trim().length > 0;
  send.disabled = rateLimited || !hasText;
}

function handleEvent(evt) {
  const type = evt.type;
  if (type === "text_delta") {
    appendAssistant(evt.delta || "");
  } else if (type === "thinking") {
    appendThinking(evt.delta || "");
  } else if (type === "tool_call") {
    (evt.calls || []).forEach((c) => $("#messages").appendChild(buildToolCallCard(c)));
  } else if (type === "tool_result") {
    $("#messages").appendChild(buildToolResultCard(evt));
  } else if (type === "usage") {
    addUsageMsg(evt.usage || {});
  } else if (type === "completed") {
    finalizeAssistant();
  } else if (type === "error") {
    addMsg("system", "Error: " + (evt.error || evt.message || "unknown error"));
  }
}

// ---- Rate-limit handling ----
function showRateLimit(data) {
  const banner = $("#rate-limit-banner");
  const detail = $("#rl-detail");
  const who = data.provider && data.model ? `${data.provider} / ${data.model}` : "the current provider";
  detail.textContent = `Sending is paused for ${who}. Switch providers or retry after the limit resets.`;
  banner.classList.remove("hidden");
  setComposerDisabled(true);
  addMsg("system", `⚠ Rate limit reached for ${who}.`);
}
function setComposerDisabled(disabled) {
  const wrap = document.querySelector(".composer");
  const input = $("#input");
  if (wrap) wrap.classList.toggle("disabled", disabled);
  if (input) input.disabled = disabled;
  updateSendState();
}
function clearRateLimit() {
  $("#rate-limit-banner").classList.add("hidden");
  setComposerDisabled(false);
}

// ---- Messages ----
function addMsg(role, html, asMarkdown = false, hidx = null, meta = null) {
  const wrap = document.createElement("div");
  wrap.className = "msg " + role;
  wrap.dataset.msgId = String(++msgCounter);
  if (hidx !== null && hidx !== undefined) wrap.dataset.hidx = String(hidx);
  const label = document.createElement("div");
  label.className = "role-label";
  label.textContent = role === "user" ? "You" : role === "assistant" ? "Forge" : role === "tool" ? "Tool" : "System";
  const bubbleWrap = document.createElement("div");
  bubbleWrap.className = "bubble-wrap";
  const bubble = document.createElement("div");
  bubble.className = "bubble";
  if (asMarkdown) bubble.innerHTML = renderMarkdown(html);
  else bubble.textContent = html;
  bubbleWrap.appendChild(bubble);
  if (role === "assistant") {
    // Version state for regenerate (multiple regenerations allowed).
    const versions = (meta && meta.versions) ? meta.versions.slice() : [];
    const regenerated = !!(meta && meta.regenerated);
    const vIndex = (meta && typeof meta.version_index === "number") ? meta.version_index : versions.length;
    wrap.dataset.regenerated = String(regenerated);
    wrap._versions = versions;
    wrap._vIndex = vIndex;

    const copy = document.createElement("button");
    copy.className = "copy-btn";
    copy.title = "Copy message";
    copy.innerHTML = "⧉";
    copy.addEventListener("click", () => copyMessage(bubble, copy));
    bubbleWrap.appendChild(copy);

    // Action groups: feedback on the LEFT, retry + version nav on the RIGHT.
    const actionsLeft = document.createElement("div");
    actionsLeft.className = "msg-actions left";
    const up = document.createElement("button");
    up.className = "msg-action";
    up.title = "Good response";
    up.textContent = "👍";
    up.addEventListener("click", () => sendFeedback(wrap.dataset.msgId, "up"));
    const down = document.createElement("button");
    down.className = "msg-action";
    down.title = "Bad response";
    down.textContent = "👎";
    down.addEventListener("click", () => sendFeedback(wrap.dataset.msgId, "down"));
    actionsLeft.appendChild(up);
    actionsLeft.appendChild(down);

    const actionsRight = document.createElement("div");
    actionsRight.className = "msg-actions right";
    const regen = document.createElement("button");
    regen.className = "msg-action";
    regen.title = "Regenerate";
    // Inline SVG so the retry icon always renders (no missing-glyph tofu).
    regen.innerHTML = '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 12a9 9 0 1 1-3-6.7"/><path d="M21 3v5h-5"/></svg>';
    regen.addEventListener("click", () => regenerate(hidx === null ? undefined : Number(hidx)));
    actionsRight.appendChild(regen);

    bubbleWrap.appendChild(actionsLeft);
    bubbleWrap.appendChild(actionsRight);

    // Version switcher (< > arrows + count) — only when multiple responses
    // exist (the current one plus at least one stored version). Placed after
    // the regenerate button.
    const total = versions.length + 1;
    if (total > 1) {
      const nav = document.createElement("div");
      nav.className = "version-nav";
      const prev = document.createElement("button");
      prev.className = "version-btn";
      prev.textContent = "‹";
      prev.title = "Previous response";
      const count = document.createElement("span");
      count.className = "version-count";
      const next = document.createElement("button");
      next.className = "version-btn";
      next.textContent = "›";
      next.title = "Next response";
      const renderVersion = (idx) => {
        wrap._vIndex = idx;
        const v = idx === versions.length ? { content: bubble.dataset.latest || html } : versions[idx];
        bubble.innerHTML = renderMarkdown(v.content || "");
        count.textContent = `${idx + 1}/${total}`;
        prev.disabled = idx === 0;
        next.disabled = idx === versions.length;
        prev.classList.toggle("disabled", idx === 0);
        next.classList.toggle("disabled", idx === versions.length);
      };
      bubble.dataset.latest = html;
      prev.addEventListener("click", () => renderVersion(Math.max(0, wrap._vIndex - 1)));
      next.addEventListener("click", () => renderVersion(Math.min(versions.length, wrap._vIndex + 1)));
      renderVersion(vIndex);
      nav.appendChild(prev);
      nav.appendChild(count);
      nav.appendChild(next);
      actionsRight.appendChild(nav);
    }
  }
  wrap.appendChild(label);
  wrap.appendChild(bubbleWrap);
  $("#messages").appendChild(wrap);
  scrollDown();
  return wrap;
}

async function sendFeedback(msgId, feedback) {
  if (!currentSession) return;
  const el = document.querySelector(`.msg[data-msg-id="${msgId}"]`);
  // Prefer the persisted history index (data-hidx); fall back to msg counter.
  const index = el && el.dataset.hidx !== undefined ? Number(el.dataset.hidx) : Number(msgId) - 1;
  try {
    await api("POST", `/api/sessions/${currentSession}/feedback`, { index, feedback });
    showToast("Thanks for the feedback", "info");
  } catch {}
}

async function copyMessage(bubble, btn) {
  const text = bubble.innerText || bubble.textContent || "";
  try {
    await navigator.clipboard.writeText(text);
  } catch {
    const ta = document.createElement("textarea");
    ta.value = text;
    document.body.appendChild(ta);
    ta.select();
    document.execCommand("copy");
    ta.remove();
  }
  const prev = btn.innerHTML;
  btn.innerHTML = "✓";
  btn.classList.add("copied");
  setTimeout(() => {
    btn.innerHTML = prev;
    btn.classList.remove("copied");
  }, 1200);
}

function appendAssistant(text) {
  hideEmpty();
  if (!assistantEl) {
    // When regenerating, update the SAME bubble in place (no new message).
    if (regenTargetEl && regenTargetEl.isConnected) {
      assistantEl = regenTargetEl;
      // Reset version nav if present (will be re-added on finalize if needed).
      const oldNav = assistantEl.querySelector(".version-nav");
      if (oldNav) oldNav.remove();
      assistantEl.dataset.regenerated = "false";
    } else {
      assistantEl = addMsg("assistant", "", true);
    }
    assistantText = "";
  }
  assistantText += text;
  const bubble = assistantEl.querySelector(".bubble");
  bubble.dataset.latest = assistantText;
  bubble.innerHTML = renderMarkdown(assistantText);
  bubble.classList.add("cursor");
  maybeScroll();
}
function finalizeAssistant() {
  // During a regeneration the `completed` event may have already cleared
  // `assistantEl`; fall back to the regeneration target so we can still
  // finalize and render the version switcher.
  const el = assistantEl || (regenTargetEl && regenTargetEl.isConnected ? regenTargetEl : null);
  if (el) {
    const bubble = el.querySelector(".bubble");
    bubble.classList.remove("cursor");
    if (bubble.textContent.trim().endsWith("…") || bubble.textContent.trim().endsWith("...")) {
      addContinueButton(el);
    }
    // If this was a regeneration, mark the bubble and show the version switcher
    // (only when multiple responses exist). The regen button stays enabled so
    // the user can keep regenerating.
    if (regenTargetEl && el === regenTargetEl) {
      el.dataset.regenerated = "true";
      const versions = el._versions || [];
      const total = versions.length + 1;
      if (total > 1) {
        // Remove any existing navigator so we never stack two of them
        // (e.g. when `completed` and `done` both finalize the turn).
        const oldNav = el.querySelector(".version-nav");
        if (oldNav) oldNav.remove();
        const nav = document.createElement("div");
        nav.className = "version-nav";
        const prev = document.createElement("button");
        prev.className = "version-btn"; prev.textContent = "‹"; prev.title = "Previous response";
        const count = document.createElement("span");
        count.className = "version-count";
        const next = document.createElement("button");
        next.className = "version-btn"; next.textContent = "›"; next.title = "Next response";
        const renderVersion = (idx) => {
          el._vIndex = idx;
          const v = idx === versions.length ? { content: bubble.dataset.latest || "" } : versions[idx];
          bubble.innerHTML = renderMarkdown(v.content || "");
          count.textContent = `${idx + 1}/${total}`;
          prev.disabled = idx === 0; next.disabled = idx === versions.length;
          prev.classList.toggle("disabled", idx === 0);
          next.classList.toggle("disabled", idx === versions.length);
        };
        prev.addEventListener("click", () => renderVersion(Math.max(0, (el._vIndex || total - 1) - 1)));
        next.addEventListener("click", () => renderVersion(Math.min(versions.length, (el._vIndex || total - 1) + 1)));
        renderVersion(versions.length);
        nav.appendChild(prev); nav.appendChild(count); nav.appendChild(next);
        const rightGroup = el.querySelector(".msg-actions.right") || el.querySelector(".bubble-wrap");
        rightGroup.appendChild(nav);
      }
      regenTargetEl = null;
    }
  }
  assistantEl = null;
  assistantText = "";
}

function addContinueButton(el) {
  const actions = el.querySelector(".msg-actions") || (() => {
    const a = document.createElement("div");
    a.className = "msg-actions";
    el.querySelector(".bubble-wrap").appendChild(a);
    return a;
  })();
  const cont = document.createElement("button");
  cont.className = "msg-action";
  cont.textContent = "Continue ▸";
  cont.addEventListener("click", () => doContinue());
  actions.appendChild(cont);
}

function appendThinking(text) {
  hideEmpty();
  let box = $("#thinking-box");
  if (!box) {
    box = buildThinkingBlock("");
    box.id = "thinking-box";
    $("#messages").appendChild(box);
  }
  const bubble = box.querySelector(".reasoning-block");
  bubble.textContent = (bubble.textContent || "") + text;
  maybeScroll();
}

function addPlan(plan) {
  hideEmpty();
  const wrap = document.createElement("div");
  wrap.className = "msg assistant";
  wrap.dataset.msgId = String(++msgCounter);
  const label = document.createElement("div");
  label.className = "role-label";
  label.textContent = "Plan";
  const bubbleWrap = document.createElement("div");
  bubbleWrap.className = "bubble-wrap";
  const block = document.createElement("div");
  block.className = "plan-block";
  block.innerHTML = renderMarkdown(plan);
  bubbleWrap.appendChild(block);
  const copy = document.createElement("button");
  copy.className = "copy-btn";
  copy.title = "Copy plan";
  copy.innerHTML = "⧉";
  copy.addEventListener("click", () => copyMessage(block, copy));
  bubbleWrap.appendChild(copy);
  // Approve & execute (Phase 5).
  const actions = document.createElement("div");
  actions.className = "msg-actions right";
  const exec = document.createElement("button");
  exec.className = "msg-action primary";
  exec.textContent = "✓ Approve & Run";
  exec.addEventListener("click", () => executePlan(plan));
  actions.appendChild(exec);
  bubbleWrap.appendChild(actions);
  wrap.appendChild(label);
  wrap.appendChild(bubbleWrap);
  $("#messages").appendChild(wrap);
  scrollDown();
}

async function executePlan(plan) {
  showToast("Executing plan…", "info");
  await setMode("chat");
  $("#input").value = "Execute this plan:\n\n" + plan;
  autoResize();
  send();
}

function addUsageMsg(u) {
  addMsg(
    "system",
    `tokens — prompt: ${u.prompt_tokens ?? "?"} · completion: ${u.completion_tokens ?? "?"} · total: ${u.total_tokens ?? "?"}`
  );
}

// ---- Artifacts (Phase 3) ----
function openArtifact(title, html, lang) {
  const panel = $("#artifact-panel");
  const body = $("#artifact-body");
  panel.classList.remove("hidden");
  body.innerHTML = "";
  const head = document.createElement("div");
  head.className = "artifact-title";
  head.textContent = title || (lang ? lang.toUpperCase() : "Artifact");
  body.appendChild(head);
  const content = document.createElement("div");
  content.className = "artifact-content";
  if (lang === "html" || lang === "svg") {
    const iframe = document.createElement("iframe");
    iframe.className = "artifact-iframe";
    iframe.srcdoc = html;
    content.appendChild(iframe);
  } else {
    content.innerHTML = html;
    content.querySelectorAll("pre code").forEach((b) => { if (window.hljs) hljs.highlightElement(b); });
  }
  body.appendChild(content);
}

// ---- Scroll handling (Phase 1) ----
function scrollDown() {
  const m = $("#messages");
  m.scrollTop = m.scrollHeight;
}
function maybeScroll() {
  const m = $("#messages");
  const nearBottom = m.scrollHeight - m.scrollTop - m.clientHeight < 120;
  if (nearBottom) m.scrollTop = m.scrollHeight;
}
function onMessagesScroll() {
  const m = $("#messages");
  const nearBottom = m.scrollHeight - m.scrollTop - m.clientHeight < 120;
  $("#scroll-bottom").classList.toggle("hidden", nearBottom);
}
$("#messages").addEventListener("scroll", onMessagesScroll);
$("#scroll-bottom").addEventListener("click", () => {
  scrollDown();
  $("#scroll-bottom").classList.add("hidden");
});

// ---- Collapsible container (thinking / tool call / tool result) ----
function makeCollapsible(titleNode, bodyNode, collapsed = true) {
  const col = document.createElement("div");
  col.className = "collapsible";
  col.dataset.collapsed = collapsed ? "true" : "false";
  const head = document.createElement("button");
  head.className = "collapsible-head";
  head.type = "button";
  const chevron = document.createElement("span");
  chevron.className = "chevron";
  chevron.textContent = collapsed ? "▸" : "▾";
  head.appendChild(chevron);
  head.appendChild(titleNode);
  const body = document.createElement("div");
  body.className = "collapsible-body";
  body.appendChild(bodyNode);
  if (collapsed) body.style.display = "none";
  head.addEventListener("click", () => {
    const isCollapsed = col.dataset.collapsed === "true";
    col.dataset.collapsed = isCollapsed ? "false" : "true";
    chevron.textContent = isCollapsed ? "▾" : "▸";
    body.style.display = isCollapsed ? "" : "none";
  });
  col.appendChild(head);
  col.appendChild(body);
  return col;
}

// ---- Thinking block (separate, text-only reasoning bubble) ----
function buildThinkingBlock(content) {
  const wrap = document.createElement("div");
  wrap.className = "msg assistant thinking-msg";
  const label = document.createElement("div");
  label.className = "role-label";
  label.textContent = "Reasoning";
  const bubble = document.createElement("div");
  bubble.className = "reasoning-block";
  bubble.textContent = content || "";
  const title = document.createElement("span");
  title.className = "collapsible-title";
  title.textContent = "Reasoning";
  const col = makeCollapsible(title, bubble, true);
  wrap.appendChild(label);
  wrap.appendChild(col);
  return wrap;
}

// ---- Tool call card (collapsible) ----
function buildToolCallCard(call) {
  const name = call && call.name ? call.name : "tool";
  const args = call && call.arguments != null ? call.arguments : {};
  const argsStr = typeof args === "string" ? args : JSON.stringify(args, null, 2);
  const wrap = document.createElement("div");
  wrap.className = "msg tool";
  const label = document.createElement("div");
  label.className = "role-label";
  label.textContent = "Tool";
  const bubbleWrap = document.createElement("div");
  bubbleWrap.className = "bubble-wrap";
  const card = document.createElement("div");
  card.className = "tool-card";
  const head = document.createElement("div");
  head.className = "tool-head";
  head.textContent = "🔧 " + name;
  const body = document.createElement("div");
  body.className = "tool-body";
  body.textContent = argsStr;
  card.appendChild(head);
  card.appendChild(body);
  const title = document.createElement("span");
  title.className = "collapsible-title";
  title.textContent = `🔧 ${name}()`;
  const col = makeCollapsible(title, card, true);
  const copy = document.createElement("button");
  copy.className = "copy-btn";
  copy.title = "Copy arguments";
  copy.innerHTML = "⧉";
  copy.addEventListener("click", () => copyMessage(body, copy));
  bubbleWrap.appendChild(col);
  bubbleWrap.appendChild(copy);
  wrap.appendChild(label);
  wrap.appendChild(bubbleWrap);
  return wrap;
}

// ---- Tool result card (collapsible) ----
function buildToolResultCard(evt) {
  const name = evt && evt.name ? evt.name : "tool";
  const success = !(evt && evt.success === false);
  const output = evt ? (evt.output != null ? evt.output : evt.error) : "";
  const outStr = typeof output === "string" ? output : JSON.stringify(output, null, 2);
  const wrap = document.createElement("div");
  wrap.className = "msg tool";
  const label = document.createElement("div");
  label.className = "role-label";
  label.textContent = "Tool result";
  const bubbleWrap = document.createElement("div");
  bubbleWrap.className = "bubble-wrap";
  const card = document.createElement("div");
  card.className = "tool-card" + (success ? "" : " error");
  const head = document.createElement("div");
  head.className = "tool-head";
  head.textContent = (success ? "✓ " : "✗ ") + name;
  const body = document.createElement("div");
  body.className = "tool-body";
  body.textContent = outStr + (evt && evt.error && success ? "\n" + evt.error : "");
  card.appendChild(head);
  card.appendChild(body);
  const title = document.createElement("span");
  title.className = "collapsible-title";
  title.textContent = `${success ? "✓" : "✗"} ${name} result`;
  const col = makeCollapsible(title, card, true);
  const copy = document.createElement("button");
  copy.className = "copy-btn";
  copy.title = "Copy result";
  copy.innerHTML = "⧉";
  copy.addEventListener("click", () => copyMessage(body, copy));
  bubbleWrap.appendChild(col);
  bubbleWrap.appendChild(copy);
  wrap.appendChild(label);
  wrap.appendChild(bubbleWrap);
  return wrap;
}

// ---- Send / stream ----
async function send() {
  const text = $("#input").value.trim();
  if (!text) return;
  if (!currentSession) {
    await newSession();
  }
  $("#input").value = "";
  autoResize();
  updateSendState();
  hideEmpty();

  if (text.startsWith("/")) {
    const [cmd] = text.slice(1).split(" ");
    const res = await api("POST", `/api/commands/${cmd}`, { session_id: currentSession });
    addMsg("system", res.prompt || JSON.stringify(res));
    return;
  }

  const mode = currentMode();
  addMsg("user", text);
  await maybeNameSession(text);
  clearRateLimit();
  const atts = attachments.slice();
  attachments = [];
  renderAttachments();
  streamMessage(text, mode, "send", atts);
}

function streamMessage(text, mode, action, atts = []) {
  const payload = { action, message: text, mode, reasoning_effort: currentEffort() };
  if (atts && atts.length) payload.attachments = atts;
  if (ws && ws.readyState === WebSocket.OPEN) {
    setStreaming(true);
    ws.send(JSON.stringify(payload));
  } else if (ws && ws.readyState === WebSocket.CONNECTING) {
    waitForWsOpen().then(() => {
      setStreaming(true);
      ws.send(JSON.stringify(payload));
    }).catch(() => fallbackChat(text, mode, atts));
  } else {
    fallbackChat(text, mode, atts);
  }
}

async function regenerate(targetHidx = null) {
  if (!currentSession) return;
  // Resolve the target bubble. Streamed messages have no hidx, so fall back
  // to the last assistant bubble in the DOM.
  let targetEl = null;
  if (targetHidx !== null) {
    targetEl = document.querySelector(`.msg[data-hidx="${targetHidx}"]`);
  } else {
    targetEl = [...document.querySelectorAll('#messages .msg.assistant:not(.plan)')].pop() || null;
  }
  // Target the existing bubble so streaming updates it in place (no new bubble).
  regenTargetEl = targetEl && targetEl.classList.contains("assistant") ? targetEl : null;
  if (ws && ws.readyState === WebSocket.OPEN) {
    setStreaming(true);
    const payload = { action: "regenerate", mode: currentMode(), reasoning_effort: currentEffort() };
    if (targetHidx !== null) payload.target = targetHidx;
    ws.send(JSON.stringify(payload));
  } else {
    showToast("Connect to a session to regenerate", "error");
  }
}

async function doContinue() {
  if (!currentSession) return;
  if (ws && ws.readyState === WebSocket.OPEN) {
    setStreaming(true);
    ws.send(JSON.stringify({ action: "continue", mode: currentMode(), reasoning_effort: currentEffort() }));
  }
}

async function fallbackChat(text, mode, atts = []) {
  try {
    const res = await api("POST", "/api/chat", { session_id: currentSession, message: text, mode, attachments: atts });
    if (mode === "plan") addPlan(res.plan);
    else addMsg("assistant", res.content, true);
  } catch (e) {
    if (e.status === 429) {
      showRateLimit({ provider: managerProvider, model: managerModel });
    } else {
      addMsg("system", "Error: " + e.message);
    }
  }
}

function waitForWsOpen(timeoutMs = 3000) {
  return new Promise((resolve, reject) => {
    if (ws && ws.readyState === WebSocket.OPEN) return resolve();
    if (!ws) return reject(new Error("no ws"));
    const t = setTimeout(() => reject(new Error("ws timeout")), timeoutMs);
    ws.addEventListener("open", () => {
      clearTimeout(t);
      resolve();
    }, { once: true });
    ws.addEventListener("error", () => {
      clearTimeout(t);
      reject(new Error("ws error"));
    }, { once: true });
  });
}

// ---- Projects ----
async function loadProjects() {
  const projects = await api("GET", "/api/projects");
  const ul = $("#project-list");
  ul.innerHTML = "";
  projects.forEach((p) => {
    const li = document.createElement("li");
    li.textContent = `${p.name} — ${p.root} — tools: ${p.tools.join(", ")}`;
    ul.appendChild(li);
  });
}

// ---- Tasks ----
async function loadTasks() {
  const tasks = await api("GET", "/api/tasks");
  const ul = $("#task-list");
  ul.innerHTML = "";
  tasks.forEach((t) => {
    const li = document.createElement("li");
    li.textContent = `${t.id}: ${t.status}` + (t.result ? " → " + t.result : "");
    ul.appendChild(li);
  });
}

// ---- Permissions ----
async function loadPerms() {
  $("#perm-list").innerHTML = "<li>Add a rule below to enforce allow/deny/ask.</li>";
}

// ---- Provider ----
async function loadProvider() {
  try {
    const p = await api("GET", "/api/provider");
    managerProvider = p.provider;
    managerModel = p.model;
    managerCapabilities = p.capabilities || {};
    const sel = $("#prov-provider");
    sel.innerHTML = "";
    (p.providers || []).forEach((name) => {
      const opt = document.createElement("option");
      opt.value = name;
      opt.textContent = name;
      if (name === p.provider) opt.selected = true;
      sel.appendChild(opt);
    });
    $("#prov-model").value = p.model || "";
    $("#prov-base").value = p.base_url || "";
    $("#prov-reasoning").value = p.reasoning_effort || "";
    syncModelDisplay();
  } catch {}
}

// ---- Composer helpers ----
function autoResize() {
  const el = $("#input");
  el.style.height = "auto";
  el.style.height = Math.min(el.scrollHeight, 200) + "px";
}

// ---- Wire up ----
$("#send").addEventListener("click", send);
$("#input").addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); }
});
$("#input").addEventListener("input", () => { autoResize(); updateSendState(); });
const startNewChat = () => {
  currentSession = null;
  // New chats default to medium effort; thinking is on when the provider
  // advertises reasoning support (e.g. Anthropic), otherwise off.
  const thinkingSupported = !!managerCapabilities.reasoning;
  pendingSettings = {
    mode: "chat",
    reasoning_effort: "medium",
    thinking_enabled: thinkingSupported,
  };
  if (ws) ws.close();
  $("#messages").innerHTML = "";
  $("#empty-state").classList.remove("hidden");
  highlightActiveSession();
  syncModeToggle();
  syncSettingsToggle();
};
$("#new-chat-nav").addEventListener("click", startNewChat);
// Claude-style settings menu (Mode / Effort / Thinking).
const settingsTrigger = $("#settings-trigger");
const settingsMenu = $("#settings-menu");
function syncModelDisplay() {
  const name = $("#menu-model-name");
  const prov = $("#menu-model-provider");
  if (name) name.textContent = managerModel || "—";
  if (prov) prov.textContent = managerProvider ? "via " + managerProvider : "";
  syncStatusDisplay();
}
function syncStatusDisplay() {
  const sllm = $("#status-llm");
  const smode = $("#status-mode");
  const se = $("#status-effort");
  const st = $("#status-thinking");
  if (sllm) {
    const prov = managerProvider || "—";
    const model = managerModel || "—";
    sllm.textContent = prov + "/" + model;
  }
  if (smode) smode.textContent = currentMode() === "plan" ? "Plan" : "Chat";
  if (se) {
    const effort = currentEffort();
    const label = effort ? effort.charAt(0).toUpperCase() + effort.slice(1) : "Off";
    se.textContent = label;
    se.dataset.on = String(!!effort);
  }
  if (st) {
    const thinking = currentThinking();
    st.textContent = thinking ? "On" : "Off";
    st.dataset.on = String(thinking);
  }
}
function openSettingsMenu() {
  syncModelDisplay();
  settingsMenu.classList.remove("hidden");
  settingsTrigger.setAttribute("aria-expanded", "true");
}
function closeSettingsMenu() {
  settingsMenu.classList.add("hidden");
  settingsTrigger.setAttribute("aria-expanded", "false");
}
settingsTrigger.addEventListener("click", (e) => {
  e.stopPropagation();
  if (settingsMenu.classList.contains("hidden")) openSettingsMenu();
  else closeSettingsMenu();
});
const settingsWrap = document.querySelector(".settings-wrap");
// Close on outside click / Escape.
document.addEventListener("click", (e) => {
  if (!settingsMenu.classList.contains("hidden") && !settingsWrap.contains(e.target)) closeSettingsMenu();
});
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && !settingsMenu.classList.contains("hidden")) closeSettingsMenu();
});

$$('.menu-item[data-menu="mode"]').forEach((b) =>
  b.addEventListener("click", () => {
    setMode(b.dataset.value);
    closeSettingsMenu();
  })
);
$$('.menu-item[data-menu="effort"]').forEach((b) =>
  b.addEventListener("click", () => {
    const val = b.dataset.value;
    const next = val === "off" ? null : val;
    setSessionSettings({ reasoning_effort: next });
    closeSettingsMenu();
  })
);
$('.menu-item[data-menu="thinking"]').addEventListener("click", () => {
  if (!managerCapabilities.reasoning) return; // unsupported — ignore
  setSessionSettings({ thinking_enabled: !currentThinking() });
  closeSettingsMenu();
});
$$(".chip").forEach((c) =>
  c.addEventListener("click", () => {
    $("#input").value = c.textContent;
    autoResize();
    $("#input").focus();
  })
);
$("#project-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  await api("POST", "/api/projects", { root: $("#proj-root").value, name: $("#proj-name").value || undefined });
  await loadProjects();
});
$("#submit-task").addEventListener("click", async () => {
  if (!currentSession) await newSession();
  await api("POST", "/api/tasks", { session_id: currentSession, message: $("#task-msg").value });
  await loadTasks();
});
$("#refresh-tasks").addEventListener("click", loadTasks);
$("#perm-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  await api("POST", "/api/permissions", {
    project: $("#perm-project").value,
    tool: $("#perm-tool").value,
    params: $("#perm-params").value || "*",
    decision: $("#perm-decision").value,
  });
  const li = document.createElement("li");
  li.textContent = `Added: ${$("#perm-tool").value} → ${$("#perm-decision").value}`;
  $("#perm-list").prepend(li);
});
$("#btn-undo").addEventListener("click", async () => {
  const res = await fetch("/api/checkpoints/restore", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: currentSession }),
  });
  showToast(res.ok ? "Restored last checkpoint." : "No checkpoint to restore.", res.ok ? "info" : "error");
});

// Stop generation (Phase 1).
$("#stop").addEventListener("click", () => {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ action: "stop" }));
    setStreaming(false);
  }
});

// Rate-limit banner actions.
$("#rl-change-provider").addEventListener("click", () => {
  $$(".nav-btn").forEach((x) => x.classList.remove("active"));
  $$(".panel").forEach((x) => x.classList.remove("active"));
  document.querySelector('.nav-btn[data-panel="provider"]').classList.add("active");
  $("#panel-provider").classList.add("active");
  loadProvider();
});
$("#rl-retry").addEventListener("click", () => { clearRateLimit(); $("#input").focus(); });

// Provider switch form.
$("#provider-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const msg = $("#provider-msg");
  msg.className = "provider-msg";
  msg.textContent = "Switching…";
  try {
    const res = await api("POST", "/api/provider", {
      provider: $("#prov-provider").value,
      model: $("#prov-model").value,
      api_key: $("#prov-key").value || undefined,
      base_url: $("#prov-base").value || undefined,
      reasoning_effort: $("#prov-reasoning").value || undefined,
    });
    managerProvider = res.provider;
    managerModel = res.model;
    msg.className = "provider-msg ok";
    msg.textContent = `Switched to ${res.provider} / ${res.model}.`;
    clearRateLimit();
  } catch (err) {
    msg.className = "provider-msg err";
    msg.textContent = "Switch failed: " + err.message;
  }
});

// Integrations (Phase 5).
$("#mcp-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  if (!currentSession) { showToast("Open a chat first", "error"); return; }
  const msg = $("#mcp-msg");
  msg.className = "provider-msg";
  msg.textContent = "Connecting…";
  try {
    const res = await api("POST", "/api/mcp/connect", {
      session_id: currentSession,
      command: $("#mcp-command").value,
      args: $("#mcp-args").value.split(/\s+/).filter(Boolean),
    });
    msg.className = "provider-msg ok";
    msg.textContent = "Connected: " + (res.tools || []).join(", ");
  } catch (err) {
    msg.className = "provider-msg err";
    msg.textContent = "Failed: " + err.message;
  }
});
$("#subagent-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  if (!currentSession) { showToast("Open a chat first", "error"); return; }
  const msg = $("#subagent-msg");
  msg.className = "provider-msg";
  msg.textContent = "Adding…";
  try {
    await api("POST", "/api/subagents", {
      session_id: currentSession,
      name: $("#sub-name").value,
      task_template: $("#sub-task").value || "{task}",
    });
    msg.className = "provider-msg ok";
    msg.textContent = "Sub-agent added.";
  } catch (err) {
    msg.className = "provider-msg err";
    msg.textContent = "Failed: " + err.message;
  }
});

// Session search (Phase 4).
// Search chats by name AND message history (backend searches both).
let _searchTimer = null;
$("#session-search").addEventListener("input", (e) => {
  const q = e.target.value.trim();
  clearTimeout(_searchTimer);
  _searchTimer = setTimeout(() => loadSessions(currentSession, q), 150);
});

// Export (Phase 4).
$("#export-btn").addEventListener("click", () => {
  if (!currentSession) return;
  window.open(`/api/sessions/${currentSession}/export?format=markdown`, "_blank");
});

// Artifact close.
$("#artifact-close").addEventListener("click", () => $("#artifact-panel").classList.add("hidden"));

// Open a fenced code block in the artifact panel (event delegation, since the
// buttons are injected via innerHTML and lose their own listeners).
document.addEventListener("click", (e) => {
  const btn = e.target.closest(".artifact-open-btn");
  if (!btn) return;
  const lang = btn.dataset.lang || "";
  const code = btn.dataset.code || "";
  openArtifact(lang ? lang.toUpperCase() : "Code", code, lang);
});

// ---- Attachments (Phase 2) ----
let attachments = [];
function renderAttachments() {
  const box = $("#attachments");
  box.innerHTML = "";
  if (!attachments.length) { box.classList.add("hidden"); return; }
  box.classList.remove("hidden");
  attachments.forEach((a, i) => {
    const chip = document.createElement("div");
    chip.className = "attach-chip";
    chip.textContent = "📎 " + a.name;
    const x = document.createElement("button");
    x.textContent = "✕";
    x.addEventListener("click", () => { attachments.splice(i, 1); renderAttachments(); });
    chip.appendChild(x);
    box.appendChild(chip);
  });
}
$("#attach-btn").addEventListener("click", () => $("#file-input").click());
$("#file-input").addEventListener("change", (e) => {
  for (const f of e.target.files) attachments.push({ name: f.name, size: f.size });
  renderAttachments();
  e.target.value = "";
});

// ---- Theme (light / dark) ----
function applyTheme(theme) {
  document.documentElement.dataset.theme = theme;
  const btn = $("#theme-toggle");
  if (btn) btn.textContent = theme === "light" ? "☀️" : "🌙";
  const sel = $("#set-theme");
  if (sel) sel.value = theme;
  try { localStorage.setItem("ai-runtime-theme", theme); } catch {}
}
function initTheme() {
  let theme = "dark";
  try { theme = localStorage.getItem("ai-runtime-theme") || "dark"; } catch {}
  applyTheme(theme);
}
$("#theme-toggle").addEventListener("click", () => {
  const next = document.documentElement.dataset.theme === "light" ? "dark" : "light";
  applyTheme(next);
});

// ---- Settings (Phase 6) ----
function applyFontSize(px) {
  state.fontSize = px;
  document.documentElement.style.setProperty("--font-size", px + "px");
  try { localStorage.setItem("ai-runtime-font", String(px)); } catch {}
}
function initSettings() {
  let fs = 15;
  try { fs = Number(localStorage.getItem("ai-runtime-font") || 15); } catch {}
  applyFontSize(fs);
  const fsel = $("#set-font");
  if (fsel) fsel.value = String(fs);
  const msel = $("#set-mode");
  if (msel) msel.value = pendingSettings.mode;
  const esel = $("#set-effort");
  if (esel) esel.value = pendingSettings.reasoning_effort || "";
  const tchk = $("#set-thinking");
  if (tchk) tchk.checked = pendingSettings.thinking_enabled;
}
$("#set-theme").addEventListener("change", (e) => applyTheme(e.target.value));
$("#set-font").addEventListener("change", (e) => applyFontSize(Number(e.target.value)));
$("#set-mode").addEventListener("change", (e) => { pendingSettings.mode = e.target.value; syncModeToggle(); });
$("#set-effort").addEventListener("change", (e) => { pendingSettings.reasoning_effort = e.target.value || null; syncSettingsToggle(); });
$("#set-thinking").addEventListener("change", (e) => { pendingSettings.thinking_enabled = e.target.checked; syncSettingsToggle(); });

// ---- Command palette (Phase 6) ----
const PALETTE_COMMANDS = [
  { label: "New chat", run: () => startNewChat() },
  { label: "Toggle theme", run: () => $("#theme-toggle").click() },
  { label: "Chat mode", run: () => setMode("chat") },
  { label: "Plan mode", run: () => setMode("plan") },
  { label: "Toggle thinking", run: () => setSessionSettings({ thinking_enabled: !currentThinking() }) },
  { label: "Export conversation", run: () => $("#export-btn").click() },
  { label: "Clear context (/clear)", run: () => runSlash("clear") },
  { label: "Compact context (/compact)", run: () => runSlash("compact") },
];
async function runSlash(name) {
  if (!currentSession) await newSession();
  try {
    const res = await api("POST", `/api/commands/${name}`, { session_id: currentSession });
    showToast(res.prompt || (name + " done"), "info");
    if (name === "clear") { $("#messages").innerHTML = ""; $("#empty-state").classList.remove("hidden"); }
  } catch (e) { showToast("Error: " + e.message, "error"); }
}
function openPalette() {
  const p = $("#palette");
  p.classList.remove("hidden");
  $("#palette-input").value = "";
  renderPalette("");
  $("#palette-input").focus();
}
function renderPalette(q) {
  const list = $("#palette-list");
  list.innerHTML = "";
  PALETTE_COMMANDS.filter((c) => c.label.toLowerCase().includes(q.toLowerCase())).forEach((c) => {
    const li = document.createElement("li");
    li.textContent = c.label;
    li.addEventListener("click", () => { c.run(); closePalette(); });
    list.appendChild(li);
  });
}
function closePalette() { $("#palette").classList.add("hidden"); }
$("#palette-input").addEventListener("input", (e) => renderPalette(e.target.value));
$("#palette").addEventListener("click", (e) => { if (e.target.id === "palette") closePalette(); });

// ---- Keyboard shortcuts (Phase 6) ----
document.addEventListener("keydown", (e) => {
  const mod = e.metaKey || e.ctrlKey;
  if (mod && e.key === "k") { e.preventDefault(); openPalette(); }
  else if (mod && e.key === "Enter") { e.preventDefault(); send(); }
  else if (e.key === "Escape" && !$("#palette").classList.contains("hidden")) closePalette();
  else if (e.key === "Escape" && state.streaming) { $("#stop").click(); }
});

// ---- Init ----
(async () => {
  initTheme();
  initSettings();
  await loadSessions();
  await loadProjects();
  await loadTasks();
  loadPerms();
  await loadProvider();
  // Apply new-chat defaults for the pre-session state (medium effort,
  // thinking on when the provider supports reasoning).
  if (!currentSession) {
    const thinkingSupported = !!managerCapabilities.reasoning;
    pendingSettings = {
      mode: "chat",
      reasoning_effort: "medium",
      thinking_enabled: thinkingSupported,
    };
  }
  connectWs();
  syncModeToggle();
  syncSettingsToggle();
  updateSendState();
  if (currentSession) await loadHistory();
})();
