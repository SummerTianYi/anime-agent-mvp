"""Text-only live diagnostic. Use Python 3.12 with the Core dependencies."""
import argparse
import ast
import asyncio
import copy
from dataclasses import asdict
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from dotenv import dotenv_values

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
REF = "a4216b9f2d8e71fcb1bb68dffc27c9871ca9587d"
SCENES = json.loads((HERE / "scenes.json").read_text(encoding="utf-8"))
LIMIT = 60


def encoded(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha(obj):
    return hashlib.sha256(obj.encode()).hexdigest()


def read_lines(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()] if path.exists() else []


def append(path, obj):
    with path.open("a", encoding="utf-8", newline="\n") as f:
        f.write(encoded(obj) + "\n")
        f.flush()


def save(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def public_config(path):
    keys = {"DEEPSEEK_BASE_URL", "DEEPSEEK_MODEL", "DEEPSEEK_API_KEY",
            "LLM_PROXY_MODE", "LLM_PROVIDER", "LLM_TIMEOUT_SECONDS"}
    with path.open(encoding="utf-8-sig") as f:
        selected = "".join(line for line in f if line.partition("=")[0].strip() in keys)
    cfg = dict(dotenv_values(stream=io.StringIO(selected), interpolate=False))
    if (cfg.get("DEEPSEEK_BASE_URL", "").rstrip("/"), cfg.get("DEEPSEEK_MODEL"), cfg.get("LLM_PROVIDER")) != (
            "https://api.deepseek.com", "deepseek-flash", "deepseek") or not cfg.get("DEEPSEEK_API_KEY"):
        raise RuntimeError("Unexpected DS profile. No request.")
    return cfg


def start_core(args):
    src = ROOT / "services/agent-core"
    main = "services/agent-core/agent_core/main.py"
    for path in ("services/agent-core/agent_core", "apps/avatar-runtime/runtime.gd", "apps/avatar-runtime/interaction_ui.gd"):
        subprocess.run(["git", "diff", "--quiet", REF, "--", path], cwd=ROOT, check=True)
    original = (ROOT / main).read_text(encoding="utf-8")
    official = args.adapter.read_text(encoding="utf-8")
    def core_ast(source):
        tree = ast.parse(source)
        tree.body = [node for node in tree.body if getattr(node, "name", "") not in
                     {"OpenAICompatibleProvider", "_provider_config", "_reload_provider_config"}]
        return ast.dump(tree)
    if core_ast(official) != core_ast(original):
        raise RuntimeError("Adapter source has non-Provider changes")
    # This is the existing, locally configured official adapter. Pin its source, not a patched model payload.
    if sha(official) != args.adapter_sha:
        raise RuntimeError("Adapter fingerprint mismatch")
    cfg = public_config(args.ds_env)
    for key in list(os.environ):
        if key.startswith(("ANIME_AGENT_", "LLM_", "GLM_", "DEEPSEEK_", "STEPFUN_", "TTS_", "AGENT_CORE_")):
            del os.environ[key]
    os.environ.update(cfg)
    os.environ.update(ANIME_AGENT_DATA_DIR=str(args.state / "data"),
                      ANIME_AGENT_CONFIG_PATH=str(args.state / "absent.env"),
                      ANIME_AGENT_MCP_SERVERS="", ANIME_AGENT_WAKE_WORD="0", ANIME_AGENT_TTS="0",
                      ANIME_AGENT_TOOLS="1", ANIME_AGENT_TOOLS_ROOTS=str(args.state / "sandbox"),
                      ANIME_AGENT_WRITE_ROOTS=str(args.state / "sandbox"), ANIME_AGENT_ALLOWED_COMMANDS="",
                      ANIME_AGENT_VOICE_INPUT_MODE="manual")
    sys.path.insert(0, str(src))
    import agent_core
    spec = importlib.util.spec_from_file_location("agent_core.main", args.adapter)
    core = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = core
    spec.loader.exec_module(core)
    if not core.memory.path.resolve().is_relative_to(args.state) or core.provider.name != "deepseek":
        raise RuntimeError("Unexpected storage or provider")
    import agent_core.harness as harness
    prompt = harness.ACTIVE_PROMPT_OVERRIDE
    assert (ROOT / "docs/assessments/companion-v1.2/SYSTEM_PROMPT.txt").read_text(encoding="utf-8") == prompt + "\n"
    assert not core.TTS_ENABLED and not core.mcp_host.tool_entries()
    return core, prompt


class Wire:
    def __init__(self, core, args, prompt):
        self.core = core
        self.args = args
        self.path = args.output / "requests.jsonl"
        self.original = core.provider._request
        self.prompt = prompt
        self.lock = threading.Lock()
        self.tag = None
        self.expected = None
        self.first = True
        self.effects = []
        self.store = {}
        self.parsed = []
        self.messages = []
        self.loop = asyncio.get_running_loop()
        core.provider._request = self.observe
        # One reservation per transport attempt. Refuse redirects before a second HTTP dispatch.
        def refuse_redirect(handler, req, fp, code, msg, headers, newurl):
            raise urllib.error.HTTPError(req.full_url, code, "Redirect declined by test", headers, fp)
        urllib.request.HTTPRedirectHandler.redirect_request = refuse_redirect
        original_send = core.hub.send_roles
        async def events(roles, event):
            if event["type"] in {"chat.response", "core.error", "session.title"}:
                self.messages.append(copy.deepcopy(event))
            return await original_send(roles, event)
        core.hub.send_roles = events
        original_parse = core.harness.parse_reply
        def parse(text):
            reply = original_parse(text)
            self.parsed.append({"input": text, "parsed": asdict(reply)})
            return reply
        core.harness.parse_reply = parse
        async def deny(name, arguments):
            self.effects.append({"name": name, "result": "blocked at test boundary before dispatch"})
            return {"ok": False, "outcome": "denied", "error": "外部工具在本次隔离测试中不可执行"}
        core._execute_authorized_tool = deny

    def observe(self, req):
        body = json.loads(req.data)
        if req.full_url != "https://api.deepseek.com/chat/completions" or body["model"] != "deepseek-flash":
            raise RuntimeError("Unexpected network destination")
        if not body["messages"][0]["content"].startswith(self.prompt + "\n\n") or body.get("thinking") != {"type": "disabled"}:
            raise RuntimeError("Prompt or official profile mismatch")
        material = encoded(body)
        if any(s in material for s in (os.environ["DEEPSEEK_API_KEY"], "reasoning_content", str(Path.home()), str(self.args.ds_env))):
            raise RuntimeError("Refused non-public request evidence")
        digest = sha(material)
        with self.lock:
            prior = read_lines(self.path)
            count = sum(item["phase"] == "request" for item in prior)
            if count >= LIMIT:
                raise self.core.ProviderError("诊断请求额度已到上限")
            if self.first and self.expected is not None and digest != self.expected:
                raise RuntimeError("First wire payload differs from matched-history original")
            self.first = False
            number = count + 1
            append(self.path, {"n":number, "phase":"request", "turn":self.tag, "body_sha256":digest, "body":body})
        started = time.monotonic()
        result = {"n":number, "phase":"result", "turn":self.tag}
        try:
            raw = self.original(req)
            payload = json.loads(raw)
            result.update(model=payload.get("model"), response_id=payload.get("id"), usage=payload.get("usage"),
                          choices=[{"index": c.get("index"), "finish_reason": c.get("finish_reason"),
                                    "message": {k:v for k,v in c.get("message", {}).items()
                                                if k in {"role","content","tool_calls","refusal"}}}
                                   for c in payload.get("choices", [])])
            return raw
        except Exception as exc:
            result.update(error=type(exc).__name__, status=getattr(exc, "code", None))
            raise
        finally:
            result["seconds"] = round(time.monotonic()-started, 3)
            with self.lock:
                append(self.path, result)


def db_copy(source, target):
    source.backup(target)
    target.commit()


async def run(args):
    core, prompt = start_core(args)
    wire = Wire(core, args, prompt)
    tag = args.group
    replay = args.repeat
    group_name = "reconnect-long" if args.reconnect_long else tag
    initial = args.state / (group_name + "-initial.db")
    if not replay and initial.exists():
        raise RuntimeError("Original group already started")
    turns_file = args.output / "dialogues.jsonl"
    # Each CLI invocation has its own store, session and Core globals.
    core.memory.close()
    group_dir = args.state / ((group_name + "-repeat") if replay else group_name)
    group_dir.mkdir(exist_ok=False)
    core.memory = core.MemoryStore(group_dir)
    sid = core.memory.create_session()["id"]
    core._actions()
    if not replay:
        with sqlite3.connect(initial) as out:
            db_copy(core.memory.connection, out)
    if tag == "memory" and not replay:
        core.memory.add_fact("晨星项目预算120", status="confirmed", scope="session", session_id=sid)
    steps = SCENES[tag]
    for i,text in enumerate(steps, 1):
        remaining = LIMIT - sum(x["phase"]=="request" for x in read_lines(wire.path))
        if remaining < (2 if args.reconnect_long else 1):
            break
        original_id = f"{group_name}-{i}"
        label = ("repeat-" if replay else "") + original_id
        mid = f"synthetic-{tag}-{i}"
        snapshot = args.state / (original_id + ".db")
        saved_task = args.state / (original_id + ".json")
        if replay:
            previous = next(t for t in read_lines(turns_file) if t["id"] == original_id)
            with sqlite3.connect(snapshot) as inp:
                db_copy(inp,core.memory.connection)
            core._action_ledger = None
            core._actions()
            task = json.loads(saved_task.read_text(encoding="utf-8"))
            if task is not None:
                core._task_state[sid] = task
            if core._actions().pending(sid):
                raise RuntimeError("Replay fixture requires no pending operational ticket")
            first = [x for x in read_lines(wire.path) if x["phase"]=="request" and x["turn"]==original_id]
            wire.expected = first[0]["body_sha256"] if first else None
        else:
            with sqlite3.connect(snapshot) as out:
                db_copy(core.memory.connection,out)
            save(saved_task,core._task_state.get(sid))
        history = core.memory.load_messages(50,sid)
        facts = core.memory.recall_facts(sid)
        if replay and (history != previous["history_before"] or facts != previous["facts_before"]):
            raise RuntimeError("Matched history or memory differs")
        wire.tag,wire.first = label,True
        wire.parsed.clear()
        wire.messages.clear()
        wire.effects.clear()
        offset = core.memory.connection.execute("select coalesce(max(id),0) from events").fetchone()[0]
        started = time.monotonic()
        error = None
        try:
            await core.handle_chat(text,mid,sid,effort="deep")
        except Exception as exc:
            error = f"{type(exc).__name__}: {str(exc)[:160]}"
        events = [{"kind":k,"payload":json.loads(v)} for k,v in core.memory.connection.execute(
            "select event_type,payload from events where id>? order by id",(offset,))]
        final = [m for m in wire.messages if m["type"]=="chat.response"]
        row = {"id":label,"user":text,"matched_to":original_id if replay else None,
               "history_before":history,"facts_before":facts,"facts_after":core.memory.recall_facts(sid),
               "parsed":wire.parsed,"delivery_events":wire.messages,"events":events,"external_tool_guard":wire.effects,
               "chat_text":final[-1]["text"] if final else None,"seconds":round(time.monotonic()-started,3),"error":error}
        append(turns_file,row)
        print(label,"responses",len(final),"seconds",row["seconds"],"error",error,flush=True)
        if error or not final:
            break
    core.memory.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state",type=Path,required=True,help="Dedicated scratch directory outside the repository")
    parser.add_argument("--group",choices=SCENES,required=True)
    parser.add_argument("--repeat",action="store_true")
    parser.add_argument("--reconnect-long", action="store_true",
                        help="Fresh continuous session after transport outage; reserve room for one corrective call")
    parser.add_argument("--ds-env",type=Path,required=True,help="Local authorized DS config (never copied)")
    parser.add_argument("--adapter",type=Path,required=True,help="Existing official-DS prep main.py, base 7834720")
    parser.add_argument("--adapter-sha",required=True,help="Expected LF-normalized source SHA256")
    args = parser.parse_args()
    if args.reconnect_long and (args.group != "long" or args.repeat):
        parser.error("--reconnect-long requires the original long scenario")
    args.state = args.state.resolve()
    if args.state.is_relative_to(ROOT) or not (args.state/"companion-live-scratch").is_file():
        parser.error("Dedicated marked scratch required")
    args.output = args.state / "evidence"
    args.output.mkdir(exist_ok=True)
    import msvcrt
    with (args.state/"runner.lock").open("a+b") as lock:
        lock.seek(0)
        msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
        asyncio.run(run(args))
