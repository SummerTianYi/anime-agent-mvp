"""Loopback WebSocket smoke with a synthetic speaker and a correlated playback ACK."""
import argparse
import asyncio
import json
import os
from pathlib import Path
import socket
import sys
import tempfile

import uvicorn
import websockets


async def check(repo, evidence):
    with tempfile.TemporaryDirectory(prefix="tianyi-local-bridge-") as scratch:
        for name in list(os.environ):
            if name.startswith(("ANIME_AGENT_","AGENT_CORE_","LLM_","TTS_","DEEPSEEK_","GLM_")):
                os.environ.pop(name)
        os.environ.update(ANIME_AGENT_CONFIG_PATH=scratch+"/absent.env",ANIME_AGENT_DATA_DIR=scratch,
                          LLM_PROVIDER="mock",ANIME_AGENT_TTS="0",ANIME_AGENT_WAKE_WORD="0",
                          ANIME_AGENT_PROACTIVE="0",ANIME_AGENT_MCP_SERVERS="",ANIME_AGENT_FAREWELL_PRECACHE="0",
                          ANIME_AGENT_VOICE_INPUT_MODE="manual")
        src=repo/"services/agent-core"
        sys.path[:0]=[str(src),str(src/"tests")]
        from agent_core import main as core
        from test_speech_ws import ScriptedProvider, FakeSpeechClient
        core.provider=ScriptedProvider("这是一条合成桥接测试。")
        core.TTS_ENABLED=True
        core.speech_manager=core.SpeechManager(FakeSpeechClient(),core._broadcast_speak,core._broadcast_speech_stop)
        bound=socket.socket()
        bound.bind(("127.0.0.1",0))
        bound.listen()
        url=f"ws://127.0.0.1:{bound.getsockname()[1]}/ws"
        server=uvicorn.Server(uvicorn.Config(core.app,lifespan="off",log_level="warning"))
        running=asyncio.create_task(server.serve(sockets=[bound]))
        try:
            while not server.started:
                await asyncio.sleep(0.01)
            async with websockets.connect(url,proxy=None) as avatar,websockets.connect(url,proxy=None) as ui:
                async def until(ws,kind):
                    async with asyncio.timeout(5):
                        while True:
                            payload=json.loads(await ws.recv())
                            if payload["type"]==kind:
                                return payload
                for ws,role in ((avatar,"avatar"),(ui,"ui")):
                    await until(ws,"core.status")
                    await ws.send(json.dumps({"type":"client.hello","role":role}))
                    assert (await until(ws,"client.ready"))["role"]==role
                await avatar.send(json.dumps({"type":"avatar.interaction","event":"avatar.clicked","payload":{"x":20,"y":40}}))
                assert (await until(ui,"ui.menu.toggle"))["payload"]=={"x":20,"y":40}
                await ui.send(json.dumps({"type":"avatar.command","event":"avatar.wave","payload":{}}))
                assert (await until(avatar,"avatar.command"))["event"]=="avatar.wave"
                await ui.send(json.dumps({"type":"chat.message","messageId":"bridge-smoke","text":"今天雨停了"}))
                frames=[]
                acknowledgement=None
                async with asyncio.timeout(8):
                    while True:
                        e=json.loads(await avatar.recv())
                        frames.append({k:v for k,v in e.items() if k in ("type","state","text","channel","requestId","turnId","conversationId","request_id")})
                        if e["type"]=="avatar.speak":
                            acknowledgement={k:e[k] for k in ("utteranceId","playbackId","partIndex")}
                            await avatar.send(json.dumps({"type":"speech.finished",**acknowledgement,"interrupted":False}))
                        if acknowledgement and e["type"]=="agent.state" and e["state"]=="idle":
                            break
                reply=next(e for e in frames if e["type"]=="chat.response")
                voice=next(e for e in frames if e["type"]=="avatar.speak")
                assert reply["text"]==voice["text"] and reply.get("channel","companion")=="companion"
                assert voice["requestId"]==reply["request_id"]=="bridge-smoke"
                assert voice.get("conversationId",reply["conversationId"])==reply["conversationId"]
                record={"transport":"loopback /ws","speaker":"synthetic ACK, no device or TTS inference",
                        "menu_and_wave":True,"frames":frames,"matched_ack":bool(acknowledgement)}
                evidence.write_text(json.dumps(record,ensure_ascii=False,indent=2)+"\n","utf8")
                print("BRIDGE_OWNERSHIP_OK")
        finally:
            server.should_exit=True
            await running
            core.memory.close()


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args()
    asyncio.run(check(args.repo.resolve(),args.out))
