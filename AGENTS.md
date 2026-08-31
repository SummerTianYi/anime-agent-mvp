# AGENTS.md

## Mission and mandatory reading

Build a Windows-first, local-first 3D anime desktop companion whose visible product is an independent VTuber-like character, not another Codex/Claude/chat application window. Before changing code, read `docs/HANDOFF.md` and `docs/CONTRIBUTIONS.md`; then use `docs/ARCHITECTURE.md`, `docs/LOCAL_DEV.md`, `docs/TESTING.md`, `docs/KNOWN_ISSUES.md`, `docs/ASSET_PIPELINE.md`, `docs/plans/MODEL_OPTIMIZATION.md`, and `model-versions/README.md` as the source of truth for the relevant surface. Do not infer current progress from the historical milestone list or from prior conversations.

## Product and architecture decisions

| Decision | Rule |
|---|---|
| Visible runtime | Godot 3D Avatar is the primary experience; Tauri is an optional settings/debug shell |
| Production host | Codex, Claude, CC Switch and Spark are not runtime dependencies |
| Local kernel | Python Agent Core is mandatory for Provider calls, STT, persistence and desktop IPC |
| Provider | GLM 5.3 Flash is the default; DeepSeek and explicit Mock remain adapters |
| IPC | JSON events over localhost WebSocket; preserve role-directed routing |
| Storage | SQLite under `%LOCALAPPDATA%\AnimeAgent` by default; never commit user data |
| Character | Preserve Luo Tianyi identity, music-first personality and structured emotion/gesture contract |
| Assets | The character model is local-only until redistribution rights are proven; never force-add ignored assets |
| Spark | Deferred; any future integration must stay behind an adapter and cannot block the local loop |

## Current implementation boundary

The text-chat loop, GLM connection, character Harness, 20-song original catalog, SQLite history, Godot menu, basic actions/expressions, draggable window and one-click developer startup are implemented. Windows login autostart, process supervision, Startup/Idle triggers, TTS, a real permission layer, stable STT acceptance, packaging and Spark are not implemented. `memory_candidate` is persisted as a pending event but is not yet promoted into durable facts or reinjected into prompts.

## Engineering rules

1. Preserve a runnable Windows path after every milestone and keep changes scoped to the requested behavior; do not replace the 3D character with a conventional Agent window.
2. Keep Provider, future Spark and external capabilities behind adapters or narrow interfaces; domain and avatar behavior must not depend on a specific SDK.
3. Never commit `.env`, keys, tokens, cookies, personal conversations, SQLite files, logs, user memory, model binaries, textures, Blender files or downloaded source archives.
4. Treat `apps/avatar-runtime/assets/README.md` and `docs/LOCAL_MACHINE.md` as locators, not authorization to redistribute the referenced assets.
5. All destructive or externally visible computer actions require an explicit permission layer; such actions remain disabled in the current MVP.
6. Preserve WebSocket event compatibility and update `docs/AVATAR_BRIDGE.md` plus tests when the event contract changes.
7. Do not claim voice, login autostart, proactive triggers or long-term memory are complete until the acceptance checks in `docs/TESTING.md` pass.
8. Use compact prose and tables in documentation; avoid sentence-per-paragraph formatting and duplicated status lists.
9. Model versions are immutable. Before an accepted model/render optimization, verify the current snapshot; after acceptance, allocate the next `major.minor` version, preserve Blend/GLB locally, record hashes/evidence in `model-versions/`, and never reuse a rejected experiment as a formal version.

## Required verification

Run the Python unit tests, TypeScript build/type check, Godot headless input regression, local asset check and `git diff --check` for relevant changes; run the Bridge verifier only when Core is online, and note that a real Provider run sends an API request. Before committing, inspect ignored files and scan staged content for secrets and files larger than 50 MB. Exact commands and expected outputs are in `docs/TESTING.md`.

## Next recommended order

Unless the user changes priorities, stabilize and accept STT first, then implement Windows login autostart plus process supervision, then Startup/Idle triggers with an `IGNORE` outcome, then durable memory promotion; TTS and Spark remain later work. Fix regressions in the current chat/avatar loop before adding new capability.
