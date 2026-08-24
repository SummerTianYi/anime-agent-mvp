# AGENTS.md

## Project goal

Build a Windows-first local desktop anime agent MVP that starts automatically at login and remains available without manually opening Codex.

## Product decisions

- Codex is the primary development tool, not the production runtime host.
- Spark is the preferred agent-kernel integration target, but all Spark-specific logic must live behind an adapter.
- Gemini Flash is the default API for general chat, routing, and lightweight reasoning.
- A local Agent Core is mandatory for OS events, startup, memory, permissions, and desktop communication.
- MVP is local-first. Do not introduce cloud infrastructure unless required by an explicit task.

## Stack

- Desktop: Tauri + React + TypeScript
- Core: Python 3.12
- IPC: WebSocket on localhost
- Storage: SQLite
- Secrets: environment variables / local untracked config

## Engineering rules

1. Keep the first runnable path small; do not build voice, computer-use, multi-agent, or cloud features before the MVP loop works.
2. Do not couple domain logic directly to Spark/Gemini SDKs. Use adapters/interfaces.
3. All destructive or externally visible actions require an explicit permission layer.
4. Never commit API keys, tokens, personal paths, or generated user memory.
5. Every milestone must remain runnable on Windows.
6. Prefer boring, debuggable components over premature abstractions.
7. Startup and idle triggers must support a no-op/IGNORE result to prevent intrusive behavior.

## Initial implementation order

1. Scaffold Tauri desktop app.
2. Scaffold Python Agent Core with `/health` and WebSocket.
3. Connect desktop to Core and show online/offline state.
4. Add Gemini adapter and text chat.
5. Add avatar state machine.
6. Add Windows login autostart.
7. Add startup + idle triggers.
8. Add SQLite persistence.
9. Run Spark integration spike and implement SparkAdapter if viable.
