# Zero-context development handoff

This document is the operational source of truth for a new Agent with no access to prior conversations. The product is a local Windows 3D desktop companion whose visible surface is a Godot-rendered Luo Tianyi avatar; do not reinterpret it as a conventional Agent chat window, do not make Codex/Claude/Spark a production dependency, and do not commit the local character model or user data. Start by reading `AGENTS.md`, use the table below to select the relevant code, run the baseline checks in `docs/TESTING.md`, and only then modify behavior.

## Snapshot: 2026-08-31

| Area | Implemented and verified | Remaining boundary |
|---|---|---|
| Avatar | Godot transparent/borderless/always-on-top window; click menu; bottom-overlay chat UI in the Luo Tianyi theme with scrollable bubbles and session controls; interaction menu; left-drag move with persisted position; right-drag turn; wheel zoom that yields to the UI when the pointer is over any open panel | No installer, autostart or crash supervisor; chat UI has no session rename/delete or history pagination |
| Model behavior | 1 skeleton; 48 expression slots; tracked motion registry; semantic upper/lower bone masks; two complete 17-bone pigtail chains classified as upper body; an 8.03-second looping authored idle with breathing/head micro-motion starts automatically; the 4.967-second pirouette interrupts idle via `P`/menu and returns to idle; procedural gestures and expressions remain available | Thinking/speaking/greeting still need authored clips; transition policy is simple cross-fade rather than an AnimationTree; pigtails have only subtle procedural secondary sway and no collision-aware physics; skirt dynamics remain absent |
| Chat loop | Godot sends `chat.message` with an optional `conversationId`; Core loads session-scoped history per request and calls the Provider; `chat.response` returns text/emotion/gesture plus `conversationId`; `session.new`, `session.list` and `chat.history` events cover creating, listing and reloading sessions (see `docs/AVATAR_BRIDGE.md`); GLM 5.3 Flash Coding endpoint has been used successfully | No streaming, cancellation or retries/backoff; session rename/delete and history pagination stay out of scope |
| Character Harness | Luo Tianyi identity and self-boundary prompt; strict JSON output contract; safe fallback for plain text; emotion/gesture whitelist | Prompt is embedded in Python; no versioned evaluation set or prompt configuration UI |
| Music knowledge | 20 original songs in a tracked JSON seed catalog; query scoring injects only relevant records; all records include source URLs | It is not a top-100 popularity corpus, has no automated refresh, and excludes covers by product decision |
| Voice | Local microphone capture and faster-whisper transcription path are wired; one manual acceptance round passed after resetting a wedged device; root cause identified (see Known traps) | Realtek driver-wedge self-healing in `voice.py` is pending; empty/unclear audio remains common and TTS is absent |
| Memory | SQLite WAL stores sessions, messages (with `conversation_id`), events and pending `memory_candidate`; startup migration backfills legacy messages into `初始会话`; history loads per session (20 for prompts, 50 for UI reload) | Candidates are not reviewed/promoted/reinjected; settings table is unused; no session rename/delete |
| Desktop shell | React/Tauri debug shell can connect and chat | It is not the primary product surface and is not launched by the one-click path |
| Proactive agent | Architecture reserves event and permission layers | Startup/Idle triggers, `IGNORE`, permissions, tools and Spark Adapter are not implemented |

The last verified local runtime (2026-08-30) reported Core `status=ok`, one connected Avatar, `provider=glm`, `runtime=glm`, `model=glm-5.3-flash`, configured credentials, and enabled SQLite; local database content and the database file itself stay out of Git. The verification baseline at handoff is 19/19 Python tests passing (now covering session storage and migration), TypeScript type check passing, Godot headless syntax checks passing for the rewritten UI scripts, the live database migration into sessions verified on this machine, and session routing/history/isolation verified against an isolated Core instance with a mock provider.

## Zero-context takeover simulation

| Date and scope | Result | Evidence and limit |
|---|---|---|
| 2026-08-29; independent read-only Agent received only the repository root and was limited to `AGENTS.md`, README, handoff/topic docs and manifests | PASS for immediate development takeover | It correctly reconstructed the VTuber-like product form, Godot/Core/Provider architecture, fresh/current-machine startup, automated checks, implemented/deferred capabilities, local-only asset contract and STT as the first task; it found no substantive document contradiction. It correctly noted that a written verification snapshot is not proof of a future machine's state and that Python dependencies are not fully locked, so every new Agent must run the baseline before editing. |
| 2026-08-30; chat-form upgrade landed: Core session system (sessions table, per-request session-scoped history, session/history protocol) plus a rewritten Godot bottom-overlay chat UI with session controls, avatar bubbles and input-priority guards; verified by 19 unit tests, a live database migration and an isolated-instance protocol run | The runtime avatar image `apps/avatar-runtime/assets/luotianyi_avatar.jpg` is gitignored by design; new machines copy `docs/design/assets/luotianyi-avatar-256.jpg` to that path or the UI falls back to ♪ |

## Repository map and ownership

| Path | Responsibility | Start here when |
|---|---|---|
| `apps/avatar-runtime/runtime.gd` | Window behavior, model discovery, bones, semantic motion-layer filtering, expressions, authored-track rebinding/playback, pigtail secondary sway, Core WebSocket and state/action execution | Changing 3D behavior, dragging, camera, animation layers, expressions or bridge reception |
| `apps/avatar-runtime/interaction_ui.gd` | Character click menu, bottom-overlay chat UI (bubbles, sessions, composer), interaction buttons, focus and voice controls | Changing visible interaction, chat UI or input behavior |
| `apps/avatar-runtime/main.tscn` | Local GLB instance, camera, lights and runtime script | Changing scene composition; requires local model |
| `services/agent-core/agent_core/main.py` | FastAPI, WebSocket routing, Provider adapters, chat and voice orchestration | Changing protocol, Provider calls or Core lifecycle |
| `services/agent-core/agent_core/harness.py` | Character prompt, structured response parsing and behavior mapping | Changing persona, response contract or emotion/gesture policy |
| `services/agent-core/agent_core/data/luotianyi_original_songs.json` | Original-song factual seed records and source URLs | Correcting or expanding music knowledge without placing songs in the base prompt |
| `services/agent-core/agent_core/song_catalog.py` | Query normalization, scoring and prompt context formatting | Changing retrieval behavior |
| `services/agent-core/agent_core/storage.py` | SQLite schema, sessions and per-conversation persistence with startup migration | Adding durable memory or migrations |
| `services/agent-core/agent_core/voice.py` | Microphone capture, WAV encoding and faster-whisper | Stabilizing STT |
| `apps/desktop/` | Optional React/Tauri debug/settings shell | Working on diagnostics or future tray/settings UI |
| `scripts/start-mvp.ps1` | Provider-aware one-click Core and Avatar startup | Changing startup checks or process launch |
| `docs/AVATAR_BRIDGE.md` | WebSocket protocol contract | Adding or changing events |
| `docs/MOTION_PIPELINE.md` | BVH retarget command, local artifacts, semantic bone masks, Godot animation bridge, acceptance gates and motion limitations | Adding or replacing authored animation clips |
| `scripts/model-pipeline/retarget_bvh.py` | Parameterized BVH→Luo Tianyi retarget, resampling, root policy, foot lock and one-action GLB export | Building the next skeletal motion asset |

## Fast resume procedure

| Step | Command or decision | Expected result |
|---|---|---|
| 1 | `git status --short --branch` | Understand local ownership; never discard unrelated work |
| 2 | `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\check-local-assets.ps1` | Current machine prints verified path, size and SHA-256 |
| 3 | Confirm `.env` exists without printing it | GLM is default; Key remains local and ignored |
| 4 | Double-click `start-anime-agent.cmd` or run `scripts/start-mvp.ps1` | Core is reused/started hidden and exactly one Godot Avatar appears |
| 5 | `curl.exe --noproxy "*" http://127.0.0.1:8765/health` | `status=ok`, expected Provider and an Avatar role after connection |
| 6 | Run the non-paid baseline in `docs/TESTING.md` | Unit, type/build, Godot and repository checks pass; do not rely only on this document's dated snapshot |

## Next work in recommended order

| Priority | Outcome | Acceptance boundary |
|---|---|---|
| P0 | Stabilize STT and harden `voice.py` against the Realtek driver wedge | Silence detection with an actionable error, one automatic device-reopen retry and per-recording level logging; a normal 3–10 second Mandarin utterance repeatedly fills editable text without crashing or hanging |
| P0 | Windows login autostart and supervisor | After reboot, Core and one Avatar start without a terminal/Codex; duplicate launch is prevented; failures leave useful logs |
| P0 | Startup and Idle triggers | Local events reach Core, may yield a useful action or `IGNORE`, and obey quiet-hours/debounce rules |
| P1 | Durable memory promotion | Pending facts require a clear policy, are editable/deletable, and are selectively injected rather than dumped into every prompt |
| P0 | Build the character motion set | Keep the new registry/idle baseline and produce thinking, speaking-body and greeting clips; preserve the static visual model, expressions, input and bridge; add pigtail/skirt secondary dynamics without torso clipping |
| P1 | TTS | Reply audio, mouth timing and interruption are tested separately from STT |
| P2 | Permission layer and tools | Read-only capability first; mutation and external actions require explicit confirmation |
| P2 | Spark Adapter | Spike official callable surface; keep local Core functional if unavailable |

## Known traps

The GLM Coding endpoint must end in `/api/coding/paas/v4`; a wrong endpoint can return a misleading HTTP 429 even when the same key works through CC Switch. PowerShell web commands can inherit a proxy and return a false localhost 502, so local health checks must bypass proxies. Godot `_input()` runs before GUI controls, therefore keyboard shortcuts must immediately return while a `LineEdit` or `TextEdit` owns focus. `data/` must not be globally ignored because the song catalog is static package data. The runtime GLB is over GitHub's regular 100 MB limit and has unresolved redistribution rights, so use the local locator and hash rather than Git LFS. Blender's generic animated GLB export washes out the current MMD/VRM materials in Godot; use it only as an animation container and keep the accepted static GLB for rendering, as implemented in `runtime.gd`. Long pigtails are `MaWei_R_0_1` and `MaWei_L_0_1`; do not confuse them with rear hair bones. The Realtek microphone array on this machine can wedge and deliver digital zeros indefinitely; an external event (Windows mic test, Fn mute toggle, Realtek console) resets it, so treat "silence despite working settings" as a driver state, not a code bug, and plan `voice.py` self-healing around it. `apps/avatar-runtime/assets/*` is gitignored by design: copy `docs/design/assets/luotianyi-avatar-256.jpg` to `apps/avatar-runtime/assets/luotianyi_avatar.jpg` on a new machine, otherwise the chat UI falls back to ♪ placeholders.
