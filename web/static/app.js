// ai_runtime Web — frontend logic (vanilla JS, no build step).
// Markdown via marked + DOMPurify; syntax highlight via highlight.js.

const $ = (sel) => document.querySelector(sel);
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

// Configure Markdown renderer.
if (window.marked) {
  marked.setOptions({ breaks: true, gfm: true });
}
function renderMarkdown(text) {
  const raw = window.marked ? marked.parse(text || "") : text || "";
  const clean = window.DOMPurify ? DOMPurify.sanitize(raw) : raw;
  const tmp = document.createElement("div");
  tmp.innerHTML = clean;
  tmp.querySelectorAll("pre code").forEach((block) => {
    if (window.hljs) hljs.highlightElement(block);
  });
  return tmp.innerHTML;
}

let ws = null;
let currentSession = null;
let assistantEl = null; // current streaming assistant bubble
let assistantText = ""; // accumulated raw markdown
let managerProvider = null; // current backend provider (from /api/provider)
let managerModel = null;     // current backend model

function hideEmpty() {
  const e = $("#empty-state");
  if (e) e.classList.add("hidden");
}

// ---- Sidebar nav ----
document.querySelectorAll(".nav-btn").forEach((b) =>
  b.addEventListener("click", () => {
    document.querySelectorAll(".nav-btn").forEach((x) => x.classList.remove("active"));
    document.querySelectorAll(".panel").forEach((x) => x.classList.remove("active"));
    b.classList.add("active");
    $("#panel-" + b.dataset.panel).classList.add("active");
  })
);

// ---- Sessions ----
let sessionMeta = {}; // session_id -> { name, project, mode }

async function loadSessions(selectId = null) {
  const sessions = await api("GET", "/api/sessions");
  const list = $("#session-list");
  list.innerHTML = "";
  sessionMeta = {};
  sessions.forEach((s) => {
    sessionMeta[s.session_id] = { name: s.name, project: s.project, mode: s.mode || "chat" };
    const li = document.createElement("li");
    li.dataset.id = s.session_id;
    li.textContent = s.name;
    li.title = s.name;
    if (s.session_id === currentSession) li.classList.add("active");
    li.addEventListener("click", () => selectSession(s.session_id));
    list.appendChild(li);
  });
  if (selectId) currentSession = selectId;
  if (!currentSession && sessions.length) currentSession = sessions[0].session_id;
  highlightActiveSession();
}

function highlightActiveSession() {
  document.querySelectorAll("#session-list li").forEach((li) => {
    li.classList.toggle("active", li.dataset.id === currentSession);
  });
}

async function selectSession(id) {
  if (id === currentSession) return;
  currentSession = id;
  highlightActiveSession();
  syncModeToggle();
  connectWs();
  await loadHistory();
}

function currentMode() {
  const meta = sessionMeta[currentSession];
  return (meta && meta.mode) || "chat";
}

function syncModeToggle() {
  const btn = $("#mode-toggle");
  if (!btn) return;
  const mode = currentMode();
  btn.dataset.mode = mode;
  btn.textContent = mode === "plan" ? "Plan" : "Chat";
}

async function setMode(mode) {
  if (!currentSession) return;
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
  msgs.forEach((m) => {
    if (m.role === "user") {
      addMsg("user", m.content);
    } else if (m.plan) {
      addPlan(m.content);
    } else {
      addMsg("assistant", m.content, true);
    }
  });
}

async function newSession(project = "default") {
  // Guard against a click Event being passed as the argument.
  if (typeof project !== "string") project = "default";
  // The backend auto-creates the project from the configured default root
  // when it doesn't already exist, so no prompt is needed.
  const s = await api("POST", "/api/sessions", { project });
  currentSession = s.session_id;
  await loadSessions(s.session_id);
  connectWs();
  $("#messages").innerHTML = "";
  $("#empty-state").classList.remove("hidden");
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
    if (data.type === "error") {
      if (data.kind === "rate_limit") {
        showRateLimit(data);
      } else {
        addMsg("system", "Error: " + data.error);
      }
    } else if (data.type === "plan") {
      addPlan(data.plan);
    } else if (data.type === "done") {
      finalizeAssistant();
    } else {
      handleEvent(data);
    }
  };
}

function handleEvent(evt) {
  const type = evt.type;
  if (type === "text_delta") {
    appendAssistant(evt.delta || "");
  } else if (type === "thinking") {
    appendThinking(evt.delta || "");
  } else if (type === "tool_call") {
    const calls = evt.calls || [];
    calls.forEach((c) => addToolCard(c.name, c.arguments, false));
  } else if (type === "tool_result") {
    addToolCard(evt.name, evt.output || evt.error, !evt.success, evt.error);
  } else if (type === "usage") {
    const u = evt.usage || {};
    addMsg("system", `tokens — prompt: ${u.prompt_tokens ?? "?"} · completion: ${u.completion_tokens ?? "?"} · total: ${u.total_tokens ?? "?"}`);
  } else if (type === "completed") {
    finalizeAssistant();
  } else if (type === "error") {
    addMsg("system", "Error: " + evt.error);
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
  const send = $("#send");
  if (wrap) wrap.classList.toggle("disabled", disabled);
  if (input) input.disabled = disabled;
  if (send) send.disabled = disabled;
}

function clearRateLimit() {
  $("#rate-limit-banner").classList.add("hidden");
  setComposerDisabled(false);
}

// ---- Messages ----
function addMsg(role, html, asMarkdown = false) {
  const wrap = document.createElement("div");
  wrap.className = "msg " + role;
  const label = document.createElement("div");
  label.className = "role-label";
  label.textContent = role === "user" ? "You" : role === "assistant" ? "ai_runtime" : role === "tool" ? "Tool" : "System";
  const bubble = document.createElement("div");
  bubble.className = "bubble";
  if (asMarkdown) bubble.innerHTML = renderMarkdown(html);
  else bubble.textContent = html;
  wrap.appendChild(label);
  wrap.appendChild(bubble);
  $("#messages").appendChild(wrap);
  scrollDown();
  return wrap;
}

function appendAssistant(text) {
  hideEmpty();
  if (!assistantEl) {
    assistantEl = addMsg("assistant", "", true);
    assistantText = "";
  }
  assistantText += text;
  const bubble = assistantEl.querySelector(".bubble");
  bubble.innerHTML = renderMarkdown(assistantText);
  bubble.classList.add("cursor");
  scrollDown();
}
function finalizeAssistant() {
  if (assistantEl) {
    assistantEl.querySelector(".bubble").classList.remove("cursor");
  }
  assistantEl = null;
  assistantText = "";
}

function appendThinking(text) {
  hideEmpty();
  let box = $("#thinking-box");
  if (!box) {
    box = document.createElement("div");
    box.id = "thinking-box";
    box.className = "msg assistant";
    const label = document.createElement("div");
    label.className = "role-label";
    label.textContent = "Thinking";
    const bubble = document.createElement("div");
    bubble.className = "bubble thinking-block";
    box.appendChild(label);
    box.appendChild(bubble);
    $("#messages").appendChild(box);
  }
  box.querySelector(".bubble").textContent += text;
  scrollDown();
}

function addPlan(plan) {
  hideEmpty();
  const wrap = document.createElement("div");
  wrap.className = "msg assistant";
  const label = document.createElement("div");
  label.className = "role-label";
  label.textContent = "Plan";
  const block = document.createElement("div");
  block.className = "plan-block";
  block.textContent = plan;
  wrap.appendChild(label);
  wrap.appendChild(block);
  $("#messages").appendChild(wrap);
  scrollDown();
}

function addToolCard(name, payload, isError, errMsg) {
  hideEmpty();
  const wrap = document.createElement("div");
  wrap.className = "msg tool";
  const card = document.createElement("div");
  card.className = "tool-card" + (isError ? " error" : "");
  const head = document.createElement("div");
  head.className = "tool-head";
  head.textContent = (isError ? "✗ " : "🔧 ") + name;
  const body = document.createElement("div");
  body.className = "tool-body";
  let content = typeof payload === "string" ? payload : JSON.stringify(payload, null, 2);
  if (isError && errMsg) content += "\n" + errMsg;
  body.textContent = content;
  card.appendChild(head);
  card.appendChild(body);
  wrap.appendChild(card);
  $("#messages").appendChild(wrap);
  scrollDown();
}

function scrollDown() {
  const m = $("#messages");
  m.scrollTop = m.scrollHeight;
}

// ---- Send ----
async function send() {
  const text = $("#input").value.trim();
  if (!text) return;
  // Auto-create a session if none exists yet.
  if (!currentSession) {
    await newSession();
  }
  $("#input").value = "";
  autoResize();
  hideEmpty();

  // Slash commands.
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

  if (mode === "plan") {
    try {
      const res = await api("POST", "/api/chat", { session_id: currentSession, message: text, mode });
      addPlan(res.plan);
    } catch (e) {
      if (e.status === 429) {
        showRateLimit({ provider: managerProvider, model: managerModel });
      } else {
        addMsg("system", "Error: " + e.message);
      }
    }
    return;
  }

  // Streaming via WS.
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ message: text, mode }));
  } else if (ws && ws.readyState === WebSocket.CONNECTING) {
    // Wait briefly for the freshly opened socket, then stream.
    try {
      await waitForWsOpen();
      ws.send(JSON.stringify({ message: text, mode }));
    } catch {
      await fallbackChat(text, mode);
    }
  } else {
    await fallbackChat(text, mode);
  }
}

async function fallbackChat(text, mode) {
  try {
    const res = await api("POST", "/api/chat", { session_id: currentSession, message: text, mode });
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
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    send();
  }
});
$("#input").addEventListener("input", autoResize);
$("#new-chat").addEventListener("click", () => newSession());
$("#new-chat-rail").addEventListener("click", () => newSession());
$("#mode-toggle").addEventListener("click", () => {
  const next = currentMode() === "plan" ? "chat" : "plan";
  setMode(next);
});
document.querySelectorAll(".chip").forEach((c) =>
  c.addEventListener("click", () => {
    $("#input").value = c.textContent;
    autoResize();
    $("#input").focus();
  })
);
$("#project-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  await api("POST", "/api/projects", {
    root: $("#proj-root").value,
    name: $("#proj-name").value || undefined,
  });
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
  addMsg("system", res.ok ? "Restored last checkpoint." : "No checkpoint to restore.");
});

// Rate-limit banner actions.
$("#rl-change-provider").addEventListener("click", () => {
  document.querySelectorAll(".nav-btn").forEach((x) => x.classList.remove("active"));
  document.querySelectorAll(".panel").forEach((x) => x.classList.remove("active"));
  document.querySelector('.nav-btn[data-panel="provider"]').classList.add("active");
  $("#panel-provider").classList.add("active");
  loadProvider();
});
$("#rl-retry").addEventListener("click", () => {
  clearRateLimit();
  $("#input").focus();
});

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

// ---- Init ----
(async () => {
  await loadSessions();
  await loadProjects();
  await loadTasks();
  await loadPerms();
  await loadProvider();
  connectWs();
  syncModeToggle();
  if (currentSession) await loadHistory();
})();
