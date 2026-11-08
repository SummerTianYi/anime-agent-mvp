"""Codex: all speech scenes through real Core WS + Godot audio, private fixture.

No production Core, database, window or processes are changed. --real-service
only makes synthetic-text synthesis requests to the existing local voice; all
faults are injected into this test's client/Avatar, never the live TTS process.
"""
import argparse
import asyncio
import json
import math
import os
from pathlib import Path
import shutil
import socket
import struct
import subprocess
import sys
import time
import wave


async def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo',type=Path,required=True)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--real-service',action='store_true')
    args=parser.parse_args()
    repo, source=args.repo.resolve(),args.source.resolve()
    assert repo != source and (repo/'.farewell-test-fixture').is_file()
    out=repo.parent/('speech-loop-'+time.strftime('%H%M%S'))
    out.mkdir()
    print('EVIDENCE='+str(out),flush=True)
    avatar=repo/'apps/avatar-runtime'
    for name in ('runtime.gd','speech_output.gd','farewell_speech_gate.gd','verify_speech_delivery.gd',
                 'mocap/farewell/exit_probe.gd','mocap/farewell/speech_probe.gd'):
        shutil.copy2(source/'apps/avatar-runtime'/name,avatar/name)
    launcher=avatar/'launcher.gd'
    launcher.write_text(launcher.read_text(encoding='utf-8').replace(
        'mocap/farewell/exit_probe.gd','mocap/farewell/speech_probe.gd'),encoding='utf-8')
    for key in list(os.environ):
        if key.startswith(('ANIME_AGENT_','GLM_','DEEPSEEK_','STEPFUN_','AGENT_CORE_','TTS_','LLM_')):
            os.environ.pop(key)
    os.environ.update(ANIME_AGENT_CONFIG_PATH=str(out/'absent.env'),ANIME_AGENT_DATA_DIR=str(out/'data'),
        LLM_PROVIDER='mock',ANIME_AGENT_TTS='1',ANIME_AGENT_TTS_NARRATE='0',
        ANIME_AGENT_WAKE_WORD='0',ANIME_AGENT_MCP_SERVERS='',ANIME_AGENT_TOOLS='0',
        ANIME_AGENT_QUIET_START='00:00',ANIME_AGENT_QUIET_END='00:00',
        ANIME_AGENT_IDLE_THRESHOLD='0',ANIME_AGENT_FAREWELL_PRECACHE='0')
    sys.path.insert(0,str(source/'services/agent-core'))
    import uvicorn
    import websockets
    from agent_core import main as core
    from agent_core.speech import SpeechClient, SpeechUnavailable
    events=[]
    original_event=core.memory.add_event
    def record(kind, data):
        events.append({'type':kind,**data})
        return original_event(kind,data)
    core.memory.add_event=record
    core._STARTUP_GREETINGS=('我上线啦。',)
    core._IDLE_LINES=('记得喝水哦。',)
    core.FAREWELL_LINES=('下次再见哦。',)
    class Provider:
        name='closed-loop-fixture'
        async def complete(self,messages):
            return json.dumps({'reply':'听到啦。测试成功。','emotion':'happy','gesture':'none',
                               'memory_candidate':None,'session_title':'isolated speech test'},ensure_ascii=False)
    core.provider=Provider()
    tone=out/'tone.wav'
    with wave.open(str(tone),'wb') as wav:
        wav.setparams((1,2,32000,0,'NONE','none'))
        wav.writeframes(b''.join(struct.pack('<h',int(1500*math.sin(i*2*math.pi*440/32000))) for i in range(16000)))
    class FaultClient:
        faults=['warming','warming']
        calls=0
        real=SpeechClient('http://127.0.0.1:8770') if args.real_service else None
        def is_healthy(self,**kwargs): return True
        def synthesize(self,text,speed=1):
            self.calls+=1
            fault=self.faults.pop(0) if self.faults else ''
            if fault=='warming': raise SpeechUnavailable('isolated warming',retryable=True)
            if fault=='missing': return {'audioPath':str(out/'missing.wav'),'durationMs':1,'sampleRate':32000}
            if fault=='corrupt':
                bad=out/'corrupt.wav'; bad.write_bytes(b'invalid WAV fixture')
                return {'audioPath':str(bad),'durationMs':1,'sampleRate':32000}
            if self.real: return self.real.synthesize(text,speed)
            return {'audioPath':str(tone),'durationMs':500,'sampleRate':32000}
    fault=FaultClient()
    core.speech_client=fault
    core.speech_manager.client=fault
    core.speech_manager.retry_interval_seconds=.1
    # Keep the production 5s grace: Avatar reconnect alone has a 2s backoff.
    assert core.speech_manager.completion_grace_seconds == 5.0
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0)); port=sock.getsockname()[1]
    assert port not in (8765,8770)
    server=uvicorn.Server(uvicorn.Config(core.app,host='127.0.0.1',port=port,log_level='warning'))
    server_task=asyncio.create_task(server.serve())
    process=None
    log=(out/'godot.log').open('w',encoding='utf-8')
    results=[]
    def traces():
        path=out/'tts-playback.jsonl'
        if not path.exists(): return []
        rows=[]
        for line in path.read_text(encoding='utf-8').splitlines():
            try: rows.append(json.loads(line))
            except json.JSONDecodeError: pass # last append can be in flight
        return rows
    async def wait(predicate,label,timeout=90):
        deadline=time.monotonic()+timeout
        while time.monotonic()<deadline:
            if predicate(): return
            if process is not None and process.poll() is not None: raise AssertionError('Avatar exited: '+label)
            await asyncio.sleep(.05)
        raise AssertionError('Timed out: '+label)
    async def control(**command):
        ident=str(time.time_ns())
        tmp=out/'control.tmp'
        tmp.write_text(json.dumps({'id':ident,**command}),encoding='utf-8')
        tmp.replace(out/'control.json')
        await wait(lambda:any(r.get('event')=='control' and r.get('id')==ident for r in traces()),'control')
    def passed(name):
        results.append(name)
        print('PASS '+name,flush=True)
    try:
        await wait(lambda:server.started,'Core server')
        env=dict(os.environ)
        env.update(AGENT_CORE_WS_URL=f'ws://127.0.0.1:{port}/ws',FAREWELL_EVIDENCE=str(out),
                   TTS_AUDIBLE_TEST='1' if args.real_service else '0',FAREWELL_SCENARIO='idle')
        exe=source.parent/'tools/godot-4.7.2/Godot_v4.7.2-stable_win64_console.exe'
        process=subprocess.Popen([str(exe),'--path',str(avatar),'--script','res://launcher.gd',
                                  '--resolution','16x16','--position','-100,-100'],env=env,
                                 stdout=log,stderr=log,creationflags=subprocess.CREATE_NO_WINDOW)
        await wait(lambda:core.proactive_policy._last_spoken>0,'startup greeting completion')
        assert any(r.get('event')=='finished' for r in traces())
        passed('startup greeting survives initial warmup and completes in Godot')
        await core._proactive_idle(5000)
        assert core.idle_policy._last_spoken>0
        passed('idle reminder confirmed before cooldown')
        async with websockets.connect(f'ws://127.0.0.1:{port}/ws', proxy=None) as ui:
            await ui.send(json.dumps({'type':'client.hello','role':'ui'}))
            await ui.send(json.dumps({'type':'chat.message','messageId':'loop-chat','text':'测试语音回复','effort':'chill'}))
            await wait(lambda:any(e['type']=='speech.completed' and e.get('request_id')=='loop-chat' for e in events),
                       'chat narration')
        passed('chat request to two-part spoken reply completes over real WS')
        for failure in ('missing','corrupt','warming'):
            fault.faults=[failure]
            assert await core._speak_reply('测试成功。','loop-'+failure)
            passed(f'{failure} audio recovers with completed playback')
        before=len([r for r in traces() if r.get('event')=='finished'])
        await control(drop=1)
        assert await core._speak_reply('测试成功。','loop-lost-ack')
        after=len([r for r in traces() if r.get('event')=='finished'])
        assert after-before==1, 'lost ack replayed audio'
        passed('lost completion receipt recovered without duplicate playback')
        before=len([r for r in traces() if r.get('event')=='finished'])
        await control(disconnect=True)
        assert await core._speak_reply('测试成功。','loop-ws-reconnect')
        assert len([r for r in traces() if r.get('event')=='finished'])-before==1
        passed('WS drops at completion; reconnect confirms once without replay')
        await control()
        await core._precache_farewell_audio()
        await wait(lambda:any(r.get('event')=='cache' and r.get('count',0)>0 for r in traces()),'cached farewell')
        # Delete only this test's derived cache, then take only this Core offline.
        for audio in core.FAREWELL_AUDIO_CACHE.values():
            path=Path(audio['audioPath']).resolve()
            assert path.is_relative_to(out.resolve())
            path.unlink()
        server.should_exit=True
        await asyncio.wait_for(server_task,10)
        await control(exit=True)
        await asyncio.to_thread(process.wait,15)
        rows=traces()
        assert any(r.get('event')=='started' and r.get('requestId','').startswith('exit-') and r['playing'] for r in rows)
        assert rows[-1]['event']=='exit' and rows[-1]['reason']=='animation_finished', rows[-3:]
        passed('farewell plays from memory with Core offline and cache file removed, then exits')
        if args.real_service:
            mixes=[r for r in rows if r.get('event')=='audio-mix']
            assert len(mixes)>=10 and all(r['peak']>0 and r['samples']>0 and not r['muted'] for r in mixes), mixes
            passed('real voice has nonzero unmuted Godot output for every tested line')
    finally:
        if process is not None and process.poll() is None:
            process.terminate() # Only the Popen handle owned by this fixture.
            await asyncio.to_thread(process.wait,10)
        server.should_exit=True
        if not server_task.done():
            await asyncio.wait_for(server_task,10)
        log.close()
        (out/'results.json').write_text(json.dumps({'passed':results,'synthesisCalls':fault.calls,
            'realVoice':args.real_service,'events':events},ensure_ascii=False,indent=2),encoding='utf-8')


if __name__=='__main__':
    asyncio.run(main())
