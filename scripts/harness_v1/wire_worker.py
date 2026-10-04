"""V1 wire scheduling: reuse V0's bounded rate/auth guard, not production Core."""
import asyncio
import json
from pathlib import Path
import sys
from scripts.harness_v0 import resume_worker
from scripts.harness_v0.prepare import dump
from . import worker
resume_worker.worker = worker
if __name__ == "__main__":
    job = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    dump(Path(job["output"]), asyncio.run(resume_worker.execute(job)))
