"""Offline inspection of a named function in one of the six fingerprinted Python 3.13 modules."""
import argparse
import dis
import hashlib
import importlib.util
import marshal
from pathlib import Path
import types

FILES = {
    "live_task_router":"90b5f29bc80dc1456dfba74b755c2001c8fd12976ac9038b35e0ad80b0ff9fa0",
    "main":"e2dbf35723ce15baa7a0eb4f8d46826fc24d8d1e6b3c87ca0013a8d20f5c74f8",
    "platform_core":"308cef797a63661daf9552ba5498aa530964778389c396a86a446af739718a61",
    "task_control":"454279fa8bd2961c9874e91911b8fc93167d3c750b5720a02cf938bac139f8e8",
    "live_confirmation":"9bd95a3a3378ed2c3420b1c9c77bf2142fc3e686f8602a89eef2b138a39217be",
    "agent_workflow":"bcf15e2fffa86f35531f22e5b295969f6c0f9a26361aacede2e3949d005d8bdf",
}
FIELDS = set("user assistant system role content tools model timeout userMessages conversation text action progress cancel ask_user dispatch chat task brief constraints knownInfo preferences confirmed openQuestions kind id epoch _taskControl approvalId challenge cancelRequested status taskId ownerKind ownerId controlEpoch application_result dialogue_history tool_calls arguments name task_stop swarm_status swarm_cancel jobs job_id reply expected_reply_id".split())


def descend(code):
    yield code
    for item in code.co_consts:
        if isinstance(item, types.CodeType):
            yield from descend(item)


def public_literal(value):
    if isinstance(value, tuple):
        return "(" + ", ".join(map(public_literal,value)) + ")"
    if isinstance(value, (int,float,bool,type(None))) or isinstance(value,str) and value in FIELDS:
        return repr(value)
    return "<literal omitted>"


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("folder", type=Path)
    p.add_argument("module", choices=FILES)
    p.add_argument("function", help="Exact co_qualname from AGENT_REFERENCE.md")
    args = p.parse_args()
    raw = (args.folder / "desktop-companion" / "backend" / (args.module + ".pyc")).read_bytes()
    if importlib.util.MAGIC_NUMBER != bytes.fromhex("f30d0d0a") or raw[:4] != importlib.util.MAGIC_NUMBER:
        p.error("Use an independent matching CPython 3.13 interpreter")
    if hashlib.sha256(raw).hexdigest() != FILES[args.module]:
        p.error("File differs from the inspected version")
    code = next((c for c in descend(marshal.loads(raw[16:])) if c.co_qualname == args.function), None)
    if code is None:
        p.error("Unknown function")
    print(code.co_qualname, code.co_varnames[:code.co_argcount + code.co_kwonlyargcount])
    for i in dis.get_instructions(code):
        arg = public_literal(code.co_consts[i.arg]) if i.opcode in dis.hasconst else i.argrepr
        if i.opcode in dis.hasjump:
            arg = str(i.argval)
        print(i.positions.lineno, i.offset, i.opname, arg)
