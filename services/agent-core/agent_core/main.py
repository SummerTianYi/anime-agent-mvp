from __future__ import annotations

import asyncio
import io
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Literal, Protocol

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect

ENV_PATH = Path(__file__).resolve().parents[3] / ".env"

try:
    from dotenv import load_dotenv

    load_dotenv(ENV_PATH)
except ImportError:
    pass

from .agent_loop import AgentStep, ToolsUnsupportedError, run_agent_loop
from .harness import (
    TOOL_GUIDANCE,
    AgentReply,
    CharacterHarness,
    behavior_events,
    default_title,
)
from .speech import SpeechClient, SpeechManager, SpeechUnavailable, speech_settings_from_env
from .storage import MemoryStore
from .tools import build_tool_registry, execute_tool, openai_tools_schema
from .voice import VoiceError, VoiceRecorder, transcribe_wav
from .wake_word import WakeWordListener, capture_utterance, encode_wav, is_wake_phrase

AgentState = Literal["idle", "thinking", "speaking", "working", "error"]

HOST = os.getenv("AGENT_CORE_HOST", "127.0.0.1")
PORT = int(os.getenv("AGENT_CORE_PORT", "8765"))
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "glm").strip().lower()
LLM_TIMEOUT_SECONDS = float(os.getenv("LLM_TIMEOUT_SECONDS", "45"))
MAX_HISTORY_MESSAGES = 20
TOOLS_ENABLED = os.getenv("ANIME_AGENT_TOOLS", "1").strip().lower() not in {"0", "false", "off"}
SPEECH_SETTINGS = speech_settings_from_env()
TTS_ENABLED = SPEECH_SETTINGS["enabled"]
TTS_NARRATE = SPEECH_SETTINGS["narrate"]
NARRATION_LINE = "我看到了，稍等我整理一下~"

app = FastAPI(title="Anime Agent Core", version="0.2.0")

AVATAR_EVENTS = {
    "avatar.turn_left",
    "avatar.turn_right",
    "avatar.reset",
    "avatar.nod",
    "avatar.wave",
    "avatar.greet",
    "avatar.blink",
    "avatar.smile",
    "avatar.surprised",
    "avatar.angry",
    "avatar.wink",
    "avatar.tears",
    "avatar.mouth_a",
    "avatar.mouth_i",
    "avatar.mouth_u",
    "avatar.mouth_e",
    "avatar.mouth_o",
    "avatar.expression",
}


class ProviderError(RuntimeError):
    """An expected provider failure safe to show in the local UI."""


class ChatProvider(Protocol):
    name: str
    configured: bool

    async def complete(self, messages: list[dict[str, str]]) -> str:
        ...


class MockProvider:
    name = "mock"
    configured = False

    async def complete(self, messages: list[dict[str, str]]) -> str:
        user_text = next(
            (item["content"] for item in reversed(messages) if item["role"] == "user"),
            "",
        )
        return f"我听到了：{user_text}\n\n当前没有配置可用的模型 API Key，正在使用本地 Mock 回复。"


class OpenAICompatibleProvider:
    def __init__(
        self,
        *,
        name: str,
        base_url: str,
        model: str,
        api_key: str,
        timeout_seconds: float,
        reload_config: Callable[[], tuple[str, str, str] | None] | None = None,
    ) -> None:
        self.name = name
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds
        self.configured = bool(api_key)
        self._reload_config = reload_config

    @property
    def completion_url(self) -> str:
        if self.base_url.endswith("/chat/completions"):
            return self.base_url
        return f"{self.base_url}/chat/completions"

    def _apply_config(self, base_url: str, model: str, api_key: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.configured = bool(api_key)

    async def _send_with_config_reload(self, request: urllib.request.Request) -> bytes:
        """POST the request; on 401/403/429 re-read .env credentials and retry once.

        load_dotenv runs once at startup, so a key swapped into .env reaches the
        running process only through a fresh file read. The retry reuses the
        same request with a refreshed Authorization header; base_url or model changes
        apply from the next request."""
        for attempt in (0, 1):
            try:
                if attempt == 1:
                    refreshed = f"Bearer {self.api_key}"
                    request.add_header("Authorization", refreshed)
                    request.add_unredirected_header("Authorization", refreshed)
                return await asyncio.to_thread(self._request, request)
            except urllib.error.HTTPError as exc:
                if (
                    attempt == 0
                    and exc.code in RELOADABLE_HTTP_CODES
                    and self._reload_config is not None
                ):
                    fresh = await asyncio.to_thread(self._reload_config)
                    if fresh is not None and (
                        fresh[0].rstrip("/") != self.base_url
                        or fresh[1] != self.model
                        or fresh[2] != self.api_key
                    ):
                        self._apply_config(fresh[0], fresh[1], fresh[2])
                        continue
                raise
        raise ProviderError(f"{self.name} API request failed")

    async def complete(self, messages: list[dict[str, str]]) -> str:
        if not self.api_key:
            raise ProviderError(f"{self.name} API Key 未配置")

        request_body = json.dumps(
            {
                "model": self.model,
                "messages": messages,
                "stream": False,
            },
            ensure_ascii=False,
        ).encode("utf-8")
        request = urllib.request.Request(
            self.completion_url,
            data=request_body,
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            response_bytes = await self._send_with_config_reload(request)
        except urllib.error.HTTPError as exc:
            detail = self._http_error_detail(exc)
            suffix = f"：{detail}" if detail else ""
            raise ProviderError(
                f"{self.name} API 返回 HTTP {exc.code}{suffix}"
            ) from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise ProviderError(f"无法连接 {self.name} API") from exc

        try:
            payload = json.loads(response_bytes.decode("utf-8"))
            content = payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise ProviderError(f"{self.name} API 响应格式无法识别") from exc

        if isinstance(content, list):
            content = "".join(
                str(part.get("text", ""))
                for part in content
                if isinstance(part, dict)
            )
        text = str(content).strip()
        if not text:
            raise ProviderError(f"{self.name} API 返回空回复")
        return text

    async def complete_with_tools(self, messages: list[dict[str, str]], tools: list[dict]) -> dict:
        """One tool-capable turn; returns content/tool_calls plus the raw assistant message."""
        if not self.api_key:
            raise ProviderError(f"{self.name} API Key 未配置")

        request_body = json.dumps(
            {
                "model": self.model,
                "messages": messages,
                "stream": False,
                "tools": tools,
                "tool_choice": "auto",
            },
            ensure_ascii=False,
        ).encode("utf-8")
        request = urllib.request.Request(
            self.completion_url,
            data=request_body,
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            response_bytes = await self._send_with_config_reload(request)
        except urllib.error.HTTPError as exc:
            if exc.code in {400, 404, 422}:
                raise ToolsUnsupportedError(
                    f"{self.name} rejected the tools payload (HTTP {exc.code})"
                ) from exc
            detail = self._http_error_detail(exc)
            suffix = f"：{detail}" if detail else ""
            raise ProviderError(
                f"{self.name} API 返回 HTTP {exc.code}{suffix}"
            ) from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise ProviderError(f"无法连接 {self.name} API") from exc

        try:
            payload = json.loads(response_bytes.decode("utf-8"))
            message = payload["choices"][0]["message"]
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise ProviderError(f"{self.name} API 响应格式无法识别") from exc

        content = message.get("content")
        if isinstance(content, list):
            content = "".join(
                str(part.get("text", ""))
                for part in content
                if isinstance(part, dict)
            )
        text = str(content).strip() if content else ""

        tool_calls: list[dict] = []
        for index, call in enumerate(message.get("tool_calls") or []):
            function = call.get("function") or {}
            raw_arguments = function.get("arguments")
            if isinstance(raw_arguments, str):
                try:
                    arguments = json.loads(raw_arguments)
                except json.JSONDecodeError:
                    arguments = {}
            elif isinstance(raw_arguments, dict):
                arguments = raw_arguments
            else:
                arguments = {}
            if not isinstance(arguments, dict):
                arguments = {}
            tool_calls.append(
                {
                    "id": str(call.get("id") or f"call_{index}"),
                    "name": str(function.get("name", "")).strip(),
                    "arguments": arguments,
                }
            )
        return {"content": text, "tool_calls": tool_calls, "raw": message}

    @staticmethod
    def _http_error_detail(exc: urllib.error.HTTPError) -> str:
        try:
            payload = json.loads(exc.read().decode("utf-8", "replace"))
            error = payload.get("error", {})
            message = error.get("message", "") if isinstance(error, dict) else ""
        except (AttributeError, TypeError, json.JSONDecodeError, OSError):
            return ""
        return " ".join(str(message).split())[:240]

    def _request(self, request: urllib.request.Request) -> bytes:
        hostname = urllib.parse.urlparse(request.full_url).hostname
        if hostname in {"127.0.0.1", "localhost"}:
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        else:
            opener = urllib.request.build_opener()
        with opener.open(request, timeout=self.timeout_seconds) as response:
            return response.read()


RELOADABLE_HTTP_CODES = frozenset({401, 403, 429})


def _parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    try:
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            values[key.strip()] = value.strip().strip('"').strip("'")
    except OSError:
        return {}
    return values


def _reload_provider_config(name: str, env_path: Path | None = None) -> tuple[str, str, str] | None:
    """Re-read provider credentials from the .env file after an auth/quota failure.

    os.environ went stale at startup (load_dotenv runs once), so the file
    itself is the source of truth for manual key swaps; entries missing from
    the file fall back to the startup environment. Returns None when no key
    can be found anywhere.
    """
    values = _parse_env_file(env_path if env_path is not None else ENV_PATH)
    if name == "deepseek":
        prefix, default_base_url, default_model = "DEEPSEEK", "https://api.deepseek.com", "deepseek-chat"
    else:
        prefix, default_base_url, default_model = "GLM", "https://open.bigmodel.cn/api/coding/paas/v4", "glm-5.3-flash"

    def pick(suffix: str) -> str:
        return values.get(f"{prefix}_{suffix}") or os.getenv(f"{prefix}_{suffix}", "")

    api_key = pick("API_KEY")
    if not api_key:
        return None
    return pick("BASE_URL") or default_base_url, pick("MODEL") or default_model, api_key


def _provider_config(name: str) -> tuple[str, str, str]:
    if name == "deepseek":
        return (
            os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
            os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
            os.getenv("DEEPSEEK_API_KEY", ""),
        )
    return (
        os.getenv("GLM_BASE_URL", "https://open.bigmodel.cn/api/coding/paas/v4"),
        os.getenv("GLM_MODEL", "glm-5.3-flash"),
        os.getenv("GLM_API_KEY", ""),
    )


def build_provider() -> ChatProvider:
    if LLM_PROVIDER not in {"glm", "deepseek"}:
        return MockProvider()
    base_url, model, api_key = _provider_config(LLM_PROVIDER)
    if not api_key:
        return MockProvider()
    return OpenAICompatibleProvider(
        name=LLM_PROVIDER,
        base_url=base_url,
        model=model,
        api_key=api_key,
        timeout_seconds=LLM_TIMEOUT_SECONDS,
    )


provider = build_provider()
chat_lock = asyncio.Lock()
voice_recorder = VoiceRecorder()
wake_listener: WakeWordListener | None = None
_wake_busy = False
_agent_state = "idle"
memory = MemoryStore()
harness = CharacterHarness()
tool_registry = build_tool_registry()
tools_schema = openai_tools_schema(tool_registry) if TOOLS_ENABLED else []


class ConnectionHub:
    def __init__(self) -> None:
        self._clients: set[WebSocket] = set()
        self._roles: dict[WebSocket, str] = {}
        self._send_locks: dict[WebSocket, asyncio.Lock] = {}

    @property
    def client_count(self) -> int:
        return len(self._clients)

    def role_count(self, role: str) -> int:
        return sum(client_role == role for client_role in self._roles.values())

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._clients.add(websocket)
        self._roles[websocket] = "unknown"
        self._send_locks[websocket] = asyncio.Lock()

    def disconnect(self, websocket: WebSocket) -> None:
        self._clients.discard(websocket)
        self._roles.pop(websocket, None)
        self._send_locks.pop(websocket, None)

    def set_role(self, websocket: WebSocket, role: str) -> None:
        if websocket in self._clients:
            self._roles[websocket] = role

    async def send(self, websocket: WebSocket, payload: dict[str, object]) -> None:
        lock = self._send_locks.get(websocket)
        if lock is None:
            return
        async with lock:
            await websocket.send_json(payload)

    async def send_roles(self, roles: set[str], payload: dict[str, object]) -> None:
        stale_clients: list[WebSocket] = []
        for client in tuple(self._clients):
            if self._roles.get(client) not in roles:
                continue
            try:
                await self.send(client, payload)
            except (RuntimeError, WebSocketDisconnect):
                stale_clients.append(client)
        for client in stale_clients:
            self.disconnect(client)


hub = ConnectionHub()


async def _broadcast_speak(payload: dict[str, object]) -> None:
    await hub.send_roles({"avatar", "ui"}, event("avatar.speak", **payload))
    await broadcast_state("speaking", str(payload.get("requestId", "")))


async def _broadcast_speech_stop(utterance_id: str, reason: str) -> None:
    await hub.send_roles(
        {"avatar", "ui"},
        event("avatar.speech.stop", utteranceId=utterance_id, reason=reason),
    )
    memory.add_event("speech.interrupted", {"utteranceId": utterance_id, "reason": reason})


speech_client = SpeechClient(SPEECH_SETTINGS["url"])
speech_manager = SpeechManager(
    speech_client,
    on_speak=_broadcast_speak,
    on_interrupt=_broadcast_speech_stop,
)


def _make_loop_step_handler(request_id: str):
    """Broadcast tool steps; narrate on the first tool step when TTS is live."""
    narrated = {"done": False}

    async def handler(step: AgentStep) -> None:
        await broadcast_tool_step(step, request_id)
        if narrated["done"]:
            return
        narrated["done"] = True
        if not (TTS_ENABLED and TTS_NARRATE and hub.role_count("avatar") > 0):
            return
        asyncio.create_task(_speak_reply(NARRATION_LINE, request_id, narrating=True))

    return handler


async def _speak_reply(text: str, request_id: str, narrating: bool = False) -> None:
    """Synthesize + broadcast one utterance outside the chat lock, then settle state."""
    try:
        utterance = await speech_manager.speak(text, request_id)
    except SpeechUnavailable:
        utterance = None
    if utterance is None or not utterance.has_audio:
        await broadcast_state("speaking", request_id)
        await asyncio.sleep(min(1.2, max(0.35, len(text) / 55.0)))
        await broadcast_state("working" if narrating else "idle", request_id)
        return
    if speech_manager.current is None:
        await broadcast_state("working" if narrating else "idle", request_id)


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def event(event_type: str, **payload: object) -> dict[str, object]:
    return {"type": event_type, "timestamp": timestamp(), **payload}


async def broadcast_state(state: AgentState, request_id: str = "") -> None:
    global _agent_state
    _agent_state = state
    memory.add_event("agent.state", {"state": state, "request_id": request_id})
    await hub.send_roles(
        {"avatar", "ui"},
        event("agent.state", state=state, request_id=request_id),
    )


async def broadcast_behavior(reply: AgentReply) -> None:
    for command, command_payload in behavior_events(reply):
        await hub.send_roles(
            {"avatar"},
            event("avatar.command", event=command, payload=command_payload),
        )


async def run_tool(name: str, arguments: dict) -> dict:
    return await execute_tool(tool_registry, name, arguments)


async def broadcast_tool_step(step: AgentStep, request_id: str) -> None:
    await hub.send_roles(
        {"avatar", "ui"},
        event(
            "agent.tool",
            tool=step.tool,
            ok=step.ok,
            summary=step.summary,
            request_id=request_id,
        ),
    )
    await broadcast_state("working", request_id)


async def handle_chat(text: str, request_id: str, conversation_id: int | None = None) -> None:

    async with chat_lock:
        await broadcast_state("thinking", request_id)
        probe = conversation_id if conversation_id is not None else memory.latest_session_id()
        is_first_exchange = probe is None or not memory.load_messages(1, probe)
        session_id = memory.add_message("user", text, request_id, conversation_id)
        conversation_history = memory.load_messages(MAX_HISTORY_MESSAGES, session_id)
        guided = TOOL_GUIDANCE if tools_schema else ""
        messages = harness.build_messages(
            conversation_history, text, extra_system=guided, request_session_title=is_first_exchange
        )
        try:
            if tools_schema:
                loop_result = await run_agent_loop(
                    provider,
                    messages,
                    tools_schema,
                    run_tool,
                    on_step=_make_loop_step_handler(request_id),
                )
                if loop_result.degraded and hasattr(provider, "complete_with_tools"):
                    memory.add_event("agent.tools.unsupported", {"request_id": request_id})
                if loop_result.steps:
                    memory.add_event(
                        "agent.tools",
                        {
                            "request_id": request_id,
                            "tools": [step.tool for step in loop_result.steps],
                            "ok": [step.ok for step in loop_result.steps],
                        },
                    )
                raw_reply = loop_result.text
            else:
                raw_reply = await provider.complete(messages)
        except ProviderError as exc:
            memory.add_event("core.error", {"message": str(exc), "request_id": request_id})
            await hub.send_roles(
                {"avatar", "ui"},
                event("core.error", message=str(exc), request_id=request_id),
            )
            await broadcast_state("error", request_id)
            await asyncio.sleep(0.4)
            await broadcast_state("idle", request_id)
            return

        agent_reply = harness.parse_reply(raw_reply)
        memory.add_message("assistant", agent_reply.reply, request_id, session_id)
        if is_first_exchange:
            title = agent_reply.session_title or default_title(text)
            if title and memory.rename_session(session_id, title):
                await hub.send_roles(
                    {"avatar", "ui"},
                    event("session.title", conversationId=session_id, title=title),
                )
        if agent_reply.memory_candidate:
            memory.add_event(
                "memory.candidate",
                {
                    "fact": agent_reply.memory_candidate,
                    "request_id": request_id,
                    "status": "pending",
                },
            )
        await hub.send_roles(
            {"avatar", "ui"},
            event(
                "chat.response",
                conversationId=session_id,
                text=agent_reply.reply,
                emotion=agent_reply.emotion,
                emotion_intensity=agent_reply.emotion_intensity,
                gesture=agent_reply.gesture,
                request_id=request_id,
            ),
        )
        use_tts = (
            TTS_ENABLED
            and hub.role_count("avatar") > 0
            and await asyncio.to_thread(speech_client.is_healthy)
        )
        if use_tts:
            await broadcast_behavior(agent_reply)
            asyncio.create_task(_speak_reply(agent_reply.reply, request_id))
            return
        await broadcast_state("speaking", request_id)
        await broadcast_behavior(agent_reply)
        await asyncio.sleep(min(1.2, max(0.35, len(agent_reply.reply) / 55.0)))
        await broadcast_state("idle", request_id)


async def handle_voice_transcription(audio_bytes: bytes) -> None:
    await hub.send_roles({"avatar", "ui"}, event("voice.state", state="transcribing"))
    try:
        text = await asyncio.to_thread(transcribe_wav, audio_bytes)
    except VoiceError as exc:
        await hub.send_roles({"avatar", "ui"}, event("core.error", message=str(exc)))
        await hub.send_roles({"avatar", "ui"}, event("voice.state", state="idle"))
        return
    await hub.send_roles({"avatar", "ui"}, event("voice.transcript", text=text))
    await hub.send_roles({"avatar", "ui"}, event("voice.state", state="idle"))


async def handle_wake_word(buffered_audio) -> None:
    global _wake_busy
    if _wake_busy or voice_recorder.recording or _agent_state != "idle":
        memory.add_event("wake.busy", {"state": _agent_state})
        return
    _wake_busy = True
    if wake_listener is not None:
        wake_listener.pause()
    try:
        if buffered_audio is None:
            return
        await hub.send_roles({"avatar", "ui"}, event("voice.state", state="transcribing"))
        try:
            wake_text = await asyncio.to_thread(transcribe_wav, encode_wav(buffered_audio))
        except VoiceError as exc:
            await hub.send_roles({"avatar", "ui"}, event("voice.state", state="idle"))
            await hub.send_roles({"avatar", "ui"}, event("core.error", message=str(exc)))
            return
        await hub.send_roles({"avatar", "ui"}, event("voice.state", state="idle"))
        if not is_wake_phrase(wake_text):
            memory.add_event("wake.rejected", {"text": wake_text})
            return
        session = memory.create_session()
        await hub.send_roles({"avatar", "ui"}, event("session.switched", conversationId=session["id"], title=session["title"]))
        await speech_manager.interrupt("wake")
        await hub.send_roles({"avatar", "ui"}, event("wake.triggered", conversationId=session["id"]))
        await hub.send_roles({"avatar", "ui"}, event("voice.state", state="recording"))
        try:
            command_bytes = await asyncio.to_thread(capture_utterance)
        except VoiceError as exc:
            await hub.send_roles({"avatar", "ui"}, event("core.error", message=str(exc)))
            await hub.send_roles({"avatar", "ui"}, event("voice.state", state="idle"))
            return
        if command_bytes is not None:
            await hub.send_roles({"avatar", "ui"}, event("voice.state", state="transcribing"))
            try:
                command_text = await asyncio.to_thread(transcribe_wav, command_bytes)
            except VoiceError:
                command_text = ""
            await hub.send_roles({"avatar", "ui"}, event("voice.state", state="idle"))
            if command_text.strip():
                request_id = "wake-" + str(int(datetime.now().timestamp() * 1000))
                await hub.send_roles({"avatar", "ui"}, event("chat.user_message", conversationId=session["id"], text=command_text))
                asyncio.create_task(handle_chat(command_text, request_id, conversation_id=session["id"]))
                return
        await hub.send_roles({"avatar", "ui"}, event("wake.idle"))
    finally:
        _wake_busy = False
        if wake_listener is not None:
            wake_listener.resume()


@app.on_event("startup")
async def start_wake_word_listener() -> None:
    global wake_listener
    if os.getenv("ANIME_AGENT_WAKE_WORD", "1").strip().lower() in {"0", "false", "off"}:
        return
    loop = asyncio.get_running_loop()

    def on_detected(buffered_audio) -> None:
        asyncio.run_coroutine_threadsafe(handle_wake_word(buffered_audio), loop)

    def on_note(note: str) -> None:
        memory.add_event("wake.note", {"note": note})

    try:
        listener = WakeWordListener(on_detected=on_detected, on_note=on_note)
    except VoiceError as exc:
        memory.add_event("wake.disabled", {"reason": str(exc)})
        return
    listener.start()
    wake_listener = listener
    memory.add_event("wake.enabled", {"keyword": "嗨天依"})


@app.post("/wake-test")
async def wake_test(request: Request) -> dict[str, object]:
    """Diagnostic: feed a WAV body through the live wake pipeline."""
    import numpy as _np
    import wave as _wave
    body = await request.body()
    if not body:
        return {"ok": False, "reason": "empty body"}
    reader = _wave.open(io.BytesIO(body), "rb")
    rate = reader.getframerate()
    raw = reader.readframes(reader.getnframes())
    reader.close()
    samples = _np.frombuffer(raw, dtype=_np.int16).astype(_np.float32) / 32768.0
    if rate != 16000 and len(samples):
        count = int(len(samples) * 16000 / rate)
        samples = _np.interp(
            _np.linspace(0.0, len(samples) - 1.0, count),
            _np.arange(len(samples), dtype=_np.float64),
            samples.astype(_np.float64),
        ).astype(_np.float32)
    asyncio.create_task(handle_wake_word(samples))
    return {"ok": True, "queued": True, "samples": int(len(samples))}


@app.get("/health")
async def health() -> dict[str, object]:
    return {
        "status": "ok",
        "service": "anime-agent-core",
        "version": "0.2.0",
        "timestamp": timestamp(),
        "clients": hub.client_count,
        "roles": {
            "avatar": hub.role_count("avatar"),
            "ui": hub.role_count("ui"),
        },
        "llm": {
            "provider": LLM_PROVIDER,
            "runtime": provider.name,
            "configured": provider.configured,
            "model": getattr(provider, "model", "mock"),
        },
        "memory": {"path": str(memory.path), "enabled": True},
        "tools": {"enabled": TOOLS_ENABLED, "count": len(tools_schema)},
        "tts": {
            "enabled": TTS_ENABLED,
            "narrate": TTS_NARRATE,
            "service": SPEECH_SETTINGS["url"],
            "available": await asyncio.to_thread(speech_client.is_healthy) if TTS_ENABLED else False,
        },
        "wake": {
            "enabled": wake_listener is not None,
            "running": bool(wake_listener and wake_listener.running),
            "paused": bool(wake_listener and wake_listener.paused),
            "recent_peak": wake_listener.recent_peak if wake_listener else 0.0,
        },
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await hub.connect(websocket)
    await hub.send(websocket, event("core.status", status="online"))

    try:
        while True:
            payload = await websocket.receive_json()
            event_type = payload.get("type")

            if event_type == "ping":
                await hub.send(websocket, event("pong"))
                continue

            if event_type == "client.hello":
                role = str(payload.get("role", "unknown")).strip() or "unknown"
                hub.set_role(websocket, role)
                await hub.send(websocket, event("client.ready", role=role))
                continue

            if event_type == "avatar.interaction":
                interaction = str(payload.get("event", "")).strip()
                interaction_payload = payload.get("payload", {})
                if interaction != "avatar.clicked" or not isinstance(interaction_payload, dict):
                    await hub.send(websocket, event("core.error", message="Invalid avatar interaction"))
                    continue
                await hub.send_roles(
                    {"ui"},
                    event("ui.menu.toggle", payload=interaction_payload),
                )
                continue

            if event_type == "voice.start":
                if TTS_ENABLED:
                    await speech_manager.interrupt("voice")
                if wake_listener is not None:
                    wake_listener.pause()
                try:
                    voice_recorder.start()
                except VoiceError as exc:
                    await hub.send(websocket, event("core.error", message=str(exc)))
                else:
                    await hub.send_roles({"avatar", "ui"}, event("voice.state", state="recording"))
                continue

            if event_type == "voice.stop":
                try:
                    audio_bytes = voice_recorder.stop()
                except VoiceError as exc:
                    await hub.send(websocket, event("core.error", message=str(exc)))
                else:
                    asyncio.create_task(handle_voice_transcription(audio_bytes))
                if wake_listener is not None:
                    wake_listener.resume()
                continue

            if event_type == "speech.finished":
                utterance_id = str(payload.get("utteranceId", "")).strip()
                if utterance_id:
                    await speech_manager.notify_finished(utterance_id)
                continue

            if event_type == "voice.cancel":
                voice_recorder.cancel()
                if wake_listener is not None:
                    wake_listener.resume()
                await hub.send_roles({"avatar", "ui"}, event("voice.state", state="idle"))
                continue

            if event_type == "session.new":
                await speech_manager.interrupt("session-switch")
                session = memory.create_session()
                await hub.send_roles(
                    {"avatar", "ui"},
                    event("session.switched", conversationId=session["id"], title=session["title"]),
                )
                continue

            if event_type == "session.list.request":
                sessions = memory.list_sessions()
                await hub.send(
                    websocket,
                    event(
                        "session.list.response",
                        sessions=[
                            {
                                "conversationId": item["id"],
                                "title": item["title"],
                                "updatedAt": item["updated_at"],
                            }
                            for item in sessions
                        ],
                    ),
                )
                continue

            if event_type == "chat.history.request":
                raw = payload.get("conversationId")
                session_id = None
                if raw is not None:
                    try:
                        session_id = int(raw)
                    except (TypeError, ValueError):
                        session_id = None
                history_session = session_id if session_id is not None else memory.latest_session_id()
                history = memory.load_history(conversation_id=history_session) if history_session else []
                await hub.send(
                    websocket,
                    event(
                        "chat.history.response",
                        conversationId=history_session,
                        messages=history,
                    ),
                )
                continue

            if event_type == "session.delete":
                raw = payload.get("conversationId")
                try:
                    session_id = int(raw)
                except (TypeError, ValueError):
                    await hub.send(websocket, event("core.error", message="Invalid conversationId"))
                    continue
                await speech_manager.interrupt("session-switch")
                if not memory.delete_session(session_id):
                    await hub.send(websocket, event("core.error", message="会话不存在或已删除"))
                    continue
                await hub.send_roles(
                    {"avatar", "ui"},
                    event("session.deleted", conversationId=session_id),
                )
                current = memory.latest_session_id()
                switched = memory.get_session(current) if current else None
                if switched is not None:
                    await hub.send_roles(
                        {"avatar", "ui"},
                        event("session.switched", conversationId=switched["id"], title=switched["title"]),
                    )
                continue

            if event_type == "avatar.command":
                command = str(payload.get("event", "")).strip()
                command_payload = payload.get("payload", {})
                if command not in AVATAR_EVENTS or not isinstance(command_payload, dict):
                    await hub.send(websocket, event("core.error", message="Invalid avatar command"))
                    continue
                await hub.send_roles(
                    {"avatar"},
                    event("avatar.command", event=command, payload=command_payload),
                )
                continue

            if event_type != "chat.message":
                await hub.send(websocket, event("core.error", message="Unsupported event"))
                continue

            text = str(payload.get("text", "")).strip()
            if not text:
                continue
            if len(text) > 4000:
                await hub.send(websocket, event("core.error", message="消息长度不能超过 4000 字"))
                continue
            request_id = str(payload.get("messageId", "")).strip() or f"chat-{int(datetime.now().timestamp() * 1000)}"
            conversation_id = None
            raw_conversation_id = payload.get("conversationId")
            if raw_conversation_id is not None:
                try:
                    conversation_id = int(raw_conversation_id)
                except (TypeError, ValueError):
                    await hub.send(websocket, event("core.error", message="Invalid conversationId"))
                    continue
            asyncio.create_task(handle_chat(text, request_id, conversation_id))
    except WebSocketDisconnect:
        pass
    finally:
        hub.disconnect(websocket)


def run() -> None:
    import uvicorn

    uvicorn.run(app, host=HOST, port=PORT, log_level="info")


if __name__ == "__main__":
    run()
