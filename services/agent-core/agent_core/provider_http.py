"""Codex: bounded recovery for one model HTTP call, never an agent/tool replay."""
from __future__ import annotations

import asyncio
import http.client
import logging
import math
import random
import socket
import ssl
import time
import urllib.error
import urllib.parse
from contextvars import ContextVar
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from uuid import uuid4

REQUEST_ID = ContextVar("provider_request_id", default="")
DEADLINE = ContextVar("provider_deadline", default=None)
TRANSPORT_ERRORS = (urllib.error.URLError, OSError, http.client.HTTPException)
RETRY_HTTP = {408, 500, 502, 503, 504}
_logger = logging.getLogger(__name__)


def route_for(url: str, mode: str) -> str:
    if mode not in {"auto", "system", "direct"}:
        raise ValueError("LLM_PROXY_MODE must be auto, system or direct")
    host = urllib.parse.urlparse(url).hostname
    if host in {"localhost", "127.0.0.1", "::1"}:
        return "direct"
    # This exact domestic gateway was independently verified reachable directly.
    # Do not silently bypass proxy policy for arbitrary custom endpoints.
    if mode == "auto":
        return "direct" if host == "chatapi.weixin.qq.com" else "system"
    return mode


def category(exc: BaseException) -> str:
    if isinstance(exc, urllib.error.HTTPError):
        return f"http_{exc.code}"
    cause = exc.reason if isinstance(exc, urllib.error.URLError) else exc
    if isinstance(cause, ssl.SSLCertVerificationError):
        return "tls_certificate"
    if isinstance(cause, ssl.SSLError):
        return "tls"
    if isinstance(cause, TimeoutError):
        return "timeout"
    if isinstance(cause, socket.gaierror):
        return "dns"
    if isinstance(cause, ConnectionRefusedError):
        return "connection_refused"
    if isinstance(cause, (ConnectionResetError, BrokenPipeError, http.client.RemoteDisconnected)):
        return "connection_reset"
    if isinstance(cause, http.client.IncompleteRead):
        return "incomplete_response"
    return "transport"


def retry_delay(exc: BaseException, attempt: int) -> float | None:
    """Quota/auth/permanent errors are not outage retries. Honor Retry-After."""
    if isinstance(exc, urllib.error.HTTPError):
        header = exc.headers.get("Retry-After") if exc.headers else None
        if exc.code not in RETRY_HTTP and not (exc.code == 429 and header):
            return None
        if header:
            try:
                delay = float(header)
            except ValueError:
                try:
                    delay = (parsedate_to_datetime(header) - datetime.now(timezone.utc)).total_seconds()
                except (ValueError, TypeError, OverflowError):
                    delay = float("nan")
            if math.isfinite(delay):
                return max(0.0, delay)
            if exc.code == 429:
                return None
    elif category(exc) in {"tls_certificate", "tls"}:
        # Never disable certificate checks or bypass an SSL failure with fallback.
        return None
    elif not isinstance(exc, TRANSPORT_ERRORS):
        return None
    return 0.25 * (2 ** (attempt - 1)) + random.uniform(0.0, 0.1)


def network_message(name: str, exc: BaseException) -> str:
    label = {
        "timeout": "请求超时", "dns": "域名解析失败",
        "connection_refused": "连接被拒绝", "connection_reset": "连接中断",
        "incomplete_response": "响应传输不完整", "tls_certificate": "证书校验失败",
        "tls": "安全连接失败", "transport": "网络传输失败",
    }.get(category(exc), "网络传输失败")
    return f"{name} API 暂时不可用（{label}）。网络恢复后可直接重试，无需重启天依。"


def read_response(response, deadline: float) -> bytes:
    """Check wall time between reads even if a server dribbles bytes forever."""
    chunks = []
    while True:
        if time.monotonic() >= deadline:
            raise TimeoutError("model response deadline exceeded")
        chunk = response.read1(65536)
        if not chunk:
            if response.length:
                raise http.client.IncompleteRead(b"", response.length)
            return b"".join(chunks)
        chunks.append(chunk)


class ModelHttpTransport:
    def __init__(self, on_event=None):
        self.on_event = on_event
        # An uncancellable OS/DNS worker keeps its slot until it really exits.
        # Timeouts cannot create an unbounded pile of detached HTTP workers.
        self._slots = asyncio.Semaphore(2)

    async def _once(self, send, request):
        await self._slots.acquire()
        task = asyncio.create_task(asyncio.to_thread(send, request))

        def finished(done):
            self._slots.release()
            if not done.cancelled():
                done.exception()  # retrieve a late exception; never deliver a late result

        task.add_done_callback(finished)
        return await asyncio.shield(task)

    async def send(self, send, request, *, name, route, timeout, refresh):
        started = time.monotonic()
        deadline = started + timeout
        token = DEADLINE.set(deadline)
        call_id = uuid4().hex
        attempt = 0
        refreshed = False

        def emit(outcome, exc=None):
            info = {
                "call_id": call_id, "request_id": REQUEST_ID.get(), "provider": name,
                "host": urllib.parse.urlparse(request.full_url).hostname,
                "route": route, "attempt": attempt, "outcome": outcome,
                "elapsed_ms": round((time.monotonic() - started) * 1000),
            }
            if exc is not None:
                info["category"] = category(exc)
                info["exception_type"] = type(exc).__name__
                cause = exc.reason if isinstance(exc, urllib.error.URLError) else exc
                errno = getattr(cause, "errno", None)
                if isinstance(errno, int):
                    info["errno"] = errno
            # No exception strings, URL query/path, body, headers or credentials.
            try:
                if self.on_event:
                    self.on_event(info)
            except Exception:
                _logger.warning("Provider transport telemetry unavailable")

        try:
            async with asyncio.timeout(timeout):
                for attempt in range(1, 4):
                    try:
                        result = await self._once(send, request)
                        emit("recovered" if attempt > 1 else "ok")
                        return result
                    except TRANSPORT_ERRORS as exc:
                        delay = retry_delay(exc, attempt)
                        if isinstance(exc, urllib.error.HTTPError) and not refreshed and exc.code in {401, 403, 429}:
                            refreshed = True
                            if await refresh(request):
                                delay = 0.0
                        if attempt >= 3 or delay is None or time.monotonic() + delay >= deadline:
                            emit("failed", exc)
                            raise
                        emit("retry", exc)
                        if isinstance(exc, urllib.error.HTTPError):
                            exc.close()
                        await asyncio.sleep(delay)
        except TimeoutError as exc:
            emit("deadline_exceeded", exc)
            raise
        except asyncio.CancelledError:
            emit("cancelled")
            raise
        finally:
            DEADLINE.reset(token)
