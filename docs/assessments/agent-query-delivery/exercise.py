"""Run against the checked-out Core with a disposable user profile. No lifecycle sidecars."""
import argparse
import asyncio
import hashlib
import io
import json
import os
from pathlib import Path
import socket
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.request

import uvicorn
import websockets
from dotenv import dotenv_values

from checks import ROOT, isolate

HERE = Path(__file__).resolve().parent
F1 = "你知道现在F1进行到哪一站了吗？积分情况如何"
AWARD = "请搜索网页查一下最近一届诺贝尔物理学奖的得主和获奖理由。"
CINEMA = "请搜索网页查一下今年戛纳电影节金棕榈奖得主。"
ENDPOINTS = {"https://api.deepseek.com/chat/completions":"ds", "https://api.tavily.com/search":"search"}
LIMIT = {"ds":24,"search":8}


def write_line(path, data):
    with path.open("a", encoding="utf8") as out:
        out.write(json.dumps(data, ensure_ascii=False, separators=(",",":")) + "\n")


def credentials(path):
    keys = {"DEEPSEEK_API_KEY","DEEPSEEK_BASE_URL","DEEPSEEK_MODEL","LLM_PROXY_MODE","LLM_PROVIDER","TAVILY_API_KEY"}
    with path.open(encoding="utf-8-sig") as source:
        values = dotenv_values(stream=io.StringIO("".join(l for l in source if l.partition("=")[0].strip() in keys)), interpolate=False)
    assert (values["DEEPSEEK_BASE_URL"].rstrip("/"),values["DEEPSEEK_MODEL"],values["LLM_PROVIDER"]) == ("https://api.deepseek.com","deepseek-flash","deepseek")
    assert values["DEEPSEEK_API_KEY"] and values["TAVILY_API_KEY"]
    return values


class Budget:
    def __init__(self, path, phase, output, offline=False):
        self.path, self.phase, self.output, self.turn, self.offline = path, phase, output, "", offline
        with sqlite3.connect(path) as db:
            db.execute("CREATE TABLE IF NOT EXISTS attempts (id INTEGER PRIMARY KEY,kind TEXT,phase TEXT,turn TEXT,body_hash TEXT)")
        sys.addaudithook(self.audit)

    def audit(self, event, args):
        if event != "urllib.Request":
            return
        if self.offline:
            raise RuntimeError("Replay must not access any HTTP endpoint")
        url, data, _, method = args
        if url not in ENDPOINTS or method != "POST":
            raise RuntimeError("Unapproved HTTP destination")
        kind = ENDPOINTS[url]
        body = json.loads(data)
        if kind == "ds" and body.get("model") != "deepseek-flash":
            raise RuntimeError("Unexpected provider")
        with sqlite3.connect(self.path, isolation_level=None) as db:
            db.execute("BEGIN IMMEDIATE")
            count = db.execute("SELECT count(*) FROM attempts WHERE kind=?",(kind,)).fetchone()[0]
            if count >= LIMIT[kind]:
                db.rollback()
                raise RuntimeError("Assessment transport budget exhausted")
            digest = hashlib.sha256(data).hexdigest()
            db.execute("INSERT INTO attempts(kind,phase,turn,body_hash) VALUES (?,?,?,?)",(kind,self.phase,self.turn,digest))
            db.commit()
        write_line(self.output, {"kind":kind,"n":count+1,"turn":self.turn,"sha256":digest,
            "fields":{k:v for k,v in body.items() if k not in {"messages","tools","api_key"}},
            "messages":len(body.get("messages",[])),"tools":[t["function"]["name"] for t in body.get("tools",[])]})
    @staticmethod
    def no_redirect(handler, req, fp, code, msg, headers, newurl):
        raise urllib.error.HTTPError(req.full_url, code, "Redirect disabled", headers, fp)


async def main(args):
    state = args.state.resolve()
    cfg = ({"DEEPSEEK_BASE_URL":"https://api.deepseek.com","DEEPSEEK_MODEL":"deepseek-flash","LLM_PROVIDER":"deepseek",
            "DEEPSEEK_API_KEY":"offline","TAVILY_API_KEY":"offline"} if args.replay else credentials(args.config))
    isolate(state)
    sys.path.insert(0,str(args.repo.resolve()/"services/agent-core"))
    os.environ.update(cfg)
    os.environ["ANIME_AGENT_TOOLS"] = "1"
    from agent_core import main as core
    from agent_core.mcp_host import McpServer
    from agent_core.harness import ACTIVE_PROMPT_OVERRIDE
    assert hashlib.sha256(ACTIVE_PROMPT_OVERRIDE.encode()).hexdigest() == "714ae650ce060f0a645f2fa1055878790438a5e93566ceda18a3ecbdc9d9c9f6"
    assert core.memory.path.resolve().is_relative_to(state) and core.provider.name == "deepseek" and not core.TTS_ENABLED
    assert not core.mcp_host.servers
    wires = state / "wire.jsonl"
    budget = Budget(args.budget.resolve(),args.phase,wires,offline=bool(args.replay))
    urllib.request.HTTPRedirectHandler.redirect_request = Budget.no_redirect
    orig_request = core.provider._request
    cached_search = {}
    if args.replay:
        recorded = [json.loads(l) for l in (args.replay/"wire.jsonl").read_text("utf8").splitlines()]
        def orig_request(req):
            row = next(r for r in recorded if r.get("result")=="ds" and r["turn"]==budget.turn)
            return json.dumps({"choices":[{"message":msg,"finish_reason":"stop"} for msg in row["reply"]]}).encode()
        for line in (args.replay/"events.jsonl").read_text("utf8").splitlines():
            event=json.loads(line)
            data=event["payload"]
            result=data.get("result",{})
            if result.get("sources"):
                cached_search[data["request_id"]]=result
    def observe(req):
        start = time.monotonic()
        try:
            raw = orig_request(req)
            res = json.loads(raw)
            write_line(wires,{"turn":budget.turn,"result":"ds","usage":res.get("usage"),"elapsed":round(time.monotonic()-start,3),
                "reply":[{k:v for k,v in c["message"].items() if k in {"content","tool_calls"}} for c in res["choices"]]})
            return raw
        except Exception as exc:
            write_line(wires,{"turn":budget.turn,"error":type(exc).__name__,"http":getattr(exc,"code",None)})
            raise
    core.provider._request = observe
    async def speak(text, request_id, narrating=False):
        write_line(state/"tts.jsonl",{"request":request_id,"text":text,"narrating":narrating})
        return True
    core.TTS_ENABLED = True
    core._speak_reply = speak
    core.proactive_policy.allow = lambda: (False,"isolated-window")
    schema = {"name":"tavily_search","description":"Search public web sources for current information.",
        "inputSchema":{"type":"object","properties":{"query":{"type":"string"}},"required":["query"]}}
    if args.phase == "before":
        core.mcp_host.servers["search"] = McpServer("search",[],tools=[schema])
    execute = core._execute_authorized_tool
    async def guarded(name, arguments):
        write_line(state/"dispatch.jsonl",{"request":core.REQUEST_ID.get(),"tool":name,"arguments":arguments})
        if name not in {"get_time","public_web_search","mcp__search__tavily_search"}:
            return {"ok":False,"outcome":"denied","error":"隔离环境禁用此操作"}
        if args.replay and name=="public_web_search":
            return cached_search[core.REQUEST_ID.get()]
        return await execute(name, arguments)
    core._execute_authorized_tool = guarded
    sock = socket.socket()
    sock.bind(("127.0.0.1",0))
    sock.listen()
    port = sock.getsockname()[1]
    url = f"ws://127.0.0.1:{port}/ws"
    server = uvicorn.Server(uvicorn.Config(core.app,lifespan="off",log_level="error"))
    running = asyncio.create_task(server.serve(sockets=[sock]))
    proc = None
    window = state / "window.jsonl"
    def labels():
        if not window.exists():
            return []
        return [json.loads(l) for l in window.read_text("utf8").splitlines() if l.endswith("}")]
    async def wait_for(check, deadline):
        async with asyncio.timeout(deadline):
            while not check():
                if proc is not None and proc.poll() is not None:
                    raise RuntimeError("Godot window exited unexpectedly")
                await asyncio.sleep(0.05)
    async def receive(ws, kind, rid=""):
        async with asyncio.timeout(125):
            while True:
                data = json.loads(await ws.recv())
                if data["type"] in {"permission.pending","agent.tool","chat.response","session.switched","core.error"}:
                    write_line(state/"frames.jsonl",data)
                if data["type"]==kind and (not rid or data.get("request_id")==rid):
                    return data
    try:
        await wait_for(lambda:server.started,10)
        env = {k:v for k,v in os.environ.items() if not any(w in k for w in ("API_KEY","TOKEN","PASSWORD","SECRET"))}
        env.update(QUERY_WINDOW_LOG=str(window),AGENT_CORE_WS_URL=url)
        with (state/"godot.txt").open("w",encoding="utf8") as log:
            proc = subprocess.Popen([str(args.godot),"--path",str(args.repo.resolve()/"apps/avatar-runtime"),"--audio-driver","Dummy",
                "--rendering-method","gl_compatibility","--script",str(HERE/"read_window.gd")],
                env=env,stdout=log,stderr=subprocess.STDOUT)
        await wait_for(lambda:any(l.get("ready") for l in labels()),35)
        async with websockets.connect(url,proxy=None) as ui:
            await receive(ui,"core.status")
            await ui.send(json.dumps({"type":"client.hello","role":"ui"}))
            await receive(ui,"client.ready")
            for mode, turns in (("normal",[F1]),("award",[AWARD]),("ask",[AWARD,"确认"]),("fault",[CINEMA])):
                if args.cases and mode not in args.cases:
                    continue
                if args.phase == "after":
                    from agent_core.permissions import PolicyRule, ASK
                    core.permission_engine = core.PermissionEngine()
                    if mode == "ask":
                        core.permission_engine.rules.insert(0,PolicyRule("assessment-ask","public_web_search","user",ASK))
                    if mode == "fault":
                        os.environ.pop("TAVILY_API_KEY",None)
                    else:
                        os.environ["TAVILY_API_KEY"]=cfg["TAVILY_API_KEY"]
                await ui.send(json.dumps({"type":"session.new"}))
                sid = (await receive(ui,"session.switched"))["conversationId"]
                for i, question in enumerate(turns):
                    rid = f"{args.phase}-{mode}-{i+1}"
                    budget.turn=rid
                    await ui.send(json.dumps({"type":"chat.message","text":question,"messageId":rid,"conversationId":sid,"effort":"standard"}))
                    reply = await receive(ui,"chat.response",rid)
                    await wait_for(lambda:any(l.get("request")==rid and l["type"]=="chat.response" for l in labels()),8)
                    seen = next(l for l in labels() if l.get("request")==rid and l["type"]=="chat.response")
                    assert reply["text"] in seen["labels"]
                    write_line(state/"turns.jsonl",{"request":rid,"question":question,"text":reply["text"],"channel":reply["channel"],
                        "session":sid,"task":reply.get("taskId")})
                    print(rid,reply["channel"],flush=True)
            await asyncio.sleep(0.3)
        for kind, payload in core.memory.connection.execute("SELECT event_type,payload FROM events ORDER BY id"):
            if kind.startswith(("permission.","chat.delivery","agent.tools","tool.result")):
                write_line(state/"events.jsonl",{"type":kind,"payload":json.loads(payload)})
        write_line(state/"isolation.jsonl",{"core_pid":os.getpid(),"godot_pid":proc.pid,"port":port,"window":True,
            "lifespan":"off","speaker":"queue capture","provider":"recorded" if args.replay else "deepseek","synthesis":False})
    finally:
        if proc and proc.poll() is None:
            proc.terminate()
            proc.wait(timeout=10)
        server.should_exit=True
        await running
        core.memory.close()


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("phase",choices=("before","after"))
    for name in ("state","budget","config","godot"):
        p.add_argument(name,type=Path)
    p.add_argument("--cases",nargs="+",choices=("normal","award","ask","fault"))
    p.add_argument("--repo",type=Path,default=ROOT,help="Product checkout; use the fixed candidate to reproduce before")
    p.add_argument("--replay",type=Path,help="Replay captured search and DS receipts; all HTTP is disabled")
    asyncio.run(main(p.parse_args()))
