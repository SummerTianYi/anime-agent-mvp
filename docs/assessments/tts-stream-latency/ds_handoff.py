"""Time the current Core's real DS call through its first speech client invocation."""
import argparse
import asyncio
from collections import defaultdict
import hashlib
import json
import os
from pathlib import Path
import runpy
import sys
import time

HERE = Path(__file__).resolve().parent
GROUPS = [
    ["用一句短话回应我：面包烤好了。","我切开了，里面很松软。请也简短回应。"],
    ["用两三句话，跟我聊聊窗台上新长的一片叶子。","叶尖卷起来一点了，接着说两三句话。"],
    ["请用五六句，讲一个雨滴落到花盆里的小故事。","接上刚才的故事，再讲五六句，让雨慢慢停下来。"],
]

async def main(a):
    settings = runpy.run_path(str(HERE.parent/"companion-live-eval/run_eval.py"))["public_config"](a.ds_env)
    for k in list(os.environ):
        if k.startswith(("ANIME_AGENT_", "TTS_", "LLM_", "DEEPSEEK_", "GLM_", "STEPFUN_")):
            del os.environ[k]
    os.environ.update(settings)
    os.environ.update(ANIME_AGENT_CONFIG_PATH=str(a.scratch/"absent.env"),
                      ANIME_AGENT_DATA_DIR=str(a.scratch/"ds-data"), ANIME_AGENT_TTS="1",
                      TTS_SERVICE_URL="http://127.0.0.1:1", ANIME_AGENT_TOOLS="1",
                      ANIME_AGENT_TOOLS_ROOTS=str(a.scratch), ANIME_AGENT_WRITE_ROOTS=str(a.scratch),
                      ANIME_AGENT_MCP_SERVERS="", ANIME_AGENT_WAKE_WORD="0")
    sys.path.insert(0,str(a.core/"services/agent-core"))
    import agent_core.main as core
    assert core.memory.path.resolve().is_relative_to(a.scratch) and core.provider.name=="deepseek"
    assert not core.mcp_host.tool_entries()
    count=0
    original=core.provider._request
    tag=""
    start=0
    rows=defaultdict(dict)
    def stamp():
        return round((time.perf_counter()-start)*1000,2)
    def request(req):
        nonlocal count
        if count>=12 or req.full_url!="https://api.deepseek.com/chat/completions":
            raise core.ProviderError("isolated budget or destination limit")
        body=json.loads(req.data)
        assert body["model"]=="deepseek-flash" and body["stream"] is False
        count+=1
        attempt={"n":count,"start_ms":stamp()}
        rows[tag].setdefault("ds",[]).append(attempt)
        try:
            data=original(req)
            response=json.loads(data)
            attempt.update(model=response["model"],tokens=response["usage"]["total_tokens"])
            return data
        except Exception as exc:
            attempt["error"]=type(exc).__name__
            raise
        finally:
            attempt["end_ms"]=stamp()
    core.provider._request=request
    async def block(name,args):
        raise RuntimeError("External tools disabled in isolated timing probe")
    core._execute_authorized_tool=block
    core.hub.role_count=lambda role: int(role=="avatar")
    send=core.hub.send_roles
    async def event(roles,item):
        if item["type"]=="chat.response":
            rows[tag].update(chat_response_ms=stamp(),reply_chars=len(item["text"]))
        return await send(roles,item)
    core.hub.send_roles=event
    def synth(text,*args,**kwargs):
        active=core.speech_manager.current
        rows[tag].setdefault("tts_entries",[]).append({"ms":stamp(),"chars":len(text),"id":active.request_id})
        raise core.SpeechUnavailable("isolated timing boundary",retryable=False)
    core.speech_client.synthesize=synth
    for g,messages in enumerate(GROUPS):
        sid=core.memory.create_session()["id"]
        for index,text in enumerate(messages):
            if count>=12:
                break
            tag=f"{['short','medium','long'][g]}-{index+1}"
            rows[tag]["user"]=text
            start=time.perf_counter()
            await core.handle_chat(text,tag,sid,effort="deep")
            if core._background_tasks:
                await asyncio.gather(*list(core._background_tasks),return_exceptions=True)
            print(tag,rows[tag],flush=True)
            report={"rows":dict(rows),"actual_ds_attempts":count,
                    "formal_disk_main_sha256":hashlib.sha256((a.core/"services/agent-core/agent_core/main.py").read_bytes()).hexdigest()}
            a.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    core.memory.close()

if __name__=="__main__":
    p=argparse.ArgumentParser()
    for name in ("core","scratch","ds-env","output"):
        p.add_argument("--"+name,type=Path,required=True)
    a=p.parse_args()
    a.scratch=a.scratch.resolve()
    if (a.scratch/"ds-data").exists() or a.scratch.is_relative_to(a.core.resolve()):
        p.error("Fresh external scratch/data required")
    asyncio.run(main(a))
