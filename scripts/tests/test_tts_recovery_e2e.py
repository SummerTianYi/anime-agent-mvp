"""Codex: real Windows processes/HTTP, isolated synthetic voice; no production faults."""
import argparse
import ctypes
from ctypes import wintypes as w
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import time
import urllib.request
import venv
import wave
from concurrent.futures import ThreadPoolExecutor


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--sidecar',type=Path,required=True)
    args=parser.parse_args()
    source=args.source.resolve(); sidecar=args.sidecar.resolve()
    bench=Path(tempfile.mkdtemp(prefix='codex-tts-e2e-'))
    repo=bench/'fixture'; tts=bench/'tianyi-tts'
    print('TTS_EVIDENCE='+str(bench),flush=True)
    for path in (repo/'scripts',repo/'apps/avatar-runtime',tts/'scripts'):
        path.mkdir(parents=True)
    for path in (repo,tts): (path/'.tts-test-fixture').write_text('Codex isolated synthetic voice test')
    for name in ('startup-common.ps1','tts-lifecycle.ps1','watch-tts-session.ps1'):
        shutil.copy2(source/'scripts'/name,repo/'scripts'/name)
    shutil.copy2(source/'scripts/tests/tts-driver.ps1',repo/'scripts/tts-driver.ps1')
    shutil.copy2(source/'scripts/tests/tts-fixture-server.py',tts/'scripts/tts_server.py')
    for origin,dest in (('tts_server.py','tts_implementation.py'),('service_health.py','service_health.py')):
        shutil.copy2(sidecar/'scripts'/origin,tts/'scripts'/dest)
    venv.EnvBuilder(with_pip=False).create(tts/'venv')
    (repo/'.env').write_text('LLM_PROVIDER=mock\n')
    (repo/'apps/avatar-runtime/project.godot').write_text('[application]\nconfig/name="Codex TTS isolated actor"\n')
    (repo/'apps/avatar-runtime/actor.gd').write_text('extends SceneTree\nfunc _init():\n\tpass\n')
    def port():
        with socket.socket() as s: s.bind(('127.0.0.1',0)); return s.getsockname()[1]
    tts_port=port(); core_port=port()
    assert tts_port not in (8765,8770) and core_port not in (8765,8770,tts_port)
    env={k:v for k,v in os.environ.items() if not k.startswith(('AGENT_CORE_','ANIME_AGENT_','TTS_','LLM_','GLM_','DEEPSEEK_','STEPFUN_'))}
    env.pop('PSModulePath',None)
    for key in ('APPDATA','LOCALAPPDATA','TEMP','TMP'):
        (bench/key).mkdir(); env[key]=str(bench/key)
    env.update(ANIME_AGENT_TTS='1',TTS_SERVICE_URL=f'http://127.0.0.1:{tts_port}',TTS_WORKSPACE=str(tts),
               AGENT_CORE_PORT=str(core_port),LLM_PROVIDER='mock',ANIME_AGENT_WAKE_WORD='0',ANIME_AGENT_MCP_SERVERS='',PYTHONDONTWRITEBYTECODE='1',PYTHONIOENCODING='utf-8')
    ps_exe=str(Path(os.environ['SystemRoot'])/'System32/WindowsPowerShell/v1.0/powershell.exe')
    flags=subprocess.CREATE_NO_WINDOW
    def ps(command):
        r=subprocess.run([ps_exe,'-NoProfile','-ExecutionPolicy','Bypass','-Command',command],env=env,
                         capture_output=True,text=True,encoding='utf-8',errors='replace',creationflags=flags,timeout=30)
        if r.returncode: raise RuntimeError(r.stdout+r.stderr)
        return r.stdout.strip()
    protected=json.loads(ps("Get-CimInstance Win32_Process | Where-Object { $_.Name -like 'Godot*' -or $_.CommandLine -match 'agent_core.main|tts_server.py|core_watchdog.ps1|watch-tts-session.ps1' } | Select-Object ProcessId,Name,@{n='ticks';e={$_.CreationDate.Ticks}} | ConvertTo-Json -Compress"))
    if isinstance(protected,dict): protected=[protected]
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.OpenProcess.argtypes=[w.DWORD,w.BOOL,w.DWORD]; kernel.OpenProcess.restype=w.HANDLE
    kernel.GetExitCodeProcess.argtypes=[w.HANDLE,ctypes.POINTER(w.DWORD)]; kernel.CloseHandle.argtypes=[w.HANDLE]
    handles=[]
    for row in protected:
        handle=kernel.OpenProcess(0x1000,False,row['ProcessId']); code=w.DWORD()
        if handle and kernel.GetExitCodeProcess(handle,ctypes.byref(code)) and code.value==259: handles.append((row,handle))
        elif handle: kernel.CloseHandle(handle)
    (bench/'protected.json').write_text(json.dumps([r for r,h in handles],indent=2))
    def protect():
        for row,handle in handles:
            code=w.DWORD(); assert kernel.GetExitCodeProcess(handle,ctypes.byref(code)) and code.value==259, ('pre-existing process changed',row)
    def state():
        # CIM and socket tables are separate snapshots: a just-created worker
        # can bind between them. Retry observation only, never weaken ownership
        # or treat an unverified port as healthy. Persistent conflicts still fail.
        for attempt in range(3):
            protect()
            try:
                return json.loads(ps("& '"+str(repo/'scripts/tts-driver.ps1')+"'"))
            except RuntimeError as exc:
                if 'Foreign/unverified TTS port owner' not in str(exc) or attempt == 2:
                    raise
                time.sleep(.2)
    def health():
        try:
            with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(env['TTS_SERVICE_URL']+'/health',timeout=.5) as r: return json.load(r)
        except Exception: return {}
    def wait(fn,seconds=45):
        deadline=time.monotonic()+seconds
        while time.monotonic()<deadline:
            protect(); result=fn()
            if result: return result
            time.sleep(.2)
        raise AssertionError('condition deadline exceeded')
    def control(**value): (tts/'control.json').write_text(json.dumps(value))
    def kill_tts(snapshot):
        # Identity/command/venv/port checked in the fixture-only driver as well.
        row=next(x for x in snapshot['tts'] if x['ProcessId']==snapshot['listener'])
        assert row['ProcessId'] not in [r['ProcessId'] for r,h in handles]
        ps("& '"+str(repo/'scripts/tts-driver.ps1')+f"' -Action stop -TargetId {row['ProcessId']} -TargetTicks {row['Ticks']}")
    actors=[]; watchers=[]; results=[]; foreign=None
    godot=source.parent/'tools/godot-4.7.2/Godot_v4.7.2-stable_win64.exe'
    def actor():
        p=subprocess.Popen([str(godot),'--headless','--path',str(repo/'apps/avatar-runtime'),'--script','res://actor.gd'],env=env,
                           stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=flags)
        actors.append(p); snapshot=wait(lambda: (s if (s:=state())['avatar'] else None))
        return p,snapshot
    def watcher(snapshot):
        log=open(bench/f'watch-{len(watchers)}.log','w',encoding='utf-8')
        p=subprocess.Popen([ps_exe,'-NoProfile','-ExecutionPolicy','Bypass','-File',str(repo/'scripts/watch-tts-session.ps1'),
            '-AvatarId',str(snapshot['avatar']),'-AvatarTicks',str(snapshot['avatarTicks']),'-PollSeconds','.2','-WarmupSeconds','5'],
            env=env,stdout=log,stderr=log,creationflags=flags)
        log.close(); watchers.append(p); return p
    def passed(name,**extra):
        protect(); row={'case':name,'result':'PASS',**extra}; results.append(row)
        (bench/'results.json').write_text(json.dumps(results,indent=2)); print(json.dumps(row),flush=True)
    try:
        control(warm=2)
        a,s=actor(); watcher(s)
        h=wait(lambda: h if (h:=health()).get('ok') else None)
        passed('cold-ready-only-after-warmup',pid=h['pid'])
        old=h['pid']; control(legacy_pid=old)
        h=wait(lambda:h if (h:=health()).get('ok') and h.get('pid') and h['pid']!=old else None)
        control(); passed('owned-legacy-server-upgrades-on-new-session',pid=h['pid'])
        first=state(); before=time.monotonic(); control(); kill_tts(first)
        h=wait(lambda: h if (h:=health()).get('ok') and h['pid']!=first['listener'] else None)
        passed('kill-owned-sidecar-revives',seconds=round(time.monotonic()-before,3),pid=h['pid'])
        active=state(); duplicate=watcher(active); duplicate.wait(timeout=18)
        assert health()['pid']==h['pid']; passed('duplicate-supervisor-no-duplicate-tts')
        duplicate_server=subprocess.run([str(tts/'venv/Scripts/python.exe'),str(tts/'scripts/tts_server.py'),'--port',str(tts_port)],
            env=env,capture_output=True,text=True,encoding='utf-8',errors='replace',creationflags=flags,timeout=15)
        assert duplicate_server.returncode!=0 and 'TTS_SERVER_WARMING' not in duplicate_server.stdout
        assert health()['pid']==h['pid']; passed('exclusive-bind-rejects-second-server-before-model-load')
        def synth(timeout=35):
            request=urllib.request.Request(env['TTS_SERVICE_URL']+'/synthesize',data=b'{"text":"test"}',headers={'Content-Type':'application/json'})
            with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(request,timeout=timeout) as response:
                return json.load(response)
        control(synth_delay=3)
        with ThreadPoolExecutor(2) as pool:
            futures=[pool.submit(synth) for _ in range(2)]
            assert all(f.result()['ok'] for f in futures)
        control(); assert health()['pid']==h['pid']
        passed('normal-overlapping-takes-do-not-drop-or-restart')
        # One failed take must not restart a healthy model; a sustained failure
        # is distinguished from a malformed request and must recover.
        control(mode='synth_error')
        try: synth()
        except urllib.error.HTTPError as error: assert error.code==503
        assert health()['ok'] and health()['pid']==h['pid']
        control(); assert synth()['ok']; assert health()['consecutiveFailures']==0
        passed('one-model-error-recovers-without-restart')
        control(mode='synth_error')
        for _ in range(3):
            try: synth()
            except urllib.error.HTTPError as error: assert error.code==503
        assert health()['phase']=='failed'
        old=h['pid']; control()
        h=wait(lambda: h if (h:=health()).get('ok') and h['pid']!=old else None)
        passed('sustained-synthesis-failure-restarts')
        old=h['pid']; control(mode='health_hang')
        # Keep the fault latched until identity inspection sees a restart,
        # avoiding confusing a single recovered timeout with actual healing.
        wait(lambda:(s:=state())['listener'] and s['listener']!=old,45)
        control(); h=wait(lambda:h if (h:=health()).get('ok') else None)
        passed('unresponsive-http-restarts-after-confirmation')
        # HTTP stays responsive while real synthesis handler is wedged.
        control(mode='synth_hang')
        request=urllib.request.Request(env['TTS_SERVICE_URL']+'/synthesize',data=b'{"text":"test"}',headers={'Content-Type':'application/json'})
        try: urllib.request.build_opener(urllib.request.ProxyHandler({})).open(request,timeout=.2)
        except Exception: pass
        wait(lambda: health().get('phase')=='stalled',4)
        old=h['pid']; control()
        before=time.monotonic()
        # This is the sixth back-to-back fault. Production intentionally backs
        # off 120s after five starts; ordinary cold/crash cases still use 45s.
        h=wait(lambda: h if (h:=health()).get('ok') and h['pid']!=old else None,150)
        passed('health-alive-but-synthesis-stalled-recovered',pid=h['pid'],seconds=round(time.monotonic()-before,3))
        # Two-second negative cache must not mask recovery.
        sys_path=str(source/'services/agent-core')
        import sys
        sys.path.insert(0,sys_path)
        from agent_core.speech import SpeechClient
        client=SpeechClient(env['TTS_SERVICE_URL'])
        client._healthy=False; client._probed_monotonic=time.monotonic()-3
        assert client.is_healthy()
        audio=client.synthesize('test')
        with wave.open(audio['audioPath'],'rb') as wav: assert wav.getnframes()>0 and wav.getframerate()==32000
        passed('recovered-client-produces-valid-wav-not-just-port')
        # New avatar already present before old exits: no stale-watch kill.
        a2=subprocess.Popen([str(godot),'--headless','--path',str(repo/'apps/avatar-runtime'),'--script','res://actor.gd'],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=flags)
        actors.append(a2); time.sleep(.5); old_tts=health()['pid']; a.terminate(); a.wait(5)
        s=wait(lambda: s if (s:=state())['avatar']==a2.pid else None)
        watcher(s); wait(lambda:len(state()['watchers'])==1)
        assert health()['pid']==old_tts; passed('rapid-new-avatar-handover-keeps-tts')
        control(mode='crash'); wait(lambda:not health().get('ok'))
        a2.terminate(); a2.wait(5)
        wait(lambda:not (s:=state())['tts'] and not s['watchers'])
        passed('close-during-recovery-no-respawn')
        control() # clear the deliberate crash before the independent port test
        # A foreign socket is not ours to terminate, even if it occupies the
        # configured TTS port; recovery resumes only after that conflict clears.
        foreign=socket.socket(); foreign.setsockopt(socket.SOL_SOCKET,socket.SO_EXCLUSIVEADDRUSE,1)
        foreign.bind(('127.0.0.1',tts_port)); foreign.listen()
        a3=subprocess.Popen([str(godot),'--headless','--path',str(repo/'apps/avatar-runtime'),'--script','res://actor.gd'],
            env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=flags)
        actors.append(a3)
        raw=ps(". '"+str(repo/'scripts/startup-common.ps1')+"'; Initialize-AgentRuntime '"+str(repo)+"'; $a=Get-ProjectAvatar; @{avatar=$a.ProcessId;avatarTicks=$a.CreationDate.Ticks}|ConvertTo-Json -Compress")
        watcher(json.loads(raw))
        log=Path(env['LOCALAPPDATA'])/'AnimeAgent/logs/tts-watch.log'
        wait(lambda:'Foreign/unverified TTS port owner' in log.read_text(encoding='utf-8-sig'),20)
        assert foreign.fileno()!=-1
        foreign.close(); foreign=None
        wait(lambda:health().get('ok'))
        passed('foreign-owner-never-killed-and-cleared-conflict-recovers')
        a3.terminate(); a3.wait(5)
        wait(lambda:not (s:=state())['tts'] and not s['watchers'])
    finally:
        if foreign is not None: foreign.close()
        for a in actors:
            if a.poll() is None: a.terminate(); a.wait(5)
        try: wait(lambda:not (s:=state())['tts'] and not s['watchers'],25)
        finally:
            for proc in watchers:
                if proc.poll() is None: proc.terminate(); proc.wait(5)
            snapshot=state()
            for row in snapshot['tts']:
                ps("& '"+str(repo/'scripts/tts-driver.ps1')+f"' -Action stop -TargetId {row['ProcessId']} -TargetTicks {row['Ticks']}")
            protect()
            for row,handle in handles: kernel.CloseHandle(handle)
    print('TTS_WINDOWS_RECOVERY_PASS '+str(bench),flush=True)


if __name__=='__main__': main()
