# Architecture and contracts

## Runtime topology

```text
User mouse / keyboard / microphone
              │
              ▼
Godot Avatar Runtime ── localhost WebSocket ── Python Agent Core ── HTTPS ── GLM / DeepSeek
   │          │                                      │
   │          └─ menu, chat, actions                 ├─ Character Harness + song retrieval
   └─ GLB, bones, expressions                        ├─ microphone + faster-whisper
                                                     ├─ tool loop + permission engine + MCP host
                                                     ├─ SQLite messages/events/facts/settings
                                                     └─ TTS sidecar (HTTP, GPT-SoVITS, separate venv)

Optional React/Tauri shell ── localhost WebSocket ───┘
```

The Core is the only component that talks to LLM Providers or opens the microphone; the Avatar owns visible character interaction and rendering; Tauri is an optional diagnostics/settings surface and must not displace the Avatar. Default network exposure is loopback only. `AGENT_CORE_PORT` selects the Core port, `AGENT_CORE_WS_URL` is passed to Godot, and `VITE_AGENT_CORE_WS_URL` can override the optional web shell URL.

The desktop Avatar does not move the 3D model away from the camera optical axis. Godot renders the model, camera, environment and lights into a fixed-aspect 1920×2320 SubViewport, downsamples it to a 960×1160 transparent composite, and moves only that 2D composite across the full working-area canvas. The derived FOV preserves the accepted 3.8-unit perspective and original apparent model size while leaving extra transparent margin for large gestures and maximum zoom; click-through remains driven by the smaller dynamic character/menu hull rather than the composite rectangle. Procedural gestures derive local axes from the MMD rest pose, while an action-independent camera-space guard prevents animated arm segments from collapsing edge-on into a few pixels. The runtime processes after the child AnimationPlayer so these corrections survive authored playback; full-body clips also mirror standard MMD leg-control deltas into the parallel D deform chain that actually carries mesh weights. Both mechanisms change only runtime bone poses and can be disabled per authored clip with `sync_mmd_deform_bones: false`; the official GLB remains byte-identical. Menu and interaction panels dynamically choose the free side of the avatar instead of covering its body.

## Component contracts

| Component | Inputs | Outputs | Persistent state |
|---|---|---|---|
| Godot runtime | Pointer/keyboard, Core events, local GLB | Chat/voice/interaction events, rendered character | `user://avatar_window.cfg` |
| Agent Core | WebSocket JSON, `.env`, Provider HTTP responses, microphone samples | Directed WebSocket events, Provider requests, logs | SQLite under `%LOCALAPPDATA%\AnimeAgent\data` |
| Character Harness | Recent history, user text, matching song records | Provider messages and parsed `AgentReply` | None; code and static JSON are versioned |
| Song catalog | User query and tracked song JSON | Up to six ranked factual records | `agent_core/data/luotianyi_original_songs.json` |
| Permission engine | Tool invocation requests from the agent loop | allow/ask/deny decisions, audit events, parked in-chat confirmations | None; rules from code plus `ANIME_AGENT_*` env |
| TTS sidecar (separate venv) | Synthesis HTTP requests from Core | wav artifacts, utterance lifecycle | Local spool directory |
| Tauri shell | Browser input and Core events | `chat.message`, diagnostic display | None in current MVP |

## Chat and behavior sequence

| Order | Event/action | Owner |
|---|---|---|
| 1 | Client connects, receives `core.status`, sends `client.hello` with role `avatar` or `ui` | Client/Core |
| 2 | Avatar sends `chat.message` with `text` and `messageId` | Godot |
| 3 | Core serializes chat work, records user message and broadcasts `agent.state=thinking` | Core |
| 4 | Harness builds a system prompt, injects relevant original-song records and normalizes assistant history to the JSON contract | Harness |
| 5 | Provider returns JSON or plain text; parser clamps emotion intensity and whitelists gestures | Provider/Harness |
| 6 | Core records assistant text, emits `chat.response`, then `agent.state=speaking`, directed `avatar.command` events and finally `idle` | Core |
| 7 | Godot updates chat history, expression, mouth shape and procedural action | Godot |

The Provider output contract is `{"reply":"...","emotion":"neutral|happy|thinking|surprised|sad|angry|shy","emotion_intensity":0.0,"gesture":"none|nod|wave|greet|turn_left|turn_right","memory_candidate":null}`. Plain text remains usable as a neutral/no-gesture fallback; invalid emotions or gestures are dropped, and `memory_candidate` is truncated to 200 characters and promoted tier-wise into the `facts` table (preference-class auto-confirmed, explicit "记住" forces confirmation, the rest pending), from which lexical retrieval injects relevant facts into chat prompts; a newly confirmed fact supersedes a near-duplicate confirmed one (status superseded), and non-sensitive pending facts are injected tagged （待确认）.

## Persistence and trust boundary

| Data | Location | Git policy | Current use |
|---|---|---|---|
| API credentials | Repository-root `.env` or process environment | Ignored; never print or commit | Provider authentication |
| Message/event database | `%LOCALAPPDATA%\AnimeAgent\data\anime-agent.sqlite3` by default | Local-only | Recent history, diagnostics and pending memory candidates |
| Core logs | `%LOCALAPPDATA%\AnimeAgent\logs` | Local-only | Hidden-process startup diagnostics |
| Song facts | Tracked package JSON | Commit | Retrieval context; no lyrics |
| Character model | `apps/avatar-runtime/assets/luotianyi_v4.glb` | Ignored | Godot scene dependency |
| Window location | Godot `user://avatar_window.cfg` | Local-only | Restores desktop position |

External-action capability is gated by the three-tier permission engine (`agent_core/permissions.py`: allow/ask/deny, deny-by-default, path-safety hard-deny, `permission.decision` audit events in the events table); write/command/privacy tools default to ask and park in the in-chat confirmation flow until the user confirms in chat. Any new tool must register in `tools.py`, declare its tier, and pass the same gate — a tool that bypasses it is a security regression.
