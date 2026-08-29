# Zero-context development handoff

This document is the operational source of truth for a new Agent with no access to prior conversations. The product is a local Windows 3D desktop companion whose visible surface is a Godot-rendered Luo Tianyi avatar; do not reinterpret it as a conventional Agent chat window, do not make Codex/Claude/Spark a production dependency, and do not commit the local character model or user data. Start by reading `AGENTS.md`, use the table below to select the relevant code, run the baseline checks in `docs/TESTING.md`, and only then modify behavior.

## Snapshot: 2026-08-29

| Area | Implemented and verified | Remaining boundary |
|---|---|---|
| Avatar | Godot transparent/borderless/always-on-top window; click menu; chat overlay; interaction menu; left-drag move with persisted position; right-drag turn; wheel zoom | No installer, autostart or crash supervisor |
| Model behavior | 1 skeleton; 8 cached action bones; 2 pigtail roots; 48 expression slots; nod, wave, greet, turn, blink, smile, surprise, anger, wink, tears and vowel mouth shapes | Actions are procedural and visually rough; no authored animation clips or physics collision |
| Chat loop | Godot sends `chat.message`; Core calls Provider; `chat.response` returns text/emotion/gesture; GLM 5.3 Flash Coding endpoint has been used successfully | No streaming, cancellation, retries/backoff or conversation UI virtualization |
| Character Harness | Luo Tianyi identity and self-boundary prompt; strict JSON output contract; safe fallback for plain text; emotion/gesture whitelist | Prompt is embedded in Python; no versioned evaluation set or prompt configuration UI |
| Music knowledge | 20 original songs in a tracked JSON seed catalog; query scoring injects only relevant records; all records include source URLs | It is not a top-100 popularity corpus, has no automated refresh, and excludes covers by product decision |
| Voice | Local microphone capture and faster-whisper transcription path are wired; dependencies exist on this machine | Stable human acceptance has not passed; empty/unclear audio remains common and TTS is absent |
| Memory | SQLite WAL stores messages, events and pending `memory_candidate`; latest 20 messages reload on startup | Candidates are not reviewed/promoted/reinjected; settings table is unused |
| Desktop shell | React/Tauri debug shell can connect and chat | It is not the primary product surface and is not launched by the one-click path |
| Proactive agent | Architecture reserves event and permission layers | Startup/Idle triggers, `IGNORE`, permissions, tools and Spark Adapter are not implemented |

The last verified local runtime reported Core `status=ok`, one connected Avatar, `provider=glm`, `runtime=glm`, `model=glm-5.3-flash`, configured credentials, and enabled SQLite; local database counts were 20 messages and 30 events, but neither content nor database is part of Git. The verification baseline at handoff is 11/11 Python tests passing, TypeScript type check passing, Godot headless input guard passing, 48 expressions detected, two pigtail roots detected, asset hash passing, and no tracked diff whitespace errors.

## Zero-context takeover simulation

| Date and scope | Result | Evidence and limit |
|---|---|---|
| 2026-08-29; independent read-only Agent received only the repository root and was limited to `AGENTS.md`, README, handoff/topic docs and manifests | PASS for immediate development takeover | It correctly reconstructed the VTuber-like product form, Godot/Core/Provider architecture, fresh/current-machine startup, automated checks, implemented/deferred capabilities, local-only asset contract and STT as the first task; it found no substantive document contradiction. It correctly noted that a written verification snapshot is not proof of a future machine's state and that Python dependencies are not fully locked, so every new Agent must run the baseline before editing. |

## Repository map and ownership

| Path | Responsibility | Start here when |
|---|---|---|
| `apps/avatar-runtime/runtime.gd` | Window behavior, model discovery, bones, expressions, Core WebSocket, state/action execution | Changing 3D behavior, dragging, camera, expressions or bridge reception |
| `apps/avatar-runtime/interaction_ui.gd` | Character click menu, chat panel, interaction buttons, focus and voice controls | Changing visible interaction or input behavior |
| `apps/avatar-runtime/main.tscn` | Local GLB instance, camera, lights and runtime script | Changing scene composition; requires local model |
| `services/agent-core/agent_core/main.py` | FastAPI, WebSocket routing, Provider adapters, chat and voice orchestration | Changing protocol, Provider calls or Core lifecycle |
| `services/agent-core/agent_core/harness.py` | Character prompt, structured response parsing and behavior mapping | Changing persona, response contract or emotion/gesture policy |
| `services/agent-core/agent_core/data/luotianyi_original_songs.json` | Original-song factual seed records and source URLs | Correcting or expanding music knowledge without placing songs in the base prompt |
| `services/agent-core/agent_core/song_catalog.py` | Query normalization, scoring and prompt context formatting | Changing retrieval behavior |
| `services/agent-core/agent_core/storage.py` | SQLite schema and recent-message persistence | Adding durable memory or migrations |
| `services/agent-core/agent_core/voice.py` | Microphone capture, WAV encoding and faster-whisper | Stabilizing STT |
| `apps/desktop/` | Optional React/Tauri debug/settings shell | Working on diagnostics or future tray/settings UI |
| `scripts/start-mvp.ps1` | Provider-aware one-click Core and Avatar startup | Changing startup checks or process launch |
| `docs/AVATAR_BRIDGE.md` | WebSocket protocol contract | Adding or changing events |

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
| P0 | Stabilize STT | A normal 3–10 second Mandarin utterance repeatedly fills editable text without crashing or hanging |
| P0 | Windows login autostart and supervisor | After reboot, Core and one Avatar start without a terminal/Codex; duplicate launch is prevented; failures leave useful logs |
| P0 | Startup and Idle triggers | Local events reach Core, may yield a useful action or `IGNORE`, and obey quiet-hours/debounce rules |
| P1 | Durable memory promotion | Pending facts require a clear policy, are editable/deletable, and are selectively injected rather than dumped into every prompt |
| P1 | Improve model motion | Replace rough procedural poses incrementally, preserve current interaction and avoid hair/body clipping |
| P1 | TTS | Reply audio, mouth timing and interruption are tested separately from STT |
| P2 | Permission layer and tools | Read-only capability first; mutation and external actions require explicit confirmation |
| P2 | Spark Adapter | Spike official callable surface; keep local Core functional if unavailable |

## Known traps

The GLM Coding endpoint must end in `/api/coding/paas/v4`; a wrong endpoint can return a misleading HTTP 429 even when the same key works through CC Switch. PowerShell web commands can inherit a proxy and return a false localhost 502, so local health checks must bypass proxies. Godot `_input()` runs before GUI controls, therefore keyboard shortcuts must immediately return while a `LineEdit` or `TextEdit` owns focus. `data/` must not be globally ignored because the song catalog is static package data. The runtime GLB is over GitHub's regular 100 MB limit and has unresolved redistribution rights, so use the local locator and hash rather than Git LFS. Long pigtails are `MaWei_R_0_1` and `MaWei_L_0_1`; do not confuse them with rear hair bones.
