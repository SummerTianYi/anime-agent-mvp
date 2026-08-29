# Verification and acceptance

Run checks from the repository root unless the table says otherwise. The baseline checks are local and do not send paid Provider requests; the Bridge check does send chat through whichever Provider the running Core has configured, so use explicit Mock when an external request is not intended.

| Gate | Command | Pass condition |
|---|---|---|
| Python unit tests | `Set-Location services\agent-core; $env:PYTHONDONTWRITEBYTECODE='1'; .\.venv\Scripts\python.exe -m unittest discover -s tests -v; Set-Location ..\..` | 11 tests pass; catalog, prompt normalization, response parsing and safe Provider error detail are covered |
| Frontend type/build | `pnpm build:desktop` | TypeScript and Vite build succeed; generated `dist` remains ignored |
| Asset contract | `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\check-local-assets.ps1` | Accepted path, size and SHA-256 print |
| Godot input/scene guard | `& '..\tools\godot-4.7.2\Godot_v4.7.2-stable_win64_console.exe' --headless --path apps\avatar-runtime --script res://verify_text_input.gd` | Prints `GODOT_AVATAR_INTERACTION_READY` and `GODOT_CHAT_SHORTCUT_GUARD_OK` with 48 expressions and two pigtail roots |
| Core health | `curl.exe --noproxy "*" -sS http://127.0.0.1:8765/health` | JSON contains `status=ok`, expected Provider/runtime/model and current client roles |
| Bridge routing | `.\services\agent-core\.venv\Scripts\python.exe .\scripts\verify-avatar-bridge.py` | Prints `bridge=ok`, thinking→speaking→idle, chat response, menu routing and Avatar command routing |
| Repository whitespace | `git diff --check` | No errors |
| Tracked large files | `git ls-files | ForEach-Object { Get-Item -LiteralPath $_ } | Where-Object Length -gt 50MB` | No output unless explicitly reviewed |
| Ignored boundaries | `git status --ignored --short` | `.env`, model assets, caches, databases, logs and dependency/build outputs stay ignored; static song JSON and asset README stay trackable |

## Manual MVP acceptance

| Scenario | Procedure | Accepted when |
|---|---|---|
| One-click launch | Stop current Avatar/Core, run `start-anime-agent.cmd`, then run it again | First run launches one Core/Avatar; second run reuses them without duplicate or port error |
| Text chat | Click character → Chat, type Chinese text containing Avatar shortcut letters, press Enter | Text is editable, shortcuts do not fire, user message appears and a character-consistent Provider reply returns |
| 3D interaction | Drag left/right, rotate, zoom, trigger menu actions, restart Avatar | Movement is usable, rear view works, position persists, actions return to idle and no major hair/body clipping appears |
| Character behavior | Ask identity, limitations and an original-song question | It speaks as Luo Tianyi, does not claim to be a generic assistant, respects unavailable senses/actions, and uses matching catalog facts without claiming Producer credit |
| Voice/STT | Hold Voice for 3–10 seconds of normal Mandarin, release and repeat across several trials | Transcript reliably fills the editable input; no crash/hang; failures explain device/audio cause rather than silently doing nothing |
| Persistence | Send messages, stop/restart Core, inspect behavior without exposing DB content | Recent conversation reloads and DB remains under LocalAppData |

The current handoff passes all local automated baseline checks; `.github/workflows/ci.yml` repeats Core tests and the desktop build on Windows without requiring the local model. Text chat and real GLM were manually exercised, while voice/STT remains unaccepted. For a bug fix, add or strengthen the narrowest regression test before claiming completion.
