# Local development

The primary runnable path is Godot Avatar plus Python Agent Core; React/Tauri is optional. A fresh clone can build and test Core/Tauri immediately, but the Godot scene requires the separately supplied local model documented in `docs/ASSET_PIPELINE.md`. Current-machine locators are in `docs/LOCAL_MACHINE.md`; never convert those absolute paths into committed runtime assumptions.

## Prerequisites

| Tool | Supported/current baseline | Required for |
|---|---|---|
| Windows | Windows-first | Desktop overlay, microphone and launch scripts |
| Python | 3.12; current 3.12.10 | Agent Core, tests and Bridge verification |
| Godot | 4.7.2 stable | Primary 3D Avatar runtime |
| Node/pnpm | Node 24.19, pnpm 11.19 | Optional React/Tauri shell |
| Rust/Cargo | 1.98 | Tauri native build |
| Blender | 5.2.1 LTS | Model conversion only, not normal runtime |
| Blender extensions | MMD Tools 4.5.13, VRM 4.5.0 | PMX import and VRM export |

## Fresh-clone setup

Run these commands from the repository root in PowerShell. Core installation without `[voice]` is enough for text-only runtime work; install the `test` extra for the full test suite and the voice extra for the confirmed product scope.

```powershell
Set-Location services\agent-core
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[voice,test]"
Set-Location ..\..
pnpm install
Copy-Item .env.example .env
```

Edit `.env` locally without printing it into logs. `LLM_PROVIDER=glm` requires `GLM_API_KEY` and the Coding base URL ending in `/api/coding/paas/v4`; `LLM_PROVIDER=deepseek` requires `DEEPSEEK_API_KEY`; `LLM_PROVIDER=mock` intentionally starts without a Provider Key. `AGENT_CORE_PORT` controls Core, `AGENT_CORE_WS_URL` controls Godot when explicitly supplied, and `VITE_AGENT_CORE_WS_URL` controls the optional web shell at build/dev time. Speech defaults are `STT_MODEL=small`, `STT_DEVICE=cpu`, and `STT_COMPUTE_TYPE=int8`.

## Local model setup

Place the independently obtained and processed runtime file at `apps/avatar-runtime/assets/luotianyi_v4.glb`, then run `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\check-local-assets.ps1`. The current accepted file is 128,621,144 bytes with SHA-256 `DF55806D343D149B41C20D0EF074373CAFCA2379212FD8691E998EA6CDDC6E4A`; if another legitimate source produces a different file, update the asset contract only after revalidating the skeleton, pigtail roots, 48 expressions and visual behavior.

## Run modes

| Mode | Command | Notes |
|---|---|---|
| Complete local MVP | Double-click `start-anime-agent.cmd` or run `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\start-mvp.ps1` | Reuses a healthy Core, prevents duplicate Avatar, validates selected Provider and starts Core hidden |
| Core only | `pnpm core:dev` | Foreground diagnostics; direct Python alternative is `.\services\agent-core\.venv\Scripts\python.exe -m agent_core.main` from `services/agent-core` |
| Avatar only | `pnpm avatar:dev` | Requires local GLB and a Godot candidate path recognized by the script |
| Avatar compact fallback | `$env:ANIME_AGENT_CANVAS_MODE='compact'; pnpm avatar:dev` | Restores the legacy 560×760 movable OS window for diagnostics; normal product runs should leave this variable unset |
| Model-look rollback | Set `ANIME_AGENT_MODEL_LOOK=1.1` in `.env`, then restart the Avatar | The one-click launcher restores the accepted 1.1 pixels; use `1.2` or remove the value for the current accepted look (`1.2-preview` remains a compatible legacy alias) |
| Browser debug shell | `pnpm dev:desktop` | Vite at `127.0.0.1:1420` |
| Tauri debug shell | `pnpm tauri:dev` | Optional; not the primary visible product |

Core health is `http://127.0.0.1:8765/health` and WebSocket is `ws://127.0.0.1:8765/ws` at defaults. Use `curl.exe --noproxy "*"` for localhost because machine proxy settings can otherwise create a false 502. Hidden Core logs are written to `%LOCALAPPDATA%\AnimeAgent\logs`; SQLite is under `%LOCALAPPDATA%\AnimeAgent\data` unless `ANIME_AGENT_DATA_DIR` overrides it.

## Interaction reference

| Input | Behavior |
|---|---|
| Left click | Open/close character menu |
| Left drag | Move the character within the desktop transparent canvas and save its normalized screen position |
| Right drag | Continuous yaw/turn |
| Mouse wheel | Zoom |
| Arrow/A/D, R | Turn or reset front |
| N, W, Space | Nod, wave, greet |
| B, S, O, X, L, T | Blink, smile, surprise, anger, wink, tears |
| F1 | Debug HUD |
| Esc | Exit Avatar |

The chat input receives normal keyboard events while focused; global Avatar shortcuts must not consume those events. The voice button records while held and returns editable transcript text rather than auto-sending it.

## TTS sidecar（E 期声线，可选组件）

天依声线由独立 sidecar 进程提供（GPT-SoVITS v2Pro，与 Core 完全隔离、自带 venv）。侧车源码与模型归 tianyi-tts 工作区（anime-agent-tts 私有仓库）管理，不在本仓库内。启动命令：

```powershell
& 'D:/UserData/Administrator/Documents/Codex/2026-08-28/https-github-com-summertianyi-anime-agent/work/tianyi-tts/venv/Scripts/python.exe' 'D:/UserData/Administrator/Documents/Codex/2026-08-28/https-github-com-summertianyi-anime-agent/work/tianyi-tts/scripts/tts_server.py' --port 8770
```

模型常驻约 3.5GB 显存；首次加载约 30-60 秒，就绪标志是日志输出 `TTS_SERVER_READY`，或 `GET http://127.0.0.1:8770/health` 返回 ok。Core 侧 .env 设 `ANIME_AGENT_TTS=1` 启用；侧车不在时聊天自动降级为文字-only。
