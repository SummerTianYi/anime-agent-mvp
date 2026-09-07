# AGENTS.md

## Mission and mandatory reading

Build a Windows-first, local-first 3D anime desktop companion whose visible product is an independent VTuber-like character (Luo Tianyi), not another Codex/Claude/chat application window. **Read `docs/HANDOFF.md` (接手总纲) first** — it is the single source of truth for the mission, the milestone ladder, the three-agent ownership history, the current frozen capability list and the takeover gate. Then read `docs/CONTRIBUTIONS.md` (ownership declarations) and `docs/VERIFICATION_SPEC.md` (mandatory real-machine verification). Use `docs/ARCHITECTURE.md`, `docs/LOCAL_DEV.md`, `docs/TESTING.md`, `docs/KNOWN_ISSUES.md`, `docs/ASSET_PIPELINE.md`, `docs/plans/*`, and `model-versions/README.md` as the source of truth for the relevant surface. Do not infer current progress from prior conversations or from any document whose status section contradicts `docs/HANDOFF.md`.

## Product and architecture decisions

| Decision | Rule |
|---|---|
| Visible runtime | Godot 3D Avatar is the primary experience; Tauri is an optional settings/debug shell |
| Production host | Codex, Claude, zcode and other dev agents are not runtime dependencies |
| Local kernel | Python Agent Core is mandatory for Provider calls, STT, TTS, persistence and desktop IPC |
| Provider | GLM 5.3 Flash is the default; DeepSeek and explicit Mock remain adapters |
| IPC | JSON events over localhost WebSocket; preserve role-directed routing (see `docs/AVATAR_BRIDGE.md`) |
| Storage | SQLite under `%LOCALAPPDATA%\AnimeAgent` by default; never commit user data |
| Character | Preserve Luo Tianyi identity, music-first personality and structured emotion/gesture contract |
| Capability grants | New capabilities are proven in the `anime-agent-workbench` sandbox and pass exams before real permissions are granted in this repo (T0-T3 precedent); the allow/ask/deny permission engine is never bypassed |
| Assets | The character model is local-only until redistribution rights are proven; never force-add ignored assets |
| Spark | Deferred; any future integration must stay behind an adapter and cannot block the local loop |

## Current implementation boundary

Implemented and frozen (see `docs/HANDOFF.md` §3 for the full list with exam evidence): text-chat loop with sessions, wake word + STT pipeline, TTS sidecar client with interruption, read-only tool loop, persona prompt override, three-tier permission engine with audit, atomic `write_file` with write-roots + in-chat confirmation, `run_command` with command whitelist, per-tool-type narration, MCP stdio host with confirmation routing, proactive startup greeting with quiet hours, screen vision via GLM native multimodality (privacy ask-gate, live-verified 2026-09-07), memory facts table with tiered promotion and lexical recall. Idle trigger (local poll + template bank, standby is zero-quota), STT wedge self-heal, and five real MCP servers (browser/GitHub/search/Gmail/Drive, 93 tools) shipped 2026-09-07. Not implemented: Windows autostart/supervision (owner deferred), keyboard/mouse control (deferred by design), pending-memory review UI, Spark Adapter. `docs/TESTING.md` (181 tests) is the acceptance baseline.

## Engineering rules

1. Preserve a runnable Windows path after every milestone and keep changes scoped to the requested behavior; do not replace the 3D character with a conventional Agent window.
2. **Do not rebuild frozen capabilities.** If a task touches a capability listed as ✅ in `docs/HANDOFF.md` §3, run its regression tests first and make the minimal fix; a rewrite requires the owner's explicit approval.
3. Keep Provider, Spark and external capabilities behind adapters or narrow interfaces; domain and avatar behavior must not depend on a specific SDK.
4. Never commit `.env`, keys, tokens, cookies, personal conversations, SQLite files, logs, user memory, model binaries, textures, Blender files or downloaded source archives.
5. Treat `apps/avatar-runtime/assets/README.md` and `docs/LOCAL_MACHINE.md` as locators, not authorization to redistribute the referenced assets.
6. All write, command and privacy-sensitive tools go through the permission engine (allow/ask/deny) with audit events; ask-tier actions park in the in-chat confirmation flow. Never add a tool that bypasses the gate.
7. Preserve WebSocket event compatibility and update `docs/AVATAR_BRIDGE.md` plus tests when the event contract changes.
8. Do not claim voice, autostart, proactive triggers or long-term memory are complete until the acceptance checks in `docs/TESTING.md` pass.
9. Model versions are immutable. Before an accepted model/render optimization, verify the current snapshot; after acceptance, allocate the next `major.minor` version, preserve Blend/GLB locally, record hashes/evidence in `model-versions/`, and never reuse a rejected experiment as a formal version.
10. Declare your work: append your agent name, date, scope and evidence to `docs/CONTRIBUTIONS.md`; tag commits with your agent name. Append-only — never overwrite another agent's declaration.
11. Shell discipline on this machine: use Git Bash for all shell work - never PowerShell heredocs; when a file contains backslashes, regexes or escape sequences (.py regexes, .cmd, JSON paths), create it with the file-writing tool instead of shell heredocs, and pass Windows-style paths to Windows Python processes.
12. Keep documentation truthful: when a capability's status changes, update `docs/HANDOFF.md` §3 and the README status table in the same change. The takeover gate in `docs/HANDOFF.md` §7 (zero-context white-paper test) must pass before every handover.

## Required verification

Run the Python unit tests (currently 181), TypeScript build/type check, Godot headless input regression, local asset check and `git diff --check` for relevant changes; whenever a documentation status claim changes, also run the docs-consistency guard (`scripts/check_docs_consistency.py`, expect `DOCS_CONSISTENCY_OK`); run the Bridge verifier only when Core is online, and note that a real Provider run sends an API request (state the expected call count to the owner first). Real-machine verification follows `docs/VERIFICATION_SPEC.md`. Never force-push `main` — git history is the disaster-recovery baseline; before deleting any tracked file, be able to name the recovery command (see `docs/HANDOFF.md` §10). Before committing, inspect ignored files and scan staged content for secrets and files larger than 50 MB. Exact commands and expected outputs are in `docs/TESTING.md`.

## Next recommended order

Do not start from this file — claim your territory from `docs/HANDOFF.md` §1 (当值分派) and pick from §3 "未开工" list. Default priorities if the owner does not override: the frontend UI upgrade (U0 survey + form-factor decision, `docs/plans/UI_UPGRADE.md`), then prompt training item 2 (poison-content proactive warning) and the memory review UI (KI-016).
