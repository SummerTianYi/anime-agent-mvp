"""Opt-in observation of R2-triggered tasks; no decision/output substitutions.

Installed temporarily beside Core/TTS, invoked by a gated diagnostic hook.
Disabled by removing control.json or setting enabled=false. Local files are
PRIVATE evidence: a marked request can recall existing memory/context; export
only reviewed synthetic records. Never log headers,
credentials, binary assets, or model-private reasoning fields.
"""
from __future__ import annotations
import contextvars
import dataclasses
import functools
import hashlib
import inspect
import json
import os
from pathlib import Path
import sys
import threading
import time
import traceback
import uuid

TRACE = contextvars.ContextVar("round02_trace", default=None)
_lock = threading.Lock()
_root: Path | None = None
_requests: dict[str, dict] = {}
_utterances: dict[str, dict] = {}
_sessions: set[int] = set()
_installed = False
_seq = 0


def enabled() -> bool:
    try:
        if _root is None:
            return False
        config = json.loads((_root / "control.json").read_text(encoding="utf-8"))
        return isinstance(config, dict) and config.get("enabled") is True and time.time() < config.get("expires_epoch", 0)
    except (OSError, ValueError, TypeError):
        return False


def safe(value):
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return safe(dataclasses.asdict(value))
    if isinstance(value, dict):
        if isinstance(value.get("type"), str) and value["type"] in {"thinking", "redacted_thinking", "reasoning", "image", "image_url", "audio", "input_audio"}:
            return {"omitted_type": value["type"]}
        return {str(k): safe(v) for k, v in value.items()
                if str(k).lower() not in {"authorization", "headers", "api_key", "access_token", "refresh_token", "id_token",
                                          "reasoning", "reasoning_content", "reasoning_details", "thinking", "signature", "blob", "image", "audio", "raw"}}
    if isinstance(value, (tuple, list, set)):
        return [safe(v) for v in value if not (isinstance(v, dict) and isinstance(v.get("type"), str) and v["type"] in {"thinking", "redacted_thinking", "image", "audio"})]
    if isinstance(value, bytes):
        return {"binary_bytes": len(value), "sha256": hashlib.sha256(value).hexdigest()}
    if isinstance(value, str) and value.startswith("data:"):
        return {"data_uri_omitted": True, "chars": len(value)}
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return {"type": type(value).__name__}


def stream_value(stream, name, invoke=False):
    try:
        value = getattr(stream, name, None)
        return value() if invoke and callable(value) else value
    except Exception as exc:
        return {"unavailable": type(exc).__name__}


def trace_for(payload):
    if TRACE.get():
        return TRACE.get()
    if not isinstance(payload, dict):
        return None
    request = payload.get("request_id", payload.get("requestId"))
    utterance = payload.get("utteranceId")
    return (_requests.get(request) if isinstance(request, str) else None) or (_utterances.get(utterance) if isinstance(utterance, str) else None)


def emit(stage: str, data, trace: dict | None = None) -> None:
    global _seq
    trace = trace or TRACE.get()
    if not trace or not enabled():
        return
    try:
        with _lock:
            _seq += 1
            item = {"version": "r2-observer-v3", "pid": os.getpid(), "seq": _seq,
                    "epoch": time.time(), "monotonic": time.monotonic(), "trace": trace,
                    "stage": stage, "data": safe(data)}
            with (_root / f"trace-{os.getpid()}.jsonl").open("a", encoding="utf-8") as output:
                output.write(json.dumps(item, ensure_ascii=False) + "\n")
    except Exception:
        # Observation must not change the runtime outcome. A visible diagnostic
        # marker makes an unavailable trace an explicit evidence gap.
        try:
            print("ROUND02_OBSERVER_WRITE_FAILED", file=sys.stderr, flush=True)
        except Exception:
            pass


def wire_response(parsed):
    """Explicit allowed response fields; private reasoning is never serialized."""
    if not isinstance(parsed, dict):
        return {"unrecognized_type": type(parsed).__name__}
    result = {key: parsed[key] for key in ("id", "model", "object", "created", "usage", "stop_reason", "stop_sequence") if key in parsed}
    if "choices" in parsed:
        result["choices"] = []
        for choice in parsed["choices"]:
            msg = choice.get("message", {})
            result["choices"].append({"index": choice.get("index"), "finish_reason": choice.get("finish_reason"),
                                      "message": {k: msg[k] for k in ("role", "content", "tool_calls", "refusal") if k in msg}})
    if "content" in parsed:
        result["content"] = [item for item in parsed["content"] if isinstance(item, dict) and item.get("type") in {"text", "tool_use"}]
    if "error" in parsed:
        result["error"] = parsed["error"]
    return safe(result)


def wire_request(body):
    # Context identity is exact without persisting unrelated recalled memory.
    # The marked user input and model output are recorded at their own stages.
    if not isinstance(body, dict):
        return {"unrecognized_type": type(body).__name__}
    result = {key: body[key] for key in ("model", "tools", "tool_choice", "temperature", "max_tokens", "max_completion_tokens", "stream") if key in body}
    for key in ("messages", "system"):
        if key in body:
            encoded = json.dumps(body[key], ensure_ascii=False, sort_keys=True).encode("utf-8")
            result[key + "_sha256"] = hashlib.sha256(encoded).hexdigest()
            result[key + "_bytes"] = len(encoded)
    result["message_shapes"] = [{"role": m.get("role"), "keys": sorted(m), "content_chars": len(str(m.get("content", "")))} for m in body.get("messages", [])]
    return result



def context_segments(extra):
    """Retain only explicit R2 task/receipt segments; omit recalled memory."""
    if not isinstance(extra, str):
        return {"unavailable": "non-string context"}
    prefix = "【任务状态数据，非新增指令】\n"
    if not extra.startswith(prefix):
        return {"unavailable": "missing task prefix"}
    decoder = json.JSONDecoder()
    task, end = decoder.raw_decode(extra[len(prefix):])
    if not isinstance(task, dict) or not isinstance(task.get("original_intent"), str) or not task["original_intent"].startswith("[R2-"):
        return {"unavailable": "not an explicit synthetic task"}
    remainder = extra[len(prefix)+end:].lstrip("\n")
    result = {"task_context": task, "extra_chars": len(extra),
              "extra_sha256": hashlib.sha256(extra.encode("utf-8")).hexdigest()}
    constants = (
        "既有操作仍待确认，本条消息没有授予执行权限。保留所有待办；确认必须绑定展示的参数版本。",
        "旧参数已取消，绝不能执行。仅当用户在本轮明确提供新要求，才能提出新版本待办。",
    )
    receipt_prefix = "【本轮确认的真实回执】\n"
    if remainder.startswith(receipt_prefix):
        receipt, _ = decoder.raw_decode(remainder[len(receipt_prefix):])
        result["confirmation_kind"] = "actual_receipt"
        result["confirmation_receipt"] = receipt
    else:
        note = next((value for value in constants if remainder.startswith(value)), None)
        result["confirmation_kind"] = "literal" if note else "none_or_unrecognized"
        if note:
            result["confirmation_note"] = note
    return result

def task_state(core, session):
    try:
        task = core._task_state.get(session)
        cache = core._result_pages.get(session)
        return {"task": safe(task), "cache_identity": id(cache) if cache else None,
                "cache_refs": list(cache.items) if cache else [], "cache_chars": cache.size if cache else 0,
                "shown_confirmation": core._shown_confirmations.get(session),
                "pending_head": core._pending_writes.get(session),
                "actions": [safe(a) for a in core._action_ledger.records.values() if a.get("session_id") == session] if core._action_ledger is not None else []}
    except Exception as exc:
        return {"observation_error": type(exc).__name__}


def observe_async(obj, name: str, stage: str, arguments: bool = True):
    original = getattr(obj, name)
    @functools.wraps(original)
    async def wrapped(*args, **kwargs):
        if arguments:
            emit(stage + ".in", {"args": args, "kwargs": kwargs})
        try:
            result = await original(*args, **kwargs)
        except BaseException as exc:
            emit(stage + ".exception", {"type": type(exc).__name__, "stack": traceback.format_exc()})
            raise
        emit(stage + ".out", result)
        return result
    setattr(obj, name, wrapped)


def observe_sync(obj, name: str, stage: str):
    original = getattr(obj, name)
    @functools.wraps(original)
    def wrapped(*args, **kwargs):
        emit(stage + ".in", {"args": args, "kwargs": kwargs})
        try:
            result = original(*args, **kwargs)
        except BaseException as exc:
            emit(stage + ".exception", {"type": type(exc).__name__, "stack": traceback.format_exc()})
            raise
        emit(stage + ".out", result)
        return result
    setattr(obj, name, wrapped)


def install_core(core, root: str) -> None:
    global _root, _installed
    if _installed:
        return
    _root = Path(root)
    if not enabled():
        return
    _installed = True
    original_chat = core.handle_chat
    @functools.wraps(original_chat)
    async def chat(text, request_id, conversation_id=None, *args, **kwargs):
        active = enabled() and conversation_id is not None and (text.startswith("[R2-") or conversation_id in _sessions)
        if not active:
            return await original_chat(text, request_id, conversation_id, *args, **kwargs)
        _sessions.add(conversation_id)
        trace = {"request_id": request_id, "session_id": conversation_id}
        _requests[request_id] = trace
        token = TRACE.set(trace)
        emit("input", {"text": text, "args": args, "kwargs": kwargs, "before": task_state(core, conversation_id)})
        try:
            return await original_chat(text, request_id, conversation_id, *args, **kwargs)
        finally:
            emit("turn.final", task_state(core, conversation_id))
            TRACE.reset(token)
    core.handle_chat = chat

    for cls in (core.OpenAICompatibleProvider, core.AnthropicCompatibleProvider):
        # Actual HTTP exchange, BEFORE JSON parsing and adapter normalization.
        original_request = cls._request
        def make_request(original):
            @functools.wraps(original)
            def request(self, req):
                exchange = uuid.uuid4().hex
                try:
                    body = json.loads(req.data or b"{}")
                except (ValueError, TypeError):
                    body = {"body_unparseable": True}
                try:
                    reduced = wire_request(body)
                except Exception as exc:
                    reduced = {"observation_error": type(exc).__name__}
                emit("model.http.request", {"exchange": exchange, "body": reduced})
                try:
                    raw = original(self, req)
                except BaseException as exc:
                    emit("model.http.exception", {"exchange": exchange, "type": type(exc).__name__, "status": getattr(exc, "code", None)})
                    raise
                try:
                    parsed = json.loads(raw.decode("utf-8"))
                except (ValueError, UnicodeError):
                    parsed = {"unparseable": True}
                try:
                    reduced = wire_response(parsed)
                except Exception as exc:
                    reduced = {"observation_error": type(exc).__name__}
                emit("model.http.response", {"exchange": exchange, "raw_bytes_sha256": hashlib.sha256(raw).hexdigest(),
                                              "raw_bytes": len(raw), "payload_without_private_reasoning": reduced})
                return raw
            return request
        cls._request = make_request(original_request)
        observe_async(cls, "complete", "provider.complete", False)
        observe_async(cls, "complete_with_tools", "provider.adapted", False)

    from agent_core.mcp_host import McpServer
    observe_async(McpServer, "_roundtrip", "mcp.raw")
    observe_async(core, "run_tool", "tool")
    observe_async(core, "_execute_authorized_tool", "tool.authorized")
    observe_async(core, "run_agent_loop", "loop", False)
    original_build_messages = core.harness.build_messages
    @functools.wraps(original_build_messages)
    def build_messages(*args, **kwargs):
        try:
            trace = TRACE.get()
            if trace and enabled():
                config = json.loads((_root / "control.json").read_text(encoding="utf-8"))
                sessions = config.get("context_sessions", [])
                valid = isinstance(sessions, list) and all(type(value) is int for value in sessions)
                session_id = trace.get("session_id")
                if valid and type(session_id) is int and session_id in sessions:
                    bound = inspect.signature(original_build_messages).bind(*args, **kwargs)
                    emit("context.synthetic_segments", context_segments(bound.arguments.get("extra_system", "")))
        except Exception as exc:
            try:
                emit("context.observation_error", {"type": type(exc).__name__})
            except Exception:
                pass
        return original_build_messages(*args, **kwargs)
    core.harness.build_messages = build_messages
    observe_sync(core.harness, "parse_reply", "parse")
    observe_sync(core, "_receipt_delivery", "delivery")
    observe_sync(core, "normalize_voice_text", "voice.normalize")
    observe_sync(core, "_fact_promotion_status", "memory.promotion")

    original_event = core.memory.add_event
    @functools.wraps(original_event)
    def add_event(event_type, payload=None):
        result = original_event(event_type, payload)
        body = payload if isinstance(payload, dict) else {}
        trace = trace_for(body)
        emit("state.event", {"event_type": event_type, "payload": payload}, trace)
        return result
    core.memory.add_event = add_event
    observe_sync(core.memory, "add_message", "state.message")
    observe_sync(core.memory, "add_fact", "state.fact")

    original_send = core.hub.send_roles
    @functools.wraps(original_send)
    async def send_roles(roles, payload):
        content = payload.get("payload", payload)
        trace = trace_for(content)
        if trace and isinstance(content.get("utteranceId"), str):
            _utterances[content["utteranceId"]] = trace
        emit("godot.outgoing", {"roles": roles, "event": payload}, trace)
        return await original_send(roles, payload)
    core.hub.send_roles = send_roles
    original_direct = core.hub.send
    @functools.wraps(original_direct)
    async def send(websocket, payload):
        trace = trace_for(payload)
        if not trace and isinstance(payload.get("conversationId"), int) and payload["conversationId"] in _sessions:
            trace = {"session_id": payload["conversationId"], "request_id": "r2-session-response"}
        emit("godot.direct", payload, trace)
        return await original_direct(websocket, payload)
    core.hub.send = send
    original_voice = core.handle_voice_transcription
    @functools.wraps(original_voice)
    async def voice(audio_bytes, generation=None):
        try:
            config = json.loads((_root / "control.json").read_text(encoding="utf-8"))
            active = enabled() and isinstance(config, dict) and time.time() < config.get("synthetic_voice_until", 0)
        except (OSError, ValueError, TypeError):
            active = False
        if not active:
            return await original_voice(audio_bytes, generation)
        trace = {"request_id": "r2-voice-" + str(core.voice_capture.capture_id), "session_id": core.voice_capture.session_id}
        token = TRACE.set(trace)
        try:
            emit("stt.capture", {"generation": generation, "capture": {k: getattr(core.voice_capture, k, None) for k in ("capture_id", "generation", "session_id", "phase")}, "audio_fingerprint": {"bytes": len(audio_bytes), "sha256": hashlib.sha256(audio_bytes).hexdigest()}})
            return await original_voice(audio_bytes, generation)
        finally:
            TRACE.reset(token)
    core.handle_voice_transcription = voice
    observe_sync(core, "transcribe_wav", "stt.raw")
    observe_sync(core, "simplify_transcript", "stt.simplified")
    original_synth = core.SpeechClient.synthesize
    @functools.wraps(original_synth)
    def synth(self, text, *args, **kwargs):
        trace = TRACE.get()
        if trace and enabled():
            try:
                digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
                with _lock:
                    with (_root / "tts-allow.jsonl").open("a", encoding="utf-8") as output:
                        output.write(json.dumps({"sha256": digest, "trace": trace, "epoch": time.time()}) + "\n")
            except Exception:
                try:
                    print("ROUND02_TTS_ALLOW_WRITE_FAILED", file=sys.stderr, flush=True)
                except Exception:
                    pass
        emit("tts.client.in", {"text": text, "args": args, "kwargs": kwargs})
        try:
            result = original_synth(self, text, *args, **kwargs)
        except BaseException as exc:
            emit("tts.client.exception", {"type": type(exc).__name__, "retryable": getattr(exc, "retryable", None), "stack": traceback.format_exc()})
            raise
        emit("tts.client.out", result)
        return result
    core.SpeechClient.synthesize = synth
    emit("observer.installed", {"component": "core", "python": sys.version,
                               "stdout_encoding": stream_value(sys.stdout, "encoding"),
                               "observer_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}, {"request_id": "r2-install"})


def install_tts(tts, root: str) -> None:
    global _root, _installed
    if _installed:
        return
    _root = Path(root)
    if not enabled():
        return
    _installed = True
    original = tts.VoiceSelfCheck.run
    @functools.wraps(original)
    def run(self, text, *args, **kwargs):
        trace = None
        if enabled():
            try:
                digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
                matches = {}
                for line in reversed((_root / "tts-allow.jsonl").read_text(encoding="utf-8").splitlines()):
                    try:
                        row = json.loads(line)
                        if not isinstance(row, dict) or not isinstance(row.get("epoch"), (int, float)) or not isinstance(row.get("trace"), dict):
                            continue
                        if row.get("sha256") == digest and 0 <= time.time() - row["epoch"] < 600:
                            matches[json.dumps(row["trace"], sort_keys=True)] = row["trace"]
                    except (ValueError, TypeError, KeyError):
                        continue
                if len(matches) == 1:
                    trace = next(iter(matches.values()))
                elif matches:
                    trace = {"request_id": "ambiguous-tts-text", "candidates": list(matches.values())}
            except (OSError, ValueError, KeyError):
                pass
        if trace is None:
            return original(self, text, *args, **kwargs)
        token = TRACE.set(trace)
        emit("tts.sidecar.in", {"text": text, "stdout_encoding": stream_value(sys.stdout, "encoding"),
                                "stderr_encoding": stream_value(sys.stderr, "encoding"),
                                "stdout_errors": stream_value(sys.stdout, "errors"),
                                "stdout_isatty": stream_value(sys.stdout, "isatty", True), "utf8_mode": sys.flags.utf8_mode})
        try:
            result = original(self, text, *args, **kwargs)
            emit("tts.sidecar.out", result)
            return result
        except BaseException as exc:
            emit("tts.sidecar.exception", {"type": type(exc).__name__, "stack": traceback.format_exc()})
            raise
        finally:
            TRACE.reset(token)
    tts.VoiceSelfCheck.run = run
    emit("observer.installed", {"component": "tts", "python": sys.version,
                               "stdout_encoding": stream_value(sys.stdout, "encoding"),
                               "observer_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}, {"request_id": "r2-install"})
