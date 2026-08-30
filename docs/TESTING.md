# Verification and acceptance

Run checks from the repository root unless the table says otherwise. The baseline checks are local and do not send paid Provider requests; the Bridge check does send chat through whichever Provider the running Core has configured, so use explicit Mock when an external request is not intended.

| Gate | Command | Pass condition |
|---|---|---|
| Python unit tests | `Set-Location services\agent-core; $env:PYTHONDONTWRITEBYTECODE='1'; .\.venv\Scripts\python.exe -m unittest discover -s tests -v; Set-Location ..\..` | 19 tests pass; catalog, prompt normalization, response parsing, safe Provider error detail and session storage/migration are covered |
| Frontend type/build | `pnpm build:desktop` | TypeScript and Vite build succeed; generated `dist` remains ignored |
| Asset contract | `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\check-local-assets.ps1` | Accepted path, size and SHA-256 print |
| Godot input/scene guard | `& '..\tools\godot-4.7.2\Godot_v4.7.2-stable_win64_console.exe' --headless --path apps\avatar-runtime --script res://verify_text_input.gd` | Prints `GODOT_AVATAR_INTERACTION_READY` and `GODOT_CHAT_SHORTCUT_GUARD_OK` with 48 expressions and two pigtail roots |
| Blender pigtail rig inspection | `& 'D:\steam\steamapps\common\Blender\blender.exe' -b --python scripts\model-pipeline\inspect_pigtails.py -- --input '..\luotianyi_v4_prepared.blend'` | Prints `PIGTAIL_INSPECTION_OK`; two continuous 17-bone chains, one deformed mesh and non-zero weights on all 34 bones |
| Blender motion retarget | `& 'D:\steam\steamapps\common\Blender\blender.exe' -b --python scripts\model-pipeline\verify_retarget.py -- --input '..\motion-output\cmu-pirouette\luotianyi_pirouette.blend' --action cmu_pirouette` | Prints `RETARGET_VERIFY_OK`; 149 frames, 19 core bones, finite transforms and ≤1 mm foot-ground drift |
| Godot motion import | `& '..\tools\godot-4.7.2\Godot_v4.7.2-stable_win64_console.exe' --headless --path apps\avatar-runtime --script res://verify_motion_asset.gd` | Prints `GODOT_MOTION_ASSETS_OK`; idle and pirouette each contain one valid clip on the 751-bone rig |
| Godot motion runtime | `& '..\tools\godot-4.7.2\Godot_v4.7.2-stable_win64_console.exe' --headless --path apps\avatar-runtime --script res://verify_motion_runtime.gd` | Prints `GODOT_MOTION_RUNTIME_OK`; upper idle excludes lower-body bones, both pigtail chains stay upper-only with root/tip sway, pirouette interrupts idle, static visual model is preserved and playback returns to idle |
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
| Authored motion | Press `P`, then use character → Interaction → Pirouette sample; press `R` during playback | The 4.967-second full-body clip plays on the normal-material model, feet do not visibly float, completion/cancel returns to idle and chat input remains editable |
| Authored idle | Leave the Avatar untouched for at least 16 seconds, then trigger and finish another action | Subtle breathing/head motion loops twice without a visible seam or foot movement; interaction returns to idle automatically |
| Character behavior | Ask identity, limitations and an original-song question | It speaks as Luo Tianyi, does not claim to be a generic assistant, respects unavailable senses/actions, and uses matching catalog facts without claiming Producer credit |
| Voice/STT | Hold Voice for 3–10 seconds of normal Mandarin, release and repeat across several trials | Transcript reliably fills the editable input; no crash/hang; failures explain device/audio cause rather than silently doing nothing |
| Persistence | Send messages, stop/restart Core, inspect behavior without exposing DB content | Recent conversation reloads and DB remains under LocalAppData |
| Sessions | Open chat, tap ＋新对话, send messages, then switch back to the old session from the dropdown | Bubbles clear on switch, each session reloads its own history, and the dropdown sorts by recent activity |
| Chat overlay input priority | Open chat, wheel over the bubble area, then wheel outside the panel, then right-drag on the panel | Bubble area scrolls history, wheel outside the panel still zooms the character, and right-drag on the panel never rotates |

The current handoff passes all local automated baseline checks; `.github/workflows/ci.yml` repeats Core tests and the desktop build on Windows without requiring the local model. Text chat, sessions and real GLM were manually exercised. Voice/STT was previously blocked by a Realtek microphone-array driver wedge (the device keeps delivering digital zeros until an external event such as the Windows mic test resets it); it passed one manual round after reset, but self-healing hardening in `voice.py` is still pending. For a bug fix, add or strengthen the narrowest regression test before claiming completion.
