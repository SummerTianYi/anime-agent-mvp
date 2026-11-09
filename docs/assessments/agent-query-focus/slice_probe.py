"""Pin the isolated main implementation and probe the diagnostics projection."""
import asyncio
import json
from pathlib import Path
import sys
from unittest.mock import AsyncMock, patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "agent-query-delivery"))
from checks import isolate, offline


async def run(repo, state, target):
    isolate(state)
    offline(state)
    sys.path[:0] = [str(repo/"services/agent-core"),str(repo/"services/agent-core/tests")]
    from agent_core import main as core
    from test_agent_loop import ScriptedProvider, _assistant_tool_call, _final_turn, TOOLS_SCHEMA

    assert Path(core.__file__).resolve().is_relative_to(repo) and not core.TTS_ENABLED
    with patch.object(core.hub,"send_roles",new_callable=AsyncMock) as hub:
        for status in ("awaiting_confirmation","unknown","cancelled","succeeded","failed"):
            item={"outcome":status,"ok":status=="succeeded","needs_confirmation":status=="awaiting_confirmation"}
            result=await core.run_agent_loop(ScriptedProvider([_assistant_tool_call(),_final_turn("已核对")]),
                        [{"role":"user","content":"查询合成资料"}], TOOLS_SCHEMA, AsyncMock(return_value=item),
                        on_step=lambda s:core.broadcast_tool_step(s,"slice"))
            event=next(c.args[1] for c in reversed(hub.await_args_list) if c.args[1]["type"]=="agent.tool")
            assert result.steps[0].outcome == event["outcome"] == status
        with patch.object(core.speech_manager,"speak",side_effect=core.SpeechUnavailable("INTERNAL_SYNTH_TRACE")) as speak:
            ok=await core._speak_reply("合成语音测试","slice")
            speak.assert_awaited_once()
        error=next(c.args[1] for c in reversed(hub.await_args_list) if c.args[1]["type"]=="core.error")
        assert not ok and "语音" in error["message"] and "INTERNAL" not in error["message"]
        assert core.memory.connection.execute("SELECT count(*) FROM events WHERE event_type='speech.unavailable' AND payload LIKE '%INTERNAL_SYNTH_TRACE%'").fetchone()[0]==1
    # Run exactly the same ticket ambiguity probe on both the main projection
    # and the complete candidate; even an unexpected approval uses a simulator.
    book=core._actions()
    sid=core.memory.create_session()["id"]
    rows=[]
    for name in ("one","two"):
        rows.append(book.propose(sid,name,name,"write_file",{"path":str(state/(name+".txt")),"content":name}))
    await core._publish_pending(sid)
    with patch.object(core,"_execute_authorized_tool",new_callable=AsyncMock) as execute:
        execute.return_value={"ok":True}
        await core.handle_chat("确认","ambiguous",sid)
        ambiguous=execute.await_count
        await core.handle_chat("确认第2项","numbered",sid)
        matches=[Path(c.args[1]["path"]).name for c in execute.await_args_list]
    actual={"ambiguous_dispatches":ambiguous,"dispatched_files":matches,"states":[r["status"] for r in rows]}
    expected={"main":{"ambiguous_dispatches":1,"dispatched_files":["one.txt"],"states":["succeeded","awaiting_confirmation"]},
              "candidate":{"ambiguous_dispatches":0,"dispatched_files":["two.txt"],"states":["awaiting_confirmation","succeeded"]}}
    print("AUTH_PROBE",json.dumps(actual,ensure_ascii=False))
    assert actual==expected[target], (target,actual)
    assert not (state/"one.txt").exists() and not (state/"two.txt").exists()
    print("SLICE_PROBE_OK 5 outcomes and speech fault separated from diagnostic record")


if __name__=="__main__":
    asyncio.run(run(Path(sys.argv[1]).resolve(),Path(sys.argv[2]).resolve(),sys.argv[3]))
