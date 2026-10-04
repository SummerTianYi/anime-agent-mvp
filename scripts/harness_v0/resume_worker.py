"""Codex: scheduling/error-observation wrapper around the immutable V0 worker.

No changes to Core, prompts, tools, fixtures or grading. Stop subsequent wire
requests after a shared-gateway auth/rate error, including adapter retries.
"""
import asyncio
import io
import json
import os
from pathlib import Path
import sys
import time
import urllib.error
import urllib.request

from . import worker
from .budget import BudgetExceeded
from .prepare import dump


class WireGate:
    def __init__(self, gap=2.0):
        self.gap = gap
        self.last = None
        self.halted = None
        self.errors = []

    def reserve(self, original, *args, **kwargs):
        if self.halted:
            raise BudgetExceeded("shared_gateway_paused_" + str(self.halted))
        if self.last is not None:
            time.sleep(max(0, self.gap - (time.monotonic() - self.last)))
        serial = original(*args, **kwargs)
        self.last = time.monotonic()
        return serial

    def open(self, original, opener, req, *args, **kwargs):
        try:
            return original(opener, req, *args, **kwargs)
        except urllib.error.HTTPError as exc:
            body = exc.read(8192)
            self.errors.append({"status": exc.code, "retry_after": exc.headers.get("Retry-After") if exc.headers else None,
                                "error_body": body.decode("utf-8", errors="replace")})
            if exc.code in {401, 403, 429}:
                self.halted = exc.code
            # HTTPError caches read methods; assigning fp does not rewind it.
            preserved = urllib.error.HTTPError(exc.url, exc.code, exc.reason, exc.headers, io.BytesIO(body))
            exc.close()
            raise preserved from exc


async def execute(job):
    key = os.environ.get("HARNESS_MODEL_KEY", "")
    gate = WireGate()
    original_reserve = worker.reserve
    original_open = urllib.request.OpenerDirector.open
    worker.reserve = lambda *a, **kw: gate.reserve(original_reserve, *a, **kw)
    urllib.request.OpenerDirector.open = lambda opener, req, *a, **kw: gate.open(original_open, opener, req, *a, **kw)
    try:
        result = await worker.run(job)
    finally:
        worker.reserve = original_reserve
        urllib.request.OpenerDirector.open = original_open
    result["gateway_error_metadata"] = worker.sanitize(gate.errors, [], key)
    result["wire_gate"] = {"minimum_request_gap_seconds": 2, "halted_status": gate.halted}
    if gate.halted:
        result["blocked"] = "shared_gateway_paused_" + str(gate.halted)
    return result


def main():
    job = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    dump(Path(job["output"]), asyncio.run(execute(job)))


if __name__ == "__main__":
    main()
