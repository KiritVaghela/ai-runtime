# UI/UX & Feature Gap Analysis — `ai_runtime` Web App vs Claude.ai & ChatGPT

> Goal: Review the current `ai_runtime` web app, compare it against Claude.ai and ChatGPT chat
> experiences, enumerate UI/UX and feature gaps, and produce a detailed, executable improvement plan.

---

## 1. Current State Snapshot (as built)

**Layout**
- Left **sidebar**: brand + theme toggle, nav (Chat / Projects / Tasks / Permissions / Provider), Undo button.
- Center **chat area**: `#messages`, empty-state with suggestion chips, rate-limit banner, composer (textarea + send), composer-hint row (mode toggle, effort segmented control, thinking toggle, hint text).
- Right **session rail**: list of sessions with rename-on-first-message, delete (🗑), `+` new chat. Hidden when no sessions.

**Capabilities already implemented**
- Lazy session creation (only on first message); per-session `mode` / `reasoning_effort` / `thinking_enabled` (with pre-session "pending settings" buffer).
- Streaming over WebSocket: `text_delta`, `thinking`, `tool_call`, `tool_result`, `usage`, `completed`, `error`, `plan`.
- Structured history replay: assistant text (markdown), plan block, collapsible thinking, collapsible tool-call/result cards, per-message usage footer.
- Copy button on every assistant/plan/thinking/tool block (always visible, top-right); 👍/👎 feedback stored in history; ↻ regenerate on assistant messages.
- Stop / interrupt streaming (composer Stop button → WS `stop` cancels the runner task); global "generating" spinner; "Continue" when `finish_reason === "length"`.
- Scroll-to-bottom floating button when scrolled up; auto-scroll on new content unless user scrolled up.
- Light/dark theme toggle (persisted in `localStorage`); font-size setting.
- Artifacts / Canvas side panel (`#artifact-panel`) for code/HTML/SVG; Mermaid diagram rendering via `mermaid.run`.
- Attachments: paperclip + drag-drop with preview chips (multimodal gated by provider capability).
- Session rail: search filter, pin/unpin (📌), delete, export (Markdown/JSON download).
- Provider switching (panel), background tasks, permission rules, slash commands (`/compact`, `/clear`), checkpoints (Undo + restore), rate-limit banner.
- Integrations panel wiring `/api/mcp/connect` and `/api/subagents`; Plan mode "Approve & Run".
- Command palette (Cmd/Ctrl+K), keyboard shortcuts (Cmd+Enter send, Esc stop/close), toasts for non-content events.
- Mobile responsive: sidebar slide-over and fixed rails < 768px.
- Backend: `web/app.py` (FastAPI) + `web/managers.py` (`Manager`/`Session`), sessions persisted to `.ai-runtime/sessions/<id>.json`.

**Implementation status (as of 2026-07-15)**
- Phases 0–6 are largely complete. Fully done: A1–A7, B1, B3, B4, C1–C2, C5, D1–D4, E3, E5, F1–F2, F4–F5.
- Partial: D2 (pin only, no folders), E2 (static tool cards, no live progress), E4 (undo/restore, no timeline), F6 (basic empty-state, no friendly error illustrations).
- Not yet implemented: A3 (edit sent user message), B2 (composer model/effort quick-switch), D5 (bulk select/delete + reorder), E1 (live agent activity timeline), F3 (accessibility: aria/roles/`role="log"`/`prefers-reduced-motion`/high-contrast), plus matrix items Edit-user-msg, Composer-model-picker, Custom-instructions/memory.

**Key files**
- `web/static/index.html`, `web/static/app.js`, `web/static/styles.css`
- `web/app.py`, `web/managers.py`

---

## 2. Comparison Matrix

| Capability | ai_runtime | Claude.ai | ChatGPT | Gap | Status |
|---|---|---|---|---|---|
| Message actions (copy) | ✅ copy + 👍👎 + retry | ✅ copy + thumbs + retry | ✅ copy + thumbs + retry | feedback/regenerate now present | ✅ Done |
| Stop / interrupt generation | ✅ Stop button | ✅ | ✅ | parity | ✅ Done |
| Edit / rewrite sent user msg | ❌ | ✅ | ✅ | Missing | ❌ TODO |
| Regenerate response | ✅ ↻ on assistant msg | ✅ | ✅ | parity | ✅ Done |
| Attachments / file upload | ✅ paperclip + drag-drop chips | ✅ images/docs | ✅ images/docs/code | UI only (multimodal gated by capability) | ✅ Done (UI) |
| Model picker in composer | ❌ (Provider panel only) | ✅ | ✅ | Missing quick switch | ❌ TODO |
| Artifacts / Canvas side panel | ✅ `#artifact-panel` | ✅ | ✅ | parity | ✅ Done |
| Diagram (Mermaid) rendering | ✅ mermaid.run | partial | ✅ | parity | ✅ Done |
| Conversation search | ✅ filter in rail | ✅ | ✅ | parity | ✅ Done |
| Folders / pin / star sessions | 📌 pin only (no folders) | ✅ projects | ✅ folders | pin done, folder missing | 🟡 Partial |
| Export / share conversation | ✅ Markdown/JSON download | ✅ | ✅ | parity | ✅ Done |
| "Scroll to bottom" when scrolled up | ✅ floating button | ✅ | ✅ | parity | ✅ Done |
| Generating / thinking indicator | ✅ spinner + Stop + thinking block | ✅ spinner | ✅ spinner | parity | ✅ Done |
| Mobile responsive | ✅ sidebar slide-over < 768px | ✅ | ✅ | parity | ✅ Done |
| Keyboard shortcuts | ✅ Cmd+K palette, Cmd+Enter, Esc | ✅ | ✅ | parity | ✅ Done |
| Accessibility (aria/focus) | minimal | ✅ | ✅ | Partial | ❌ TODO |
| Continue / resume truncated | ✅ "Continue" on `length` | ✅ | ✅ | parity | ✅ Done |
| Conversation branching | ❌ | ❌ | ❌ | N/A (parity) | ➖ N/A |
| Custom instructions / memory | ❌ | ✅ | ✅ | Missing | ❌ TODO |
| Token cost tracking | ✅ per-message usage footer | ✅ per msg | ✅ per msg | parity | ✅ Done |
| MCP / subagent management UI | ✅ Integrations panel | n/a | n/a | agentic edge | ✅ Done |
| Checkpoint / version history UI | 🟰 Undo + restore (no timeline) | n/a | n/a | restore done, timeline missing | 🟡 Partial |

---

## 3. Gap Analysis (categorized)

### A. Core Chat UX (highest impact, parity with both)
- **A1. Stop / interrupt streaming** — ✅ Done (composer Stop → WS `stop` cancels runner task).
- **A2. Regenerate response** — ✅ Done (↻ button re-streams last user message). *Verified end-to-end 2026-07-15: fixed legacy `role`-based history not being recognized (backend now handles both `type` and `role` schemas) and added the missing `done` event so the assistant bubble finalizes.*
- **A3. Edit user message** — ❌ TODO (click-to-edit a sent user bubble, resend).
- **A4. Message feedback** — ✅ Done (👍/👎 stored in history). *Verified 2026-07-15: fixed 422 (backend `FeedbackReq.session_id` made optional) and wrong index mapping (frontend now passes the persisted history index via `data-hidx`).*
- **A5. Global "generating" indicator** — ✅ Done (spinner + Stop + thinking block).
- **A6. Scroll-to-bottom button** — ✅ Done (floating button when scrolled up > 200px).
- **A7. Continue / resume** — ✅ Done ("Continue" on `finish_reason === "length"`).

### B. Composer & Input
- **B1. File / image attachment** — ✅ Done (paperclip + drag-drop chips; multimodal gated by capability). *Verified 2026-07-15: attachments are now transmitted over the WS `send`/`regenerate`/`continue` actions and persisted as `attachments` on the user history entry.*
- **B2. In-composer model/effort quick switch** — ❌ TODO (dropdown next to send; today only in Provider panel).
- **B3. Slash-command palette** — ✅ Done (Cmd/Ctrl+K palette lists commands).
- **B4. Composer toolbar** — ✅ Done (attach + mode/effort/thinking grouped above textarea).

### C. Rendering & Output
- **C1. Artifacts / Canvas side panel** — ✅ Done (`#artifact-panel` for code/HTML/SVG). *Verified 2026-07-15: each fenced code block gets an "Open" button wired via event delegation (was defined-but-unreachable before).*
- **C2. Mermaid / diagram rendering** — ✅ Done (`mermaid.run` on `code.language-mermaid`).
- **C3. Syntax highlighting** — ✅ Done (highlight.js + copy-per-block).
- **C4. Inline code execution preview** (agentic) — 🟡 Partial (`.diff-view` CSS exists; not yet auto-detected from tool results/patches).
- **C5. Rich token/usage per message** — ✅ Done (usage footer under each assistant message).

### D. Session / Conversation Management
- **D1. Conversation search** — ✅ Done (filter input in rail). *Verified 2026-07-15: backend now searches message **history** (not just session names) and the frontend queries it; rail stays visible on no-match. Removed a duplicate `/api/sessions` route that shadowed the search param.*
- **D2. Folders / pin / star** — 🟡 Partial (pin/unpin done; folders not implemented).
- **D3. Rename inline** — ✅ Done (auto-named from first message; explicit rename via API + rail).
- **D4. Export / share** — ✅ Done (Markdown/JSON download via blob).
- **D5. Bulk select + delete**, drag-reorder — ❌ TODO.
- **D6. "New chat" empty-state personalization** — ✅ Done (greeting + suggestion chips).

### E. Agentic-specific (unique edge vs consumer chat)
- **E1. Live agent activity timeline** — ❌ TODO (step list with status, collapsible, real time).
- **E2. Tool progress UI** — 🟡 Partial (static tool cards; no live running/done/duration states).
- **E3. MCP / subagent management UI** — ✅ Done (Integrations panel wires both endpoints).
- **E4. Checkpoint timeline UI** — 🟡 Partial (Undo + restore; no visual timeline/compare).
- **E5. Plan mode enhancements** — ✅ Done ("Approve & Run" executes plan in chat mode).

### F. Polish & Platform
- **F1. Mobile responsive** — ✅ Done (sidebar slide-over + fixed rails < 768px).
- **F2. Keyboard shortcuts** — ✅ Done (Cmd/Ctrl+K, Cmd+Enter, Esc).
- **F3. Accessibility** — ❌ TODO (aria roles, focus traps, `role="log"`, `prefers-reduced-motion`, high-contrast).
- **F4. Settings page** — ✅ Done (theme, font size, mode/effort/thinking).
- **F5. Toasts / notifications** — ✅ Done (non-blocking toasts for save/delete/errors).
- **F6. Empty/error states** — 🟡 Partial (empty-state exists; no friendly error illustrations/retry).

---

## 4. Detailed Execution Plan (phased)

### Phase 0 — Foundation (no new features, enables everything)
- [x] Add a small **client state module** in `app.js`: `state = { streaming, canStop, activeSession, ui: {theme, fontSize} }`.
- [x] Add **toast utility** (`showToast(msg, type)`) replacing ad-hoc system messages for non-content events.
- [x] Centralize **event bus** already exists (`web/eventing/bus.py`) — expose a JS hook for UI events if needed.
- [x] Add **`data-msg-id`** to every rendered message so actions can target specific turns.

### Phase 1 — Core Chat Parity (P0, do first)
1. [x] **A1 Stop button** — `app.js`: track `ws` stream; show Stop in composer while `state.streaming`; send `{"type":"stop"}` (add WS handler in `app.py` to cancel the runner via `asyncio.Task` cancellation). Backend: wrap `session.runner.stream(...)` in a task stored on the session; on stop, cancel it.
2. [x] **A5 Generating indicator** — spinner in composer + disable send while streaming; reuse thinking block for reasoning.
3. [x] **A2 Regenerate** — button on assistant messages → calls `POST /api/chat` or re-streams last user message (new backend route or reuse WS with a `regenerate:true` flag).
4. [ ] **A3 Edit user message** — make user bubble content `contenteditable`/edit modal; on save, resend (truncate history after that turn).
5. [x] **A4 Feedback** — 👍/👎 buttons stored in history entry `{type:"text", feedback:"up"/"down"}`; persisted by `_record_event` path (extend history schema).
6. [x] **A6 Scroll-to-bottom** — floating button shown when `#messages` scrolled up > 200px; auto-scroll on new content unless user scrolled up.
7. [x] **A7 Continue** — if `finish_reason === "length"`, show "Continue generating" → resume stream.

### Phase 2 — Composer & Input (P1)
8. [x] **B1 Attachments** — paperclip + drag-drop; preview chips; send as `multipart` or attach to message payload (extend `ChatReq`/`WS` message schema; provider must support multimodal — gate by capability).
9. [ ] **B2 Model/effort quick switch** — composer dropdown reading `/api/provider` + per-session settings; updates `pendingSettings`/`setSessionSettings`.
10. [x] **B3 Slash palette** — `/` opens filtered command list (reuse existing commands).
11. [x] **B4 Composer toolbar** — group attach + tools + model into a clean toolbar above textarea.

### Phase 3 — Rendering & Output (P1)
12. [x] **C1 Artifacts side panel** — detect fenced code blocks / HTML / SVG; render in resizable right panel (`#artifact-panel`); toggle "open in artifact". Reuse highlight.js. For HTML/SVG, sandboxed `<iframe>`/preview.
13. [x] **C2 Mermaid** — lazy-load `mermaid` from CDN; render ```mermaid blocks; fallback to code.
14. [ ] **C4 Diff view** — detect patch/text diff in tool results or assistant; color added/removed lines (`.diff-view` CSS present, auto-detect not wired).
15. [x] **C5 Per-message usage** — move usage from system line into a small footer under each assistant message (read from history `usage` entries).

### Phase 4 — Session Management (P1)
16. [x] **D1 Search** — input above `#session-list`; filter by name/content (search persisted JSON).
17. [x] **D2 Folders/pin** — add `pinned: bool` + `folder: str` to `Session`; UI controls; persist. (pin done; folder not implemented)
18. [x] **D3 Inline rename** — edit icon on session `<li>`; `POST /api/sessions/{id}/rename`.
19. [x] **D4 Export** — "Export" action → `GET /api/sessions/{id}/export` returning Markdown; download via blob.
20. [ ] **D5 Bulk delete / reorder** — multi-select mode in rail.

### Phase 5 — Agentic Edge (P2)
21. [ ] **E1 Activity timeline** — new event type `agent_step` (or reuse tool events) rendered as a live, collapsible step list with status icons.
22. [ ] **E2 Tool progress** — mark tool cards `running`/`done`/`error` with spinner + duration; update in place as events arrive.
23. [x] **E3 MCP / subagent UI** — new "Integrations" panel wiring `/api/mcp/connect` and `/api/subagents`.
24. [ ] **E4 Checkpoint timeline** — visualize checkpoints from `/api/checkpoints`; click to restore/compare.
25. [x] **E5 Plan approve/execute** — in plan mode, add "Approve & Run" button that switches to chat and executes the plan.

### Phase 6 — Polish & Platform (P2/P3)
26. [x] **F1 Responsive** — CSS: sidebar becomes slide-over < 768px; composer sticks to bottom; touch targets ≥ 40px.
27. [x] **F2 Shortcuts** — `Cmd/Ctrl+K` palette, `Cmd+Enter` send, `Esc` stop, `?` help.
28. [ ] **F3 A11y** — aria-labels, `role="log"` on `#messages`, focus management, `prefers-reduced-motion`, high-contrast theme.
29. [x] **F4 Settings page** — theme, font size, default model/effort/thinking, markdown toggles.
30. [x] **F5 Toasts** — replace remaining system-line noise with toasts.
31. [ ] **F6 Empty/error states** — friendly illustrations + retry actions.

---

## 5. Proposed Architecture Notes

- **Stop/cancel**: store `session._task: asyncio.Task` in `Manager`; WS handler cancels on `stop`. Frontend shows Stop while `state.streaming`.
- **Artifacts**: pure frontend — parse rendered markdown for code blocks with `language` in a known set (html, svg, mermaid, python, etc.); open in `#artifact-panel`. No backend change except optionally returning raw blocks (already in history).
- **History schema extension**: add optional fields `feedback`, `folder`, `pinned`, `artifacts` to history entries; `_record_event` already extensible. Keep backward-compatible (legacy `role`-based entries migrated in `normalizeHistoryEntry`).
- **Search/export**: read-only over `.ai-runtime/sessions/*.json`; add `GET /api/sessions/{id}/export` and search param to `GET /api/sessions?q=`.
- **Shortcuts/palette**: a single `commandPalette` module in `app.js`; no backend change.

---

## 6. Recommended Execution Order

1. **Phase 0 + Phase 1** (stop, regenerate, edit, feedback, scroll-to-bottom, continue) — ✅ Done except A3 (edit user message).
2. **Phase 3 C1/C2** (artifacts + mermaid) — ✅ Done; C4 (diff view) partial.
3. **Phase 2** (composer: attachments, model switch, slash palette) — ✅ Done except B2 (composer model quick-switch).
4. **Phase 4** (session search, pin, rename, export) — ✅ Done except D5 (bulk delete/reorder); D2 folder not implemented.
5. **Phase 5** (agentic edge: activity timeline, tool progress, MCP/subagent UI, plan execute) — ✅ Done for E3/E5; E1/E2/E4 remaining.
6. **Phase 6** (responsive, shortcuts, a11y, settings, toasts) — ✅ Done except F3 (a11y) and F6 (error states).

**Remaining work (backlog)**
- A3 Edit sent user message (contenteditable + resend/truncate).
- B2 Composer model/effort quick-switch dropdown.
- C4 Auto-detect diffs/patches and render with `.diff-view` coloring.
- D2 Folders (beyond pin); D5 bulk select/delete + drag-reorder.
- E1 Live agent activity timeline; E2 live tool progress (running/done/duration); E4 checkpoint timeline/compare.
- F3 Accessibility (aria roles, `role="log"`, focus management, `prefers-reduced-motion`, high-contrast theme); F6 friendly error states.
- Matrix gaps: Composer model picker, Custom instructions / memory, Conversation branching (parity N/A).

Each phase is independently shippable; Phase 1 + C1 alone brought the app to near-parity with Claude.ai/ChatGPT on the essentials while keeping its agentic identity.
