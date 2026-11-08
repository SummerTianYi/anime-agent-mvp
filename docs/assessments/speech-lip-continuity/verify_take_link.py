"""Isolated HTTP trace through Core -> sidecar self-check -> delivery retry.
The two take scores and playback receipts are injected. No model or audio devices.
"""
import argparse
import asyncio
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import sys
import tempfile
import threading


def run(core, tts, output):
    sys.path[:0] = [str(core / "services/agent-core"), str(tts / "scripts")]
    from agent_core.speech import SpeechClient, SpeechManager
    import tts_server as sidecar

    with tempfile.TemporaryDirectory() as scratch:
        sidecar.SPOOL = Path(scratch)
        sidecar._lifecycle.success()
        sidecar._self_checker = sidecar.VoiceSelfCheck({"enabled":True, "max_takes":2, "threshold":.9})
        scores = iter([.7,.96,.98])
        sidecar._self_checker.check = lambda path, text: next(scores)
        sidecar._synthesize_fn = lambda *args: dict(ok=True, audioPath="fixture.wav", durationMs=10, sampleRate=32000)
        with ThreadingHTTPServer(("127.0.0.1",0),sidecar.Handler) as server:
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            events, deliveries = [], []
            async def play(payload):
                error = "audio-load-failed" if not deliveries else ""
                accepted = await manager.notify_finished(payload["utteranceId"], payload["playbackId"], error=error)
                assert accepted
                deliveries.append(dict(playbackId=payload["playbackId"], error=error, accepted=accepted))
            async def stop(*args):
                raise AssertionError("unexpected interruption")
            manager = SpeechManager(SpeechClient(f"http://127.0.0.1:{server.server_port}"),play,stop,on_timing=events.append)
            try:
                result = asyncio.run(manager.speak("固定测试。", "take-link-fixture"))
                assert result.completed and len(deliveries)==2
            finally:
                server.shutdown()
                thread.join()
            for i, selected in enumerate((2,1)):
                start, ready, dispatch = events[3*i:3*i+3]
                assert [e["stage"] for e in (start,ready,dispatch)] == ["synth-request","ready","dispatch"]
                assert len({(e["utteranceId"], e["requestId"], e["partIndex"], e["preparationId"])
                            for e in (start,ready,dispatch)})==1
                assert ready["selectedTake"]==dispatch["selectedTake"]==selected
                assert len(ready["takes"])==selected and dispatch["playbackId"]==deliveries[i]["playbackId"]
            assert events[0]["preparationId"] != events[3]["preparationId"]
            output.write_text(json.dumps(dict(events=events,syntheticReceipts=deliveries),indent=2)+"\n",encoding="utf8")

if __name__=="__main__":
    p=argparse.ArgumentParser()
    for k in ("mvp","tts","output"):
        p.add_argument(k,type=Path)
    a=p.parse_args()
    run(a.mvp,a.tts,a.output)
