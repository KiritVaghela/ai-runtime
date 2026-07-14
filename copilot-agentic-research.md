# GitHub Copilot Agentic Coding Capabilities — Research Synthesis

*Research only. Compiled 2026-07-14 from official GitHub and VS Code documentation.*

## 1. Executive summary

GitHub Copilot now spans a family of agentic surfaces, all unified under one
Copilot subscription and one agent-session model in VS Code:

- **Copilot cloud agent** (formerly "Coding Agent"): autonomous, cloud-hosted
  (GitHub Actions–powered) agent that works on GitHub issues/PRs, researches a
  repo, plans, edits on a branch, and opens a PR.
- **Agent mode in VS Code** (local agents): in-editor autonomous loop that edits
  files, runs terminals, and self-corrects in your local workspace.
- **Copilot CLI** (`copilot`): terminal-native agent with interactive and
  programmatic modes, sandboxes, and ACP support.
- **Third-party agents** (Claude, OpenAI Codex) usable inside the same VS Code
  agent surface via the provider SDKs.

Copilot is **not locked to a single model**: it is multi-model (GPT-5.x
`(copilot)`, Claude, etc.), and the CLI can even point at OpenAI-compatible,
Azure OpenAI, Anthropic, or local (Ollama) endpoints.

---

## 2. The four agent surfaces at a glance

| Surface | Where it runs | Trigger | Autonomy | Isolation |
|---|---|---|---|---|
| **Copilot cloud agent** | GitHub Actions ephemeral env (remote) | Assign issue/PR, `@copilot` comment, Chat on GitHub.com, VS Code "Cloud" handoff | Fully autonomous; 59-min hard cap/session | Separate branch + PR; repo-scoped |
| **Agent mode (local)** | Your machine, inside VS Code | Chat view "Agent" mode, inline chat (`⌘I`), Agents window | Permission levels: Default / Bypass / Autopilot | Workspace folder; sandbox optional |
| **Copilot CLI** | Local terminal (background) or cloud sandbox | `copilot`, `copilot -p "..."`, `/` commands | Per-tool approval; `--allow-all-tools` / `/yolo` | Git worktree or folder; local/cloud sandbox |
| **Third-party (Claude/Codex)** | Local or cloud via provider SDK | VS Code session picker | Provider-defined permission modes | Provider harness |

---

## 3. Dimension-by-dimension breakdown

### (1) Agent loop / autonomous mode
- **Cloud agent**: research → plan → implement → test/lint → commit → (optional)
  PR, all autonomously. Can be assigned via issue assignee = "Copilot", `@copilot`
  in a PR comment, or automations (schedule / event-driven, e.g. security
  campaigns). Max **59 minutes per session** (hard limit).
- **Agent mode (VS Code)**: the agent "plans the approach, edits files across your
  project, runs commands, and self-corrects until the work is done." Supports
  **Autopilot** permission level: keeps iterating until it judges the task
  complete, auto-retries on errors, auto-responds to clarifying questions
  (advanced autopilot delegates the "done?" decision to a small fast model).
- **Copilot CLI**: interactive (ask/execute + **plan mode** via `Shift+Tab`) and
  programmatic (`-p`). Background sessions keep running after VS Code closes.
- **Background / parallel**: multiple Copilot CLI sessions run in parallel; cloud
  and local sessions can be handed off to each other (`/delegate`, "Continue in
  Cloud").

### (2) Tool use
Built-in tool categories in VS Code chat: **edit** (`#edit`), **search**
(`#search`, `#codebase`, `#problems`, `#usages`), **read**, **terminal**
(`run commands`, background terminals, timeouts), **web/fetch** (`#web`), plus
**MCP tools** and **extension tools**. Tool sets group related tools (`#reader`,
`#search`). You can edit tool input parameters before approval. The agent
autonomously picks tools; you can force one with `#toolname`.
Cloud agent additionally runs tests/linters in its Actions environment and uses
the GitHub MCP server for repo context (issues, PRs).

### (3) Sandbox / permissions / workspace trust
- **Workspace Trust**: untrusted workspace → restricted mode → **agents disabled**.
- **Trusted directories** (CLI): must confirm trust of the launch directory.
- **Agent sandboxing** (preview, macOS/Linux/Windows): OS-level filesystem +
  network isolation; sandboxed terminal commands are auto-approved. Configurable
  allow/deny read/write paths and allowed/denied network domains.
- **MCP server sandboxing**: stdio servers on macOS/Linux can be sandboxed
  (`"sandboxEnabled": true` in `mcp.json`).
- **CLI sandboxes**: local (`/sandbox enable`) and cloud (`copilot --cloud`)
  sandboxes; cloud inherits Copilot cloud agent firewall policies.

### (4) Context management
- **Implicit**: active file, selection, filename auto-included; in agent mode the
  agent decides what extra context to pull.
- **`#`-mentions**: `#file`, `#folder`, `#codebase`, `#terminalSelection`,
  `#problems`, `#web`, tool sets.
- **Vision**: attach images/screenshots; browser-element selection adds HTML/CSS.
- **Workspace indexing / codebase**: `#codebase` semantic search over the repo.
- **CLI auto-context**: auto-compaction at ~95% token limit, `/compact`, `/context`
  token breakdown; models with 1M-token extended context available.
- **Cloud agent**: repo-scoped; GitHub MCP gives cross-issue/PR context; broader
  access configurable via repo MCP settings.

### (5) Memory (persistent cross-session)
- **Copilot Memory** (public preview, Pro/Pro+/Max on by default; Enterprise
  admin-gated): stores **repository-level facts** (conventions, architecture,
  build commands, with code citations that are re-validated against the current
  branch) and **user-level preferences** (coding style). Used across cloud agent,
  code review, and CLI. Unused entries auto-deleted after **28 days**. Admins can
  export/delete. Distinct from instruction files.
- **Instruction files** (always-on, version-controlled): `.github/copilot-instructions.md`
  (generate via `/init`), `*.instructions.md` (glob-scoped), plus `AGENTS.md` /
  `CLAUDE.md` discovery. Monorepo parent-repo discovery via
  `chat.useCustomizationsInParentRepositories`.

### (6) Skills / slash commands / custom instructions
- **Agent Skills** (open standard, agentskills.io): folders with `SKILL.md`
  (instructions + scripts + resources), progressive 3-level loading. Stored in
  `.github/skills`, `.claude/skills`, `.agents/skills` (project) or
  `~/.copilot/skills` (personal). Work across VS Code, CLI, cloud agent, code
  review, and JetBrains. Installable via `gh skill` and agent plugins.
- **Slash commands**: `/` menu lists skills + prompt files; `/create-skill`,
  `/create-agent`, `/create-instruction`, `/create-prompt`, `/create-hook`,
  `/init`, `/compact`, `/context`, `/research`, `/model`, `/allow-all`, `/yolo`,
  `/sandbox`, `/remote`, `/delegate`, `/feedback`.
- **Prompt files** (`*.prompt.md`): reusable prompts invoked as slash commands.
- **Custom instructions**: project + org-level natural-language guidance.

### (7) Multi-agent / sub-agents
- **Custom agents** (`.agent.md` / `.github/agents` / `.claude/agents`): personas
  with own instructions, tool allow-lists, model, and **handoffs** (guided
  sequential workflows, e.g. Plan → Implement → Review). Org-level agents
  discoverable via `github.copilot.chat.organizationCustomAgents.enabled`.
- **Subagents**: custom agents can declare `agents:` for subagent use; skills can
  run in a **forked context** (separate subagent, only final result returned).
- **Third-party sub-agents**: Claude `/agents` wizard; Codex runs interactively or
  unattended.
- **Handoffs between surfaces**: local ↔ Copilot CLI ↔ cloud agent session
  handoffs preserve full context.

### (8) MCP support
- **Yes, first-class.** Configure via `.vscode/mcp.json` (workspace) or user
  profile; also MCP gallery (`@mcp`), `MCP: Add Server`, dev containers, CLI.
- Transports: stdio, `http`, remote. Supports **Resources**, **Prompts**
  (`/<server>.<prompt>`), **MCP Apps** (interactive UI), and tool sandboxing.
- Cloud agent: repo MCP settings apply to both cloud agent and code review; GitHub
  MCP + Playwright MCP enabled by default.
- CLI: `--allow-tool='My-MCP-Server'`, `/mcp` to list; known org-policy
  limitations noted.
- Enterprise: `ChatMCP` policy can restrict to a curated registry (`registryOnly`)
  or disable entirely; private registry via `McpGalleryServiceUrl`.

### (9) Streaming / UX
- **Inline chat** (`⌘I`), **Chat view** (`⌃⌘I`), **Agents window** (agent-first,
  cross-project, `code --agents`), **Quick Chat** (`⇧⌥⌘L`).
- **Diff view**: inline diffs with Keep/Undo per change; **checkpoints** snapshot
  files for rollback; staging in Source Control accepts pending edits.
- **Streaming** responses; tool-call details collapsible; background-terminal
  push; OS notifications (`chat.notifyWindowOnResponseReceived` /
  `...OnConfirmation`).
- **Steering while running**: queue / steer / stop-and-send; drag-to-reorder
  pending messages.

### (10) Safety / permissions
- **Permission levels**: Default Approvals (per-tool confirmation), Bypass
  Approvals (auto-approve all), Autopilot (auto-approve + self-drive).
- **Tool approval** scopes: single use / session / workspace / all future;
  `chat.tools.eligibleForAutoApproval` to forbid auto-approval of sensitive tools.
- **URL approval**: two-step (trust domain → review fetched content) to block
  prompt injection; `chat.tools.urls.autoApprove` patterns.
- **Terminal auto-approval**: allow/deny lists with regex; `rm`/`del` blocked by
  default; best-effort parsing caveats → prefer sandbox/container.
- **Sensitive files**: `chat.tools.edits.autoApprove` glob (e.g. `"**/.env": false`).
- **Hooks**: `preToolUse` can block dangerous commands; deterministic guardrails.
- **Enterprise policies**: `ChatAgentMode` (disable agents), `ChatMCP`,
  `ChatToolsAutoApprove`, `ChatToolsEligibleForAutoApproval`,
  `ChatToolsTerminalEnableAutoApprove`, extension-tool restriction.

### (11) Provider flexibility
- **Multi-model**, not locked to OpenAI/Claude. Model picker per session; models
  with 1M-token context and configurable reasoning levels.
- **CLI bring-your-own provider**: `COPILOT_PROVIDER_TYPE` (`openai`/`azure`/
  `anthropic`), `COPILOT_PROVIDER_BASE_URL`, `COPILOT_PROVIDER_API_KEY`,
  `COPILOT_MODEL` — works with Ollama, vLLM, any OpenAI-compatible endpoint
  (requires tool-calling + streaming).
- **Third-party agents** (Claude, Codex) run inside VS Code via their SDKs, billed
  through the Copilot subscription.

### (12) Integration surfaces
- **VS Code extension** (primary): Chat view, inline chat, Agents window, agent
  mode, MCP, skills, custom agents, cloud/CLI/third-party sessions.
- **CLI**: `copilot` (GitHub Copilot CLI) — interactive + programmatic; ACP server
  for third-party tooling; `/remote` mirrors sessions to GitHub.com / Mobile.
- **Web**: GitHub.com Copilot Chat and cloud agent (assign issues, `@copilot`,
  automations, PRs); GitHub Mobile app remote control.
- **JetBrains IDEs**: agent mode + skills supported.
- **Desktop**: VS Code (incl. Insiders) and GitHub Mobile; no separate "Copilot
  desktop" app beyond VS Code.

---

## 4. How it differs from Claude Code / Codex / Cursor

| Dimension | Copilot (cloud + VS Code + CLI) | Claude Code | OpenAI Codex | Cursor |
|---|---|---|---|---|
| Autonomous cloud agent on issues/PRs | **Yes** (cloud agent, GitHub Actions) | No (local CLI/SDK) | Yes (Codex cloud) | No |
| Native GitHub issue/PR workflow | **Deep** (assignee, `@copilot`, automations) | Via MCP/tools | Via GitHub integration | Limited |
| Multi-model / BYO provider | **Yes** (incl. Ollama/local) | Anthropic only | OpenAI only | OpenAI/others via config |
| Persistent memory | **Copilot Memory** (repo + user facts) | `CLAUDE.md` + `/memory` | Session/scoped | Project rules |
| MCP | **Yes** (stdio/http/remote, sandbox) | Yes | Yes | Yes |
| Unified agent surface (local+cloud+CLI+3rd-party) | **Yes** in VS Code | No | Partial | No |
| Skills open standard | **agentskills.io** | Claude skills | Codex skills | Cursor rules |
| Enterprise policy control | **Extensive** (MCP, agents, auto-approve) | Org policies | Org policies | Limited |
| IDEs | VS Code + JetBrains + web + mobile | Terminal/SDK + some IDEs | VS Code + ChatGPT | VS Code fork |

**Key differentiators:** Copilot's tight, first-party integration with the GitHub
issue/PR/ Actions lifecycle (cloud agent) and its single unified agent-session
model spanning local, CLI, cloud, and third-party (Claude/Codex) agents inside VS
Code — with enterprise policy governance and a bring-your-own-model CLI.

---

## 5. Concrete capability checklist

- Assign a GitHub issue to "Copilot" → autonomous branch + PR.
- `@copilot` in a PR comment to request changes.
- Agent mode edits across the workspace and self-corrects.
- Autopilot mode drives to task completion without prompts.
- `copilot -p "..." --allow-tool='shell(git)'` for headless automation.
- `/sandbox enable` and `copilot --cloud` for isolated execution.
- `.github/copilot-instructions.md` via `/init` for repo standards.
- `SKILL.md` agent skills portable across VS Code/CLI/cloud/JetBrains.
- `.agent.md` custom agents with handoffs (Plan→Implement→Review).
- `mcp.json` MCP servers with resource/prompt/app/sandbox support.
- `preToolUse` hooks to block `rm -rf` / `DROP TABLE`.
- Copilot Memory auto-learns repo conventions (28-day validation).
- Third-party Claude/Codex agents inside the same VS Code surface.
- `/remote` to monitor/steer CLI sessions from GitHub.com or Mobile.
- Enterprise policies to disable agents, restrict MCP, force manual approval.

---

## 6. Source URLs

- Copilot cloud agent overview: https://docs.github.com/en/copilot/concepts/agents/coding-agent/about-coding-agent
- Copilot CLI: https://docs.github.com/en/copilot/concepts/agents/copilot-cli/about-copilot-cli
- Copilot Memory: https://docs.github.com/en/copilot/concepts/agents/copilot-memory
- Agent skills: https://docs.github.com/en/copilot/concepts/agents/about-agent-skills
- Hooks: https://docs.github.com/en/copilot/concepts/agents/hooks
- VS Code agent overview: https://code.visualstudio.com/docs/agents/overview
- Agent mode (chat): https://code.visualstudio.com/docs/chat/chat-overview
- Tools in chat: https://code.visualstudio.com/docs/chat/chat-tools
- MCP servers: https://code.visualstudio.com/docs/agent-customization/mcp-servers
- Customization overview: https://code.visualstudio.com/docs/agent-customization/overview
- Custom agents: https://code.visualstudio.com/docs/agent-customization/custom-agents
- Agent skills (VS Code): https://code.visualstudio.com/docs/agent-customization/agent-skills
- Approvals & permissions: https://code.visualstudio.com/docs/agents/approvals
- Security: https://code.visualstudio.com/docs/agents/security
- Cloud agents: https://code.visualstudio.com/docs/agents/agent-types/cloud-agents
- Copilot CLI sessions (VS Code): https://code.visualstudio.com/docs/agents/agent-types/copilot-cli
- Third-party agents: https://code.visualstudio.com/docs/agents/agent-types/third-party-agents
- Copilot Trust Center: https://resources.github.com/copilot-trust-center/
