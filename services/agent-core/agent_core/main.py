from __future__ import annotations

import asyncio
import io
import json
import os
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import replace
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

from .agent_loop import MAX_TOOL_STEPS, AgentStep, ToolsUnsupportedError, run_agent_loop
from .harness import (
    TOOL_GUIDANCE,
    AgentReply,
    CharacterHarness,
    behavior_events,
    default_title,
)
from .mcp_host import McpHost
from .memory_retrieval import retrieve_relevant
from .permissions import ALLOW, ASK, ActionRequest, PermissionEngine, PolicyDecision
from .proactive import IdlePolicy, ProactivePolicy
from .speech import SpeechClient, SpeechManager, SpeechUnavailable, speech_settings_from_env
from .storage import MemoryStore
from .voice_text import normalize_voice_text
from .tools import build_tool_registry, execute_tool, openai_tools_schema
from .voice import VoiceError, VoiceRecorder, transcribe_wav
from .wake_word import (
    WakeWordListener,
    begin_capture_scope,
    cancel_utterance_capture,
    capture_utterance,
    encode_wav,
    end_capture_scope,
    is_wake_phrase,
)

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
# zcode (E 期增强): per-tool narration templates — a multi-step task gets one
# short spoken line per NEW tool type, so she narrates without chattering.
TOOL_NARRATION_LINES = {
    "read_file": "我先看看这个文件的内容~",
    "list_dir": "我来看看这个目录里有什么~",
    "write_file": "我要动手写入这一段了哦，稍等~",
    "screenshot": "我截一下屏幕看看~",
    "run_command": "我来运行这条命令，别担心，会说给你听的~",
    "get_time": "",
    "clipboard_read": "我看看剪贴板里有什么~",
    "active_window": "我瞄一眼你现在开着什么窗口~",
}

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


class AnthropicCompatibleProvider:
    """Speaks the Anthropic /v1/messages dialect (StepFun step_plan and kin).

    The agent loop stays OpenAI-shaped: this adapter translates the
    conversation and tool schemas on the way in, and repacks text/tool_use
    content blocks into the OpenAI-shaped turn the loop expects on the way
    out. Thinking blocks (step-3.7-flash et al.) are skipped on parse, and
    max_tokens must leave room for them.
    """

    ANTHROPIC_VERSION = "2023-06-01"
    DEFAULT_MAX_TOKENS = 4096

    def __init__(
        self,
        *,
        name: str,
        base_url: str,
        model: str,
        api_key: str,
        timeout_seconds: float,
        reload_config: Callable[[], tuple[str, str, str] | None] | None = None,
        max_tokens: int | None = None,
    ) -> None:
        self.name = name
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds
        self.configured = bool(api_key)
        self._reload_config = reload_config
        self.max_tokens = int(max_tokens or self.DEFAULT_MAX_TOKENS)

    @property
    def messages_url(self) -> str:
        return f"{self.base_url}/v1/messages"

    def _apply_config(self, base_url: str, model: str, api_key: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.configured = bool(api_key)

    @staticmethod
    def _arguments_from(raw: Any) -> dict:
        if isinstance(raw, str):
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                return {}
            return parsed if isinstance(parsed, dict) else {}
        return raw if isinstance(raw, dict) else {}

    def _to_anthropic_messages(self, messages: list[dict]) -> tuple[str, list[dict]]:
        """OpenAI-shaped conversation -> (system, Anthropic messages).

        system rows merge into the top-level system param; assistant tool_calls
        become tool_use blocks; tool rows become user tool_result blocks.
        """
        system_parts: list[str] = []
        out: list[dict] = []
        for item in messages:
            role = str(item.get("role"))
            content = item.get("content")
            if role == "system":
                if content:
                    system_parts.append(str(content))
            elif role == "assistant":
                blocks: list[dict] = []
                text = str(content or "").strip()
                if text:
                    blocks.append({"type": "text", "text": text})
                for call in item.get("tool_calls") or []:
                    function = call.get("function") or {}
                    blocks.append(
                        {
                            "type": "tool_use",
                            "id": str(call.get("id") or ""),
                            "name": str(function.get("name", "")),
                            "input": self._arguments_from(function.get("arguments")),
                        }
                    )
                if not blocks:
                    blocks.append({"type": "text", "text": "（继续）"})
                out.append({"role": "assistant", "content": blocks})
            elif role == "tool":
                out.append(
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": str(item.get("tool_call_id") or ""),
                                "content": str(content or ""),
                            }
                        ],
                    }
                )
            else:
                out.append({"role": "user", "content": [{"type": "text", "text": str(content or "")}]})
        return "\n\n".join(system_parts), out

    @staticmethod
    def _to_anthropic_tools(tools: list[dict]) -> list[dict]:
        out = []
        for tool in tools:
            function = tool.get("function") or {}
            out.append(
                {
                    "name": str(function.get("name", "")),
                    "description": str(function.get("description", "")),
                    "input_schema": function.get("parameters")
                    or {"type": "object", "properties": {}},
                }
            )
        return out

    def _build_request(self, body: dict) -> urllib.request.Request:
        return urllib.request.Request(
            self.messages_url,
            data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            headers={
                "Accept": "application/json",
                "x-api-key": self.api_key,
                "anthropic-version": self.ANTHROPIC_VERSION,
                "Content-Type": "application/json",
            },
            method="POST",
        )

    async def _send_with_config_reload(self, request: urllib.request.Request) -> bytes:
        for attempt in (0, 1):
            try:
                if attempt == 1:
                    request.add_header("x-api-key", self.api_key)
                    request.add_unredirected_header("x-api-key", self.api_key)
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

    def _request(self, request: urllib.request.Request) -> bytes:
        hostname = urllib.parse.urlparse(request.full_url).hostname
        if hostname in {"127.0.0.1", "localhost"}:
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        else:
            opener = urllib.request.build_opener()
        with opener.open(request, timeout=self.timeout_seconds) as response:
            return response.read()

    @staticmethod
    def _http_error_detail(exc: urllib.error.HTTPError) -> str:
        try:
            payload = json.loads(exc.read().decode("utf-8", "replace"))
            error = payload.get("error", {})
            message = error.get("message", "") if isinstance(error, dict) else ""
        except (AttributeError, TypeError, json.JSONDecodeError, OSError):
            return ""
        return " ".join(str(message).split())[:240]

    def _parse_response(self, payload: dict) -> dict:
        content = payload.get("content")
        if not isinstance(content, list):
            raise ProviderError(f"{self.name} API 响应格式无法识别")
        text = "".join(
            str(block.get("text", ""))
            for block in content
            if isinstance(block, dict) and block.get("type") == "text"
        ).strip()
        tool_calls: list[dict] = []
        for index, block in enumerate(content):
            if isinstance(block, dict) and block.get("type") == "tool_use":
                tool_calls.append(
                    {
                        "id": str(block.get("id") or f"call_{index}"),
                        "name": str(block.get("name", "")).strip(),
                        "arguments": self._arguments_from(block.get("input")),
                    }
                )
        raw: dict = {"role": "assistant", "content": text or None}
        if tool_calls:
            raw["tool_calls"] = [
                {
                    "id": call["id"],
                    "type": "function",
                    "function": {
                        "name": call["name"],
                        "arguments": json.dumps(call["arguments"], ensure_ascii=False),
                    },
                }
                for call in tool_calls
            ]
        return {"content": text, "tool_calls": tool_calls, "raw": raw}

    async def _post(self, body: dict, tools: bool) -> dict:
        request = self._build_request(body)
        try:
            response_bytes = await self._send_with_config_reload(request)
        except urllib.error.HTTPError as exc:
            if tools and exc.code in {400, 404, 422}:
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
        except json.JSONDecodeError as exc:
            raise ProviderError(f"{self.name} API 响应格式无法识别") from exc
        return self._parse_response(payload)

    async def complete(self, messages: list[dict[str, str]]) -> str:
        if not self.api_key:
            raise ProviderError(f"{self.name} API Key 未配置")
        system, anthropic_messages = self._to_anthropic_messages(messages)
        body: dict = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "messages": anthropic_messages,
        }
        if system:
            body["system"] = system
        turn = await self._post(body, tools=False)
        text = str(turn.get("content") or "").strip()
        if not text:
            raise ProviderError(f"{self.name} API 返回空回复")
        return text

    async def complete_with_tools(self, messages: list[dict], tools: list[dict]) -> dict:
        if not self.api_key:
            raise ProviderError(f"{self.name} API Key 未配置")
        system, anthropic_messages = self._to_anthropic_messages(messages)
        body: dict = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "messages": anthropic_messages,
            "tools": self._to_anthropic_tools(tools),
        }
        if system:
            body["system"] = system
        return await self._post(body, tools=True)


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
    if name == "stepfun":
        return (
            os.getenv("STEPFUN_BASE_URL", "https://api.stepfun.com/step_plan"),
            os.getenv("STEPFUN_MODEL", "step-3.7-flash"),
            os.getenv("STEPFUN_API_KEY", ""),
        )
    return (
        os.getenv("GLM_BASE_URL", "https://open.bigmodel.cn/api/coding/paas/v4"),
        os.getenv("GLM_MODEL", "glm-5.3-flash"),
        os.getenv("GLM_API_KEY", ""),
    )


def build_provider() -> ChatProvider:
    if LLM_PROVIDER not in {"glm", "deepseek", "stepfun"}:
        return MockProvider()
    base_url, model, api_key = _provider_config(LLM_PROVIDER)
    if not api_key:
        return MockProvider()
    if LLM_PROVIDER == "stepfun":
        return AnthropicCompatibleProvider(
            name=LLM_PROVIDER,
            base_url=base_url,
            model=model,
            api_key=api_key,
            timeout_seconds=LLM_TIMEOUT_SECONDS,
        )
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
_voice_refractory = {"last_voice_stop": 0.0}
VOICE_WAKE_REFRACTORY_SECONDS = 5.0
_inflight_wake_request: str | None = None
_superseded_requests: set[str] = set()


def _register_inflight_wake_request(request_id: str) -> None:
    global _inflight_wake_request
    _inflight_wake_request = request_id


def _unregister_inflight_wake_request(request_id: str) -> None:
    global _inflight_wake_request
    if _inflight_wake_request == request_id:
        _inflight_wake_request = None


async def _withdraw_session_if_empty(session_id: int | None) -> None:
    """Drop the fresh session a superseded wake chain created: an empty,
    auto-titled leftover would otherwise linger as latest_session_id."""
    if session_id is None:
        return
    try:
        if not memory.load_messages(1, session_id):
            memory.delete_session(session_id)
            await hub.send_roles(
                {"avatar", "ui"},
                event("session.deleted", conversationId=session_id),
            )
    except Exception as exc:
        memory.add_event("core.error", {"message": f"session cleanup failed: {exc}"})
memory = MemoryStore()
harness = CharacterHarness()
tool_registry = build_tool_registry()
# zcode (phase B 前置): deny-by-default permission engine; read-only tools
# pre-allowed, write tools require user confirmation ("ask"), everything
# else rejected until explicit rules ship with it.
permission_engine = PermissionEngine()

# zcode (T1): pending write confirmations, one per session, TTL-limited.
# The "ask" tier parks a write here; the user's next chat message either
# confirms it (executes atomically) or declines it (drops it).
_pending_writes: dict[int, dict] = {}
_PENDING_TTL_SECONDS = 600
# zcode (T-MCP 验收修复 2026-09-07): scoped to the tool NAME — a session-
# wide flag leaked onto the next unrelated ask-tier tool (get_me got a
# data-less receipt right after a confirmed browser call).
_confirmed_write_once: dict[int, str] = {}
_ACTIVE_CHAT_SESSION_ID: list[int | None] = [None]
_CONFIRM_WORDS = ("确认", "可以", "同意", "执行吧", "好的", "去吧", "ok", "yes")
_DECLINE_WORDS = ("取消", "算了", "不要", "先不", "别写", "拒绝")

# zcode (phase B 记忆接入): preference-style memory candidates auto-confirm;
# anything else (files, people, locations, commands) stays pending for the
# confirmation UI planned in phase B.
_AUTO_CONFIRM_MEMORY_MARKERS = (
    "喜欢", "最喜欢", "叫我", "称呼", "名字", "生日", "职业",
    "上班", "公司", "害怕", "讨厌", "养了", "爱吃", "爱喝",
)


def _auto_confirm_memory(text: str) -> bool:
    return any(marker in text for marker in _AUTO_CONFIRM_MEMORY_MARKERS)


# zcode (2026-09-07): T2+ exam fix — when the user explicitly asks to remember,
# the fact is confirmed regardless of the preference-centric marker table.
_EXPLICIT_REMEMBER_MARKERS = ("记住", "记一下", "帮我记")


def _fact_promotion_status(candidate_text: str, user_text: str) -> str:
    if _auto_confirm_memory(candidate_text) or any(
        marker in (user_text or "") for marker in _EXPLICIT_REMEMBER_MARKERS
    ):
        return "confirmed"
    return "pending"
tools_schema = openai_tools_schema(tool_registry) if TOOLS_ENABLED else []
# zcode (C 期): MCP host — external servers merged into the tool schema
mcp_host = McpHost()
# zcode (D 期): proactive policy — startup greeting, quiet hours, cooldown
proactive_policy = ProactivePolicy(
    quiet_start=os.getenv("ANIME_AGENT_QUIET_START", "23:00"),
    quiet_end=os.getenv("ANIME_AGENT_QUIET_END", "08:00"),
    cooldown_seconds=float(os.getenv("ANIME_AGENT_PROACTIVE_COOLDOWN", "1800")),
)
_STARTUP_GREETINGS = (
    "我上线啦～今天想听歌还是想聊天？",
    "嗨，我就在桌面上等你呢。有什么需要随时叫我哦～",
    "开机啦？我也准备好啦，今天也一起加油吧～",
)
_proactive_events: dict[str, float] = {}
_proactive_skip_state: dict[str, str] = {}


def _log_skip_once(trigger: str, reason: str) -> None:
    """跳过原因只在变化时记一条，防止轮询刷屏（曾刷出 431 条）。"""
    key = f"skip:{reason}"
    if _proactive_skip_state.get(trigger) != key:
        memory.add_event("proactive.skipped", {"trigger": trigger, "reason": reason})
        _proactive_skip_state[trigger] = key

# zcode (D 期收尾, 2026-09-07): idle trigger — pure local idle detection
# (GetLastInputInfo poll) + fixed line bank; zero LLM calls at any point,
# so standby costs no quota (验收门禁：待机零 GLM 调用).
idle_policy = IdlePolicy(
    threshold_seconds=float(os.getenv("ANIME_AGENT_IDLE_THRESHOLD", "2700")),
    quiet_start=os.getenv("ANIME_AGENT_QUIET_START", "23:00"),
    quiet_end=os.getenv("ANIME_AGENT_QUIET_END", "08:00"),
    cooldown_seconds=float(os.getenv("ANIME_AGENT_IDLE_COOLDOWN", "3600")),
)
_IDLE_LINES = (
    "一直没看到你动呀，起来活动活动吧，眼睛也要歇一歇哦～",
    "在忙吗？我不吵你，就是提醒一下该喝口水啦～",
    "你安静了好一会儿，我还在桌面上等你呢，想聊天随时叫我～",
)
_IDLE_POLL_SECONDS = 30.0


def _idle_seconds_now() -> float:
    """System-wide seconds since last real keyboard/mouse input (Windows)."""
    import ctypes

    if not sys.platform.startswith("win"):
        return 0.0

    class _LastInputInfo(ctypes.Structure):
        _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]

    info = _LastInputInfo()
    info.cbSize = ctypes.sizeof(info)
    try:
        if not ctypes.windll.user32.GetLastInputInfo(ctypes.byref(info)):
            return 0.0
        delta = (ctypes.windll.kernel32.GetTickCount() - info.dwTime) & 0xFFFFFFFF
        return delta / 1000.0
    except Exception:  # noqa: BLE001 - a poll must never take Core down
        return 0.0


async def _proactive_idle(idle_seconds: float) -> None:
    allowed, reason = idle_policy.decide(idle_seconds=idle_seconds)
    if not allowed:
        _log_skip_once("idle", reason)
        return
    if hub.role_count("avatar") < 1:
        memory.add_event("proactive.skipped", {"trigger": "idle", "reason": "no-avatar"})
        return
    idle_policy.mark_spoken()
    _proactive_skip_state.pop("idle", None)
    line = _IDLE_LINES[int(time.time()) % len(_IDLE_LINES)]
    memory.add_event("proactive.idle", {"idle_seconds": round(idle_seconds), "line": line})
    try:
        await _speak_reply(line, "proactive-idle", narrating=False)
    except Exception as exc:  # noqa: BLE001
        memory.add_event("proactive.error", {"message": str(exc)[:200]})


def _idle_watch_loop(loop: asyncio.AbstractEventLoop) -> None:
    while True:
        time.sleep(_IDLE_POLL_SECONDS)
        idle = _idle_seconds_now()
        if idle < idle_policy.threshold_seconds:
            continue
        try:
            asyncio.run_coroutine_threadsafe(_proactive_idle(idle), loop)
        except RuntimeError:
            return


def _start_idle_watch() -> None:
    if idle_policy.threshold_seconds <= 0:
        memory.add_event("proactive.idle.disabled", {})
        return
    loop = asyncio.get_event_loop()
    threading.Thread(target=_idle_watch_loop, args=(loop,), daemon=True, name="idle-watch").start()
    memory.add_event("proactive.idle.enabled", {"threshold": idle_policy.threshold_seconds})


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
            if role == "avatar":
                asyncio.get_event_loop().create_task(_proactive_greeting("avatar-connect"))

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
    """Broadcast tool steps; narrate the first tool step plus each NEW tool
    type when TTS is live (E 期工作解说: narrate without chattering)."""
    narrated = {"done": False}
    narrated_tools: set[str] = set()

    async def handler(step: AgentStep) -> None:
        await broadcast_tool_step(step, request_id)
        if request_id in _superseded_requests:
            return
        if not (TTS_ENABLED and TTS_NARRATE and hub.role_count("avatar") > 0):
            return
        line = None
        if not narrated["done"]:
            narrated["done"] = True
            line = NARRATION_LINE
            narrated_tools.add(step.tool)
        elif step.tool not in narrated_tools and step.tool in TOOL_NARRATION_LINES:
            narrated_tools.add(step.tool)
            line = TOOL_NARRATION_LINES[step.tool]
        if line:
            asyncio.create_task(_speak_reply(line, request_id, narrating=True))

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


async def _proactive_greeting(trigger: str) -> None:
    """D 期主动触发：启动/空闲问候。免打扰时段与冷却期由策略模块把关，
    防骚扰去抖落在 events 里可查。问候为固定台词，不消耗 LLM 额度。"""
    allowed, reason = proactive_policy.allow()
    if not allowed:
        _log_skip_once(trigger, reason)
        return
    proactive_policy.mark_spoken()
    _proactive_skip_state.pop(trigger, None)
    line = _STARTUP_GREETINGS[int(time.time()) % len(_STARTUP_GREETINGS)]
    memory.add_event("proactive.greeting", {"trigger": trigger, "line": line})
    try:
        await _speak_reply(line, f"proactive-{trigger}", narrating=False)
    except Exception as exc:  # noqa: BLE001
        memory.add_event("proactive.error", {"message": str(exc)[:200]})


async def run_tool(name: str, arguments: dict) -> dict:
    # zcode (phase B 前置 + T1): every tool call passes the permission gate
    # first; denials never reach the executor, "ask" decisions park the call
    # as a pending confirmation the user must answer in chat.
    decision = permission_engine.evaluate(
        ActionRequest(
            tool=str(name or ""),
            arguments=arguments if isinstance(arguments, dict) else {},
            origin="agent",
            session_id=None,
        )
    )
    # zcode (T1 复盘修复): a user-confirmed write consumes its one-shot
    # authorization here, so the model's own re-invocation executes instead
    # of parking again (the confirmation loop found by the T1 exam).
    if decision.kind == ASK:
        session = _ACTIVE_CHAT_SESSION_ID[0]
        if session is not None and _confirmed_write_once.get(session) == name:
            # the pending action already executed when the user confirmed;
            # a model retry of THE SAME tool must not duplicate it. Other
            # ask-tier tools keep their own full ask flow.
            _confirmed_write_once.pop(session, None)
            memory.add_event("permission.authorized", {"tool": name})
            return {"ok": True, "already_executed": True,
                    "note": "该写入已在用户确认时执行完成，请直接向用户汇报结果，不要再调用写入工具。"}
    memory.add_event(
        "permission.decision",
        {
            "tool": name,
            "kind": decision.kind,
            "allowed": decision.allowed,
            "rule_id": decision.rule_id,
            "reason": decision.reason,
        },
    )
    if decision.kind == ASK:
        session_id = _ACTIVE_CHAT_SESSION_ID[0] if _ACTIVE_CHAT_SESSION_ID[0] is not None else None
        _pending_writes[session_id or 0] = {
            "tool": name,
            "arguments": arguments if isinstance(arguments, dict) else {},
            "request_id": None,
            "expires": time.time() + _PENDING_TTL_SECONDS,
        }
        memory.add_event(
            "permission.ask",
            {"tool": name, "session_id": session_id, "arguments": json.dumps(arguments, ensure_ascii=False, default=str)[:300]},
        )
        return {
            "ok": False,
            "needs_confirmation": True,
            "error": "该操作需要用户在聊天中明确确认（例如回复“确认”）后才会执行。"
                     "请向用户说明你想要执行的操作并请求确认，不要重复调用本工具。",
        }
    if not decision.allowed:
        return {
            "ok": False,
            "error": f"权限拒绝（{decision.rule_id}）：{decision.reason}",
        }
    if str(name).startswith("mcp__"):
        parts = str(name).split("__")
        server_name, tool_name = parts[1], parts[2]
        server = mcp_host.servers.get(server_name)
        if server is None or not server.started:
            return {"ok": False, "error": f"MCP server {server_name} 不可用"}
        result = await server.call(tool_name, arguments if isinstance(arguments, dict) else {})
        return {"ok": result.get("ok", False), "output": result.get("text", "")}
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


# zcode (UI 思考强度档): the client's per-turn effort dial. Every level keeps
# her a complete agent — the full registry plus all MCP tools stay attached and
# the permission engine is untouched; the dial only caps how many loop steps a
# turn may spend and which behavior note rides the system prompt. "deep" keeps
# the historical step budget, so clients without the field behave as before.
EFFORT_LEVELS: dict[str, dict[str, Any]] = {
    "chill": {"label": "碎碎念", "max_steps": 1},
    "standard": {"label": "帮帮忙", "max_steps": 3},
    "deep": {"label": "大展身手", "max_steps": MAX_TOOL_STEPS},
}
DEFAULT_EFFORT = "deep"
EFFORT_PROMPT_NOTES: dict[str, str] = {
    "chill": "【本轮思考强度：碎碎念｜工具预算：至多 1 次往返】"
             "回答形态：1~3 句口语短句，像聊天一样接话——不列表、不标题、不分析利弊，"
             "哪怕话题很复杂也先用最短的话接住。"
             "工具姿态：默认不调工具直接答；确需查证只做一次单点快查，拿到结果立刻收尾。"
             "主动性：不铺开任务、不主动提议更大的活；用户让你干重活时，"
             "轻声提一句调到帮帮忙或大展身手更合适，然后仍然尽力用手头预算帮上忙。",
    "standard": "【本轮思考强度：帮帮忙｜工具预算：至多 3 步】"
                "回答形态：一小段完整的话（约 3~6 句），把事情交代清楚就收——"
                "不写长篇分析，不堆砌列表。"
                "工具姿态：小任务直接开做，串联至多 3 步，每步围绕目标不绕路。"
                "主动性：3 步装不下的部分明说手头信息到这里，建议升档到大展身手，但不啰嗦。",
    "deep": "【本轮思考强度：大展身手｜工具预算：至多 5 步】"
            "回答形态：完整而结构化——可以列要点、给来源、附下一步建议，把问题当正经任务交付。"
            "工具姿态：先在心里列个小计划，再串联至多 5 步逐步执行并核实，最后汇总。"
            "主动性：预算内自主推进；确需更多步骤时先说明进展再请示。",
}


def resolve_effort(raw: Any) -> str:
    """Normalize a client-sent effort value; anything unknown falls back to deep."""
    name = str(raw or "").strip().lower()
    return name if name in EFFORT_LEVELS else DEFAULT_EFFORT


def effort_prompt_note(effort: str) -> str:
    """The per-level behavior note that rides the system prompt (may be empty)."""
    return EFFORT_PROMPT_NOTES.get(effort, "")


async def handle_chat(text: str, request_id: str, conversation_id: int | None = None, effort: Any = None) -> None:
    global _inflight_wake_request
    if _inflight_wake_request and _inflight_wake_request != request_id:
        # a newer request supersedes an in-flight wake-chain request: the same
        # intent arriving twice must never be answered twice
        _superseded_requests.add(_inflight_wake_request)
    if request_id.startswith("wake-"):
        _inflight_wake_request = request_id
    else:
        _inflight_wake_request = None

    try:
        await _handle_chat_locked(text, request_id, conversation_id, effort)
    finally:
        if _inflight_wake_request == request_id:
            _inflight_wake_request = None
        _superseded_requests.discard(request_id)


async def _handle_chat_locked(text: str, request_id: str, conversation_id: int | None = None, effort: Any = None) -> None:

    async with chat_lock:
        if request_id in _superseded_requests:
            memory.add_event("chat.superseded", {"request_id": request_id, "stage": "queued"})
            _superseded_requests.discard(request_id)
            await _withdraw_session_if_empty(conversation_id)
            return
        await broadcast_state("thinking", request_id)
        probe = conversation_id if conversation_id is not None else memory.latest_session_id()
        is_first_exchange = probe is None or not memory.load_messages(1, probe)
        session_id = memory.add_message("user", text, request_id, conversation_id)
        _ACTIVE_CHAT_SESSION_ID[0] = session_id
        # zcode (T1): a pending write from the previous turn is either
        # confirmed (executed atomically), declined (dropped), or kept alive.
        confirm_note = ""
        pending = _pending_writes.get(session_id)
        if pending is not None:
            if time.time() > pending["expires"]:
                _pending_writes.pop(session_id, None)
                memory.add_event("permission.pending.expired", {"session_id": session_id})
            elif any(word in text for word in _CONFIRM_WORDS):
                # zcode (T1 复盘修复): route through the same choke point as
                # the agent loop so local tools and mcp__ tools both work
                if str(pending["tool"]).startswith("mcp__"):
                    parts = str(pending["tool"]).split("__")
                    server = mcp_host.servers.get(parts[1]) if len(parts) > 2 else None
                    if server is None or not server.started:
                        result = {"ok": False, "error": f"MCP server {parts[1] if len(parts) > 1 else ''} 不可用"}
                    else:
                        result = await server.call(parts[2], pending["arguments"])
                        result = {"ok": result.get("ok", False), "output": result.get("text", "")}
                else:
                    result = await execute_tool(tool_registry, pending["tool"], pending["arguments"])
                _pending_writes.pop(session_id, None)
                memory.add_event(
                    "permission.confirmed",
                    {"session_id": session_id, "tool": pending["tool"],
                     "ok": bool(result.get("ok")),
                     "result": json.dumps(result, ensure_ascii=False, default=str)[:300]},
                )
                _confirmed_write_once[session_id] = pending["tool"]
                confirm_note = (
                    "【系统提示】用户已确认此前请求的写入操作，执行结果："
                    + json.dumps(result, ensure_ascii=False, default=str)[:300]
                    + "。请以天依的口吻向用户汇报这个结果。"
                )
            elif any(word in text for word in _DECLINE_WORDS):
                _pending_writes.pop(session_id, None)
                memory.add_event("permission.declined", {"session_id": session_id, "tool": pending["tool"]})
                confirm_note = "【系统提示】用户拒绝了此前请求的写入操作。请不要执行，以天依的口吻自然回应即可。"
        conversation_history = memory.load_messages(MAX_HISTORY_MESSAGES, session_id)
        effort_name = resolve_effort(effort)
        memory.add_event("chat.effort", {"request_id": request_id, "effort": effort_name})
        effective_tools_schema = list(tools_schema)
        for qualified, description, input_schema in mcp_host.tool_entries():
            effective_tools_schema.append({
                "type": "function",
                "function": {"name": qualified, "description": description, "parameters": input_schema},
            })
        guided = TOOL_GUIDANCE if effective_tools_schema else ""
        # zcode (phase B 记忆接入): recall confirmed facts relevant to this
        # turn and inject them alongside tool guidance. Retrieval failures
        # must never break the chat itself.
        recall_block = ""
        try:
            facts = memory.recall_facts(session_id)
            if facts:
                recalled = retrieve_relevant(text, facts, limit=3)
                if recalled:
                    recall_block = "【相关记忆】\n" + "\n".join(f"- {fact}" for fact in recalled)
        except Exception as exc:  # noqa: BLE001
            memory.add_event("memory.recall.error", {"message": str(exc)[:200]})
        extra_parts = [
            part
            for part in (confirm_note, effort_prompt_note(effort_name), recall_block, guided)
            if part
        ]
        extra_system = "\n\n".join(extra_parts)
        messages = harness.build_messages(
            conversation_history, text, extra_system=extra_system, request_session_title=is_first_exchange
        )
        try:
            if effective_tools_schema:
                loop_result = await run_agent_loop(
                    provider,
                    messages,
                    effective_tools_schema,
                    run_tool,
                    on_step=_make_loop_step_handler(request_id),
                    max_steps=int(EFFORT_LEVELS[effort_name]["max_steps"]),
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
                            "errors": [s.summary for s in loop_result.steps if not s.ok],
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
        if agent_reply.reply:
            agent_reply = replace(agent_reply, reply=normalize_voice_text(agent_reply.reply))
        if request_id in _superseded_requests:
            # the newer request owns this intent: withdraw the user turn so the
            # session history and the next LLM context stay clean
            memory.delete_message(request_id)
            memory.add_event("chat.superseded", {"request_id": request_id, "stage": "post-llm"})
            _superseded_requests.discard(request_id)
            await broadcast_state("idle", request_id)
            await _withdraw_session_if_empty(session_id)
            return
        memory.add_message("assistant", agent_reply.reply, request_id, session_id)
        if is_first_exchange:
            title = agent_reply.session_title or default_title(text)
            if title and memory.rename_session(session_id, title):
                await hub.send_roles(
                    {"avatar", "ui"},
                    event("session.title", conversationId=session_id, title=title),
                )
        if agent_reply.memory_candidate:
            # zcode (phase B 记忆接入): sensitivity-tiered storage. Preference-
            # style facts auto-confirm and become recallable; explicit "记住"
            # forces confirmation; everything else stays pending (injected
            # tagged via recall_facts since the T2+ exam).
            candidate_text = str(agent_reply.memory_candidate)
            status = _fact_promotion_status(candidate_text, text)
            memory.add_event(
                "memory.candidate",
                {
                    "fact": agent_reply.memory_candidate,
                    "request_id": request_id,
                    "status": status,
                },
            )
            fact_id = memory.add_fact(
                candidate_text,
                session_id=session_id,
                scope="global" if status == "confirmed" else "session",
                status=status,
                source_request_id=request_id,
            )
            memory.add_event(
                "memory.fact.stored",
                {"fact_id": fact_id, "status": status, "request_id": request_id},
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
    try:
        await hub.send_roles({"avatar", "ui"}, event("voice.state", state="transcribing"))
        try:
            text = await asyncio.to_thread(transcribe_wav, audio_bytes)
        except VoiceError as exc:
            await hub.send_roles({"avatar", "ui"}, event("core.error", message=str(exc)))
            await hub.send_roles({"avatar", "ui"}, event("voice.state", state="idle"))
            return
        await hub.send_roles({"avatar", "ui"}, event("voice.transcript", text=text))
        await hub.send_roles({"avatar", "ui"}, event("voice.state", state="idle"))
    finally:
        # only now is it safe to re-arm the wake listener: its ring buffer may
        # still hold the sentence the user just spoke into the voice button
        if wake_listener is not None:
            wake_listener.resume()


async def handle_wake_word(buffered_audio) -> None:
    global _wake_busy
    recent_voice = time.monotonic() - _voice_refractory["last_voice_stop"] < VOICE_WAKE_REFRACTORY_SECONDS
    if _wake_busy or voice_recorder.recording or recent_voice:
        memory.add_event("wake.busy", {"state": _agent_state, "refractory": recent_voice})
        return
    if _agent_state in {"thinking", "working", "error"}:
        # an LLM/tool turn owns the channel: the supersede machinery, not a
        # barge-in, resolves overlaps here
        memory.add_event("wake.busy", {"state": _agent_state, "refractory": recent_voice})
        return
    if _agent_state == "speaking":
        # wake barge-in is allowed mid-playback, unless the trigger source is
        # plausibly her own voice (the spoken text itself names her)
        spoken_text = speech_manager.current.text if speech_manager.current is not None else ""
        if "天依" in spoken_text:
            memory.add_event("wake.busy", {"reason": "self-echo", "state": "speaking"})
            return
        memory.add_event("wake.barge_in", {"state": "speaking"})
    _wake_busy = True
    if wake_listener is not None:
        wake_listener.pause()
    # the wake chain owns its identity from this moment: any manual request
    # arriving anywhere in the (multi-second) transcribe + capture window
    # supersedes it, so one spoken intent can never be answered twice
    capture_token = begin_capture_scope()
    wake_request_id = "wake-" + str(int(datetime.now().timestamp() * 1000))
    _register_inflight_wake_request(wake_request_id)
    dispatched = False
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
        if wake_request_id in _superseded_requests:
            _superseded_requests.discard(wake_request_id)
            memory.add_event("wake.busy", {"reason": "superseded-pre-dispatch"})
            return
        # zcode (2026-09-09): 会话创建推迟到真实指令捕获之后——此前每次
        # "唤醒成功但没跟指令"都会泄漏一个空"新对话"。
        await speech_manager.interrupt("wake")
        await hub.send_roles({"avatar", "ui"}, event("wake.triggered"))
        await hub.send_roles({"avatar", "ui"}, event("voice.state", state="recording"))
        try:
            command_bytes = await asyncio.to_thread(capture_utterance, capture_token)
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
                if (
                    voice_recorder.recording
                    or _agent_state in {"thinking", "working"}
                    or time.monotonic() - _voice_refractory["last_voice_stop"] < VOICE_WAKE_REFRACTORY_SECONDS
                ):
                    memory.add_event("wake.busy", {"reason": "voice-key-preempted"})
                    return
                session = memory.create_session()
                await hub.send_roles({"avatar", "ui"}, event("session.switched", conversationId=session["id"], title=session["title"]))
                await hub.send_roles({"avatar", "ui"}, event("chat.user_message", conversationId=session["id"], text=command_text))
                dispatched = True
                asyncio.create_task(handle_chat(command_text, wake_request_id, conversation_id=session["id"]))
                return
        await hub.send_roles({"avatar", "ui"}, event("wake.idle"))
    finally:
        _wake_busy = False
        if wake_listener is not None and not voice_recorder.recording:
            wake_listener.resume()
        end_capture_scope(capture_token)
        if not dispatched:
            _unregister_inflight_wake_request(wake_request_id)
            _superseded_requests.discard(wake_request_id)


@app.on_event("startup")
async def _start_mcp_servers() -> None:
    # zcode (C 期): bring up configured MCP servers before serving traffic
    try:
        await mcp_host.start_from_env()
        if mcp_host.servers:
            memory.add_event("mcp.started", {"status": mcp_host.status()})
    except Exception as exc:  # noqa: BLE001
        memory.add_event("mcp.start.error", {"message": str(exc)[:200]})
    # zcode (D 期收尾): idle watch — local poll only, never calls the provider
    try:
        _start_idle_watch()
    except Exception as exc:  # noqa: BLE001
        memory.add_event("proactive.idle.start.error", {"message": str(exc)[:200]})


@app.on_event("shutdown")
async def _stop_mcp_servers() -> None:
    await mcp_host.stop_all()


@app.on_event("startup")
async def start_wake_word_listener() -> None:
    global wake_listener
    # GPT-style session hygiene: shells that never received a message must
    # not survive into the next session list the user sees.
    memory.sweep_empty_sessions()
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


# Codex: process liveness is independent of optional TTS/LLM availability.
@app.get("/health/live")
async def liveness() -> dict[str, object]:
    return {
        "status": "ok",
        "service": "anime-agent-core",
        "pid": os.getpid(),
        "roles": {
            "avatar": hub.role_count("avatar"),
            "ui": hub.role_count("ui"),
        },
    }


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
                cancel_utterance_capture()
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
                _voice_refractory["last_voice_stop"] = time.monotonic()
                try:
                    audio_bytes = voice_recorder.stop()
                except VoiceError as exc:
                    await hub.send(websocket, event("core.error", message=str(exc)))
                    if wake_listener is not None:
                        wake_listener.resume()
                else:
                    # wake stays paused until the transcript is dispatched: the
                    # ring buffer still holds the user's sentence and re-triggering
                    # on it would duplicate the request through the wake chain
                    asyncio.create_task(handle_voice_transcription(audio_bytes))
                continue

            if event_type == "speech.finished":
                utterance_id = str(payload.get("utteranceId", "")).strip()
                if utterance_id:
                    await speech_manager.notify_finished(utterance_id)
                continue

            if event_type == "voice.cancel":
                cancel_utterance_capture()
                voice_recorder.cancel()
                if wake_listener is not None:
                    wake_listener.resume()
                await hub.send_roles({"avatar", "ui"}, event("voice.state", state="idle"))
                continue

            if event_type == "session.new":
                await speech_manager.interrupt("session-switch")
                cancel_utterance_capture()
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
                        # Codex: Godot's empty-selection sentinel is -1, not null.
                        conversationId=history_session if history_session is not None else -1,
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
                cancel_utterance_capture()
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
            # typing is a barge-in: silence the current playback at once, the
            # new reply takes over when it is ready (no-op when she is quiet)
            await speech_manager.interrupt("new-message")
            conversation_id = None
            raw_conversation_id = payload.get("conversationId")
            if raw_conversation_id is not None:
                try:
                    conversation_id = int(raw_conversation_id)
                except (TypeError, ValueError):
                    await hub.send(websocket, event("core.error", message="Invalid conversationId"))
                    continue
            asyncio.create_task(handle_chat(text, request_id, conversation_id, payload.get("effort")))
    except WebSocketDisconnect:
        pass
    finally:
        hub.disconnect(websocket)


def run() -> None:
    import uvicorn

    uvicorn.run(app, host=HOST, port=PORT, log_level="info")


if __name__ == "__main__":
    run()
