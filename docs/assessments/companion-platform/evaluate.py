"""Text-only live diagnostic. Use Python 3.12 with the Core dependencies."""
import argparse
import asyncio
import copy
from dataclasses import asdict
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from dotenv import dotenv_values

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SCENES = json.loads((HERE / "scenes.json").read_text(encoding="utf-8"))
LIMIT = 40


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
    cfg = public_config(args.ds_env) if args.phase != "archive" else {
        "LLM_PROVIDER":"deepseek","DEEPSEEK_BASE_URL":"https://api.deepseek.com",
        "DEEPSEEK_API_KEY":"synthetic-offline","DEEPSEEK_MODEL":"deepseek-flash"}
    for key in list(os.environ):
        if key.startswith(("ANIME_AGENT_", "LLM_", "GLM_", "DEEPSEEK_", "STEPFUN_", "TTS_", "AGENT_CORE_")):
            del os.environ[key]
    os.environ.update(cfg)
    box = args.state / "sandbox"
    box.mkdir(exist_ok=True)
    os.environ.update(ANIME_AGENT_DATA_DIR=str(args.state / "empty-data"),ANIME_AGENT_CONFIG_PATH=str(args.state / "absent.env"),
                      ANIME_AGENT_MCP_SERVERS="",ANIME_AGENT_WAKE_WORD="0",ANIME_AGENT_TTS="0",
                      ANIME_AGENT_TOOLS="1",ANIME_AGENT_TOOLS_ROOTS=str(box),ANIME_AGENT_WRITE_ROOTS=str(box),
                      ANIME_AGENT_ALLOWED_COMMANDS="",ANIME_AGENT_VOICE_INPUT_MODE="manual")
    sys.path.insert(0, str(args.repo/"services/agent-core"))
    from agent_core import main as core
    from agent_core.harness import ACTIVE_PROMPT_OVERRIDE as prompt
    assert core.memory.path.resolve().is_relative_to(args.state) and core.provider.name == "deepseek"
    assert sha(prompt) == "714ae650ce060f0a645f2fa1055878790438a5e93566ceda18a3ecbdc9d9c9f6"
    assert not core.TTS_ENABLED and not core.mcp_host.tool_entries()
    return core,prompt


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
        self.parsed = []
        self.messages = []
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
        if not (body["messages"][0]["content"] == self.prompt or body["messages"][0]["content"].startswith(self.prompt + "\n")) or body.get("thinking") != {"type": "disabled"}:
            raise RuntimeError("Prompt or official profile mismatch")
        material = encoded(body)
        if any(s in material for s in (os.environ["DEEPSEEK_API_KEY"], "reasoning_content", str(Path.home()), str(self.args.ds_env))):
            raise RuntimeError("Refused non-public request evidence")
        digest = sha(material)
        with self.lock:
            prior = read_lines(self.path)
            count = sum(item["phase"] == "request" for item in prior)
            if count >= min(LIMIT, self.args.ceiling):
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


async def run(args):
    core,prompt=start_core(args)
    wire=Wire(core,args,prompt)
    tts=[]
    async def queue_capture(text,request_id,*unused,**kw):
        tts.append({"request":request_id,"text":text})
        return True
    core._speak_reply=queue_capture
    core.TTS_ENABLED=True
    core.hub.role_count=lambda role: int(role=="avatar")
    output=args.output/"dialogues.jsonl"
    archived=None
    if args.phase=="archive":
        def get(name):
            data=subprocess.check_output(["git","-C",str(ROOT),"show",
                "059298ce04af021efe6297c066c2fd7e9edb4748:docs/assessments/companion-live-eval/"+name])
            return [json.loads(line) for line in data.decode().splitlines()]
        archived=(get("requests.jsonl"),get("dialogues.jsonl"))
    for group in (["daily","low","memory"] if archived else args.groups):
        core.memory.close()
        folder=args.state / (args.phase+"-"+group)
        folder.mkdir()
        core.memory=core.MemoryStore(folder)
        sid=core.memory.create_session()["id"]
        core._action_ledger=None
        core._task_state.clear()
        core._actions()
        if group=="mixed":
            core.memory.add_fact("晨星预算120",status="confirmed",scope="global")
        if archived:
            target=group+("-1" if group=="memory" else "-2")
            old=next(t for t in archived[1] if t["id"]==target)
            for fact in old["facts_before"]:
                core.memory.add_fact(fact,status="confirmed",scope="session",session_id=sid)
            for h in old["history_before"]:
                core.memory.add_message(h["role"],h["content"],"archived",sid)
            results=iter([r for r in archived[0] if r["phase"]=="result" and r["turn"]==target and r.get("choices")])
            def replay(req):
                obj=next(results)
                return json.dumps({"choices":obj["choices"]}).encode()
            core.provider._request=replay
            steps=[old["user"]]
        elif args.phase=="receipt-retest":
            assert group=="mixed"
            result=core.memory.correct_fact(core.memory.prepare_correction("把晨星预算从120更正为175。",sid),"t-mixed-3")
            assert result.get("new_value")=="175" or "175" in str(result)
            prior=next(x for x in read_lines(output) if x["id"]=="after-mixed-4")
            turn=0
            for h in prior["history_before"]:
                if h["role"]=="user":
                    turn+=1
                core.memory.add_message(h["role"],h["content"],"t-mixed-"+str(turn),sid)
            steps=[prior["user"],"取消刚才的操作。"]
        elif args.phase=="matched":
            tag="before-"+group+"-2"
            saved=next(x for x in read_lines(output) if x["id"]==tag)
            for i,h in enumerate(saved["history_before"]):
                core.memory.add_message(h["role"],h["content"],"history-"+str(i//2),sid)
            steps=[saved["user"]]
        else:
            steps=SCENES[group][:args.depth]
        for i,text in enumerate(steps,1):
            n=sum(x["phase"]=="request" for x in read_lines(wire.path))
            if not archived and n>=args.ceiling:
                break
            tag=args.phase+"-"+group+"-"+str(i)
            wire.tag,wire.first=tag,True
            wire.parsed.clear();wire.messages.clear();wire.effects.clear();tts.clear()
            hist=core.memory.load_messages(30,sid)
            rid=("t-"+group+"-"+str(2 if args.phase=="matched" else i+3 if args.phase=="receipt-retest" else i))
            started=time.monotonic()
            await core.handle_chat(text,rid,sid,effort="deep")
            await asyncio.sleep(0)
            bubbles=[{k:v for k,v in e.items() if k!="timestamp"} for e in wire.messages if e["type"]=="chat.response"]
            row={"id":tag,"user":text,"history_before":hist,"wire_turn":wire.tag,"parsed":wire.parsed,"bubbles":bubbles,"tts_queue":list(tts),
                 "errors":[e.get("message") for e in wire.messages if e["type"]=="core.error"],
                 "blocked_external_calls":list(wire.effects),"seconds":round(time.monotonic()-started,3)}
            if archived:
                row.update(archive_id=target,archived_bubble=old["chat_text"],original_provider_messages=[
                    r.get("choices") for r in archived[0] if r["turn"]==target and r["phase"]=="result"])
            if args.phase=="receipt-retest" and i==1:
                row.update(history_matches_before=(hist==prior["history_before"]),input_matches_before=(text==prior["user"]),matched_to=prior["id"])
            if args.phase=="matched":
                row.update(history_matches_before=(hist==saved["history_before"]),input_matches_before=(text==saved["user"]),matched_to=saved["id"])
            append(output,row)
            print(tag,len(bubbles),row["seconds"],len(row["errors"]),flush=True)
            if row["errors"] and not archived:
                raise RuntimeError("Controlled live error; investigate before continuing")
    core.memory.close()


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo",type=Path,required=True,help="Frozen before or candidate source")
    p.add_argument("--state",type=Path,required=True,help="Private empty directory outside a checkout")
    p.add_argument("--ds-env",type=Path)
    p.add_argument("--phase",choices=["archive","before","after","matched","receipt-retest"],required=True)
    p.add_argument("--groups",nargs="+",choices=list(SCENES),default=["daily","joy","low"])
    p.add_argument("--depth",type=int,default=6)
    p.add_argument("--ceiling",type=int,default=40,choices=range(1,41))
    args=p.parse_args()
    args.state=args.state.resolve()
    if args.state.is_relative_to(ROOT) or not (args.state/"synthetic-only").is_file():
        p.error("Mark private isolated scratch with synthetic-only")
    args.output=args.state/"evidence"
    args.output.mkdir(exist_ok=True)
    import msvcrt
    with (args.state/"runner.lock").open("a+b") as lock:
        lock.seek(0)
        msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
        asyncio.run(run(args))
