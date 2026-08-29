from __future__ import annotations

import asyncio
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Protocol

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parents[3] / ".env")
except ImportError:
    pass

from .harness import AgentReply, CharacterHarness, behavior_events
from .storage import MemoryStore
from .voice import VoiceError, VoiceRecorder, transcribe_wav

AgentState = Literal["idle", "thinking", "speaking", "working", "error"]

HOST = os.getenv("AGENT_CORE_HOST", "127.0.0.1")
PORT = int(os.getenv("AGENT_CORE_PORT", "8765"))
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "glm").strip().lower()
LLM_TIMEOUT_SECONDS = float(os.getenv("LLM_TIMEOUT_SECONDS", "45"))
MAX_HISTORY_MESSAGES = 20

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
    ) -> None:
        self.name = name
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds
        self.configured = bool(api_key)

    @property
    def completion_url(self) -> str:
        if self.base_url.endswith("/chat/completions"):
            return self.base_url
        return f"{self.base_url}/chat/completions"

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
            response_bytes = await asyncio.to_thread(self._request, request)
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
memory = MemoryStore()
harness = CharacterHarness()
conversation_history: list[dict[str, str]] = memory.load_messages(MAX_HISTORY_MESSAGES)


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


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def event(event_type: str, **payload: object) -> dict[str, object]:
    return {"type": event_type, "timestamp": timestamp(), **payload}


async def broadcast_state(state: AgentState, request_id: str = "") -> None:
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


async def handle_chat(text: str, request_id: str) -> None:
    global conversation_history

    async with chat_lock:
        await broadcast_state("thinking", request_id)
        conversation_history.append({"role": "user", "content": text})
        memory.add_message("user", text, request_id)
        messages = harness.build_messages(
            conversation_history[-MAX_HISTORY_MESSAGES:],
            text,
        )
        try:
            raw_reply = await provider.complete(messages)
        except ProviderError as exc:
            conversation_history.pop()
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
        conversation_history.append({"role": "assistant", "content": agent_reply.reply})
        memory.add_message("assistant", agent_reply.reply, request_id)
        if agent_reply.memory_candidate:
            memory.add_event(
                "memory.candidate",
                {
                    "fact": agent_reply.memory_candidate,
                    "request_id": request_id,
                    "status": "pending",
                },
            )
        conversation_history = conversation_history[-MAX_HISTORY_MESSAGES:]
        await hub.send_roles(
            {"avatar", "ui"},
            event(
                "chat.response",
                text=agent_reply.reply,
                emotion=agent_reply.emotion,
                emotion_intensity=agent_reply.emotion_intensity,
                gesture=agent_reply.gesture,
                request_id=request_id,
            ),
        )
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
                continue

            if event_type == "voice.cancel":
                voice_recorder.cancel()
                await hub.send_roles({"avatar", "ui"}, event("voice.state", state="idle"))
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
            asyncio.create_task(handle_chat(text, request_id))
    except WebSocketDisconnect:
        pass
    finally:
        hub.disconnect(websocket)


def run() -> None:
    import uvicorn

    uvicorn.run(app, host=HOST, port=PORT, log_level="info")


if __name__ == "__main__":
    run()
