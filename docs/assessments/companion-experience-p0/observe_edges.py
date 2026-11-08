"""Offline observations of the existing router and one delayed notification. No tools are dispatched."""
import asyncio
from dataclasses import asdict
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import AsyncMock

from evaluate import HERE, platform


async def observe(folder):
    core, _ = platform.start_core(SimpleNamespace(
        repo=HERE.parents[2], state=Path(folder), phase="archive"))
    from agent_core.actions import decision
    from agent_core.chat_channels import Turn, classify, current
    observations = []
    for s,pending in (("算了，先别寄出去。",True),("那封邮件别发了。",True),
                      ("帮我写文件 draft.txt。不要发给任何人。",False),
                      ("打开文件会发生什么？",False)):
        observations.append(dict(input=s,pending=pending,decision=decision(s),
                                 route=asdict(classify(s,pending=pending,active=False))))
    original = current.set(Turn(3,"old-turn"))
    try:
        core._visible_turn = Turn(4,"new-turn")
        core.hub.send_roles = AsyncMock()
        await core._broadcast_speech_recovery("old-utterance","old-turn")
        roles,event = core.hub.send_roles.await_args.args
        observations.append(dict(source_foreground=core._foreground(),targets=sorted(roles),
                                 event={k:v for k,v in event.items() if k!="timestamp"}))
    finally:
        current.reset(original)
        core.memory.close()
    return observations


if __name__ == "__main__":
    with TemporaryDirectory(prefix="tianyi-edge-") as box:
        print(json.dumps(asyncio.run(observe(box)),ensure_ascii=False,indent=2))
