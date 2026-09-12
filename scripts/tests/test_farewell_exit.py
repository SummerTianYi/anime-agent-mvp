"""Codex: isolated original-CMD/WM_CLOSE exit test; NEVER operates existing windows.
Run with --repo <already-prepared-isolated-copy> --source <real-repo>.
Only this harness's isolated repo may contain .farewell-test-fixture.
"""
import argparse
import ctypes
from ctypes import wintypes as w
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import time
import venv
import urllib.request


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo', type=Path, required=True)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--tts-fixture-sidecar', type=Path, help='Test canonical TTS lifecycle with real HTTP + synthetic audio, never production voice')
    p.add_argument('--tts-real-copy', type=Path, help='Explicit disposable complete real-voice workspace; never the production sidecar')
    p.add_argument('--voice-faults', action='store_true', help='Kill only isolated TTS/watch processes, then repeat real Core/Godot exchange')
    p.add_argument('--session-stress', action='store_true', help='Compound faults and concurrent original-CMD launches; synthetic isolated voice only')
    p.add_argument('--close-race', action='store_true', help='Freeze obsolete TTS supervisor across real WM_CLOSE and three concurrent reopen commands')
    p.add_argument('--audible', action='store_true', help='Unmute only isolated Godot and inspect its audio mix; never microphone capture')
    p.add_argument('--scenarios', nargs='+', default=['idle','listen','think','pirouette','speaking','repeated','paused','zero_scale','missing','corrupt'])
    a = p.parse_args()
    assert not (a.tts_fixture_sidecar and a.tts_real_copy)
    voice_test = bool(a.tts_fixture_sidecar or a.tts_real_copy)
    assert not a.voice_faults or voice_test
    assert not a.audible or a.tts_real_copy
    assert not a.session_stress or a.tts_fixture_sidecar
    assert not a.close_race or a.tts_fixture_sidecar
    repo, source = a.repo.resolve(), a.source.resolve()
    if a.session_stress or a.close_race:
        spec = importlib.util.spec_from_file_location('tts_session_stress', source/'scripts/tests/tts-session-stress.py')
        stress = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(stress)
    assert repo != source and repo.name == 'fixture'
    assert (repo / '.farewell-test-fixture').is_file()
    # start-mvp's optional voice-chain hooks must be unreachable, even if real
    # TTS is running. Do not merely disable an env flag those hooks don't check.
    assert not (repo.parent / 'tianyi-tts').exists()
    evidence = repo.parent / ('e2e-' + time.strftime('%H%M%S'))
    evidence.mkdir()
    print('EVIDENCE=' + str(evidence), flush=True)
    ps_exe = str(Path(os.environ['SystemRoot']) / 'System32/WindowsPowerShell/v1.0/powershell.exe')
    env = {k:v for k,v in os.environ.items() if not k.startswith(('GLM_', 'DEEPSEEK_', 'STEPFUN_', 'AGENT_CORE_', 'ANIME_AGENT_', 'FAREWELL_', 'LLM_', 'TTS_'))}
    env.pop('PSModulePath', None)
    env['PYTHONDONTWRITEBYTECODE']='1'
    for key in ('APPDATA','LOCALAPPDATA','TEMP','TMP'):
        path = repo.parent / key
        path.mkdir(exist_ok=True)
        env[key] = str(path)
    env.update(LLM_PROVIDER='mock', ANIME_AGENT_TTS='0', ANIME_AGENT_WAKE_WORD='0',
               ANIME_AGENT_MCP_SERVERS='', ANIME_AGENT_TOOLS='0', ANIME_AGENT_PROACTIVE='0',
               ANIME_AGENT_DATA_DIR=str(repo.parent/'data'), AGENT_CORE_HOST='127.0.0.1',
               PYTHONPATH=str(source/'services/agent-core/.venv/Lib/site-packages'), PYTHONIOENCODING='utf-8')
    with socket.socket() as reservation:
        reservation.bind(('127.0.0.1',0))
        port = reservation.getsockname()[1]
    assert port != 8765
    env['AGENT_CORE_PORT'] = str(port)
    env['AGENT_CORE_WS_URL'] = f'ws://127.0.0.1:{port}/ws'
    env['TTS_SERVICE_URL'] = 'http://127.0.0.1:1'
    if a.tts_fixture_sidecar:
        tts=repo.parent/'tianyi-tts'
        (tts/'scripts').mkdir(parents=True)
        (tts/'.tts-test-fixture').write_text('Codex synthetic canonical-entry test')
        (repo/'.tts-test-fixture').write_text('Codex synthetic canonical-entry test')
        venv.EnvBuilder(with_pip=False).create(tts/'venv')
        shutil.copy2(source/'scripts/tests/tts-fixture-server.py',tts/'scripts/tts_server.py')
        shutil.copy2(a.tts_fixture_sidecar/'scripts/tts_server.py',tts/'scripts/tts_implementation.py')
        shutil.copy2(a.tts_fixture_sidecar/'scripts/service_health.py',tts/'scripts/service_health.py')
        for name in ('tts-lifecycle.ps1','watch-tts-session.ps1'):
            shutil.copy2(source/'scripts'/name,repo/'scripts'/name)
        shutil.copy2(source/'scripts/tests/tts-driver.ps1',repo/'scripts/tts-driver.ps1')
        with socket.socket() as reservation:
            reservation.bind(('127.0.0.1',0)); tts_port=reservation.getsockname()[1]
        assert tts_port not in (8765,8770,port)
        env.update(ANIME_AGENT_TTS='1',ANIME_AGENT_TTS_NARRATE='0',TTS_WORKSPACE=str(tts),TTS_SERVICE_URL=f'http://127.0.0.1:{tts_port}')
    elif a.tts_real_copy:
        tts=a.tts_real_copy.resolve()
        assert tts != (source.parent/'tianyi-tts').resolve()
        assert (tts/'.real-voice-test-copy').is_file()
        assert (tts/'venv/Scripts/python.exe').is_file()
        (repo/'.tts-test-fixture').write_text('Codex real voice isolated session')
        for name in ('tts-lifecycle.ps1','watch-tts-session.ps1'):
            shutil.copy2(source/'scripts'/name,repo/'scripts'/name)
        shutil.copy2(source/'scripts/tests/tts-driver.ps1',repo/'scripts/tts-driver.ps1')
        with socket.socket() as reservation:
            reservation.bind(('127.0.0.1',0)); tts_port=reservation.getsockname()[1]
        assert tts_port not in (8765,8770,port)
        env.pop('PYTHONPATH',None) # independent 3.12 Core and 3.10 torch environments
        env.update(ANIME_AGENT_TTS='1',ANIME_AGENT_TTS_NARRATE='0',TTS_WORKSPACE=str(tts),TTS_SERVICE_URL=f'http://127.0.0.1:{tts_port}',
                   HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',OMP_NUM_THREADS='2',MKL_NUM_THREADS='2')
    env['TTS_AUDIBLE_TEST']='1' if a.audible else '0'
    def ps(command, timeout=30):
        out = subprocess.run([ps_exe,'-NoProfile','-ExecutionPolicy','Bypass','-Command',command], env=env,
                             capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=timeout,
                             creationflags=subprocess.CREATE_NO_WINDOW)
        assert out.returncode == 0, out.stdout + out.stderr
        return out.stdout.strip()
    # Read-only inventory, never print credential-bearing process command lines.
    existing = json.loads(ps("Get-CimInstance Win32_Process | Where-Object { $_.Name -like 'Godot*' -or $_.CommandLine -match 'agent_core.main|tts_server.py|core_watchdog.ps1|watch-tts-session.ps1' } | Select-Object ProcessId,Name,@{n='Ticks';e={$_.CreationDate.Ticks}} | ConvertTo-Json -Compress"))
    if isinstance(existing, dict): existing = [existing]
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    user = ctypes.WinDLL('user32', use_last_error=True)
    kernel.OpenProcess.argtypes = [w.DWORD,w.BOOL,w.DWORD]; kernel.OpenProcess.restype = w.HANDLE
    kernel.GetExitCodeProcess.argtypes = [w.HANDLE,ctypes.POINTER(w.DWORD)]
    kernel.CloseHandle.argtypes = [w.HANDLE]
    user.GetWindowThreadProcessId.argtypes = [w.HWND,ctypes.POINTER(w.DWORD)]
    user.PostMessageW.argtypes = [w.HWND,w.UINT,w.WPARAM,w.LPARAM]
    protected = []
    for row in existing:
        # The inventory command itself is transient and is not a protected service.
        h = kernel.OpenProcess(0x1000, False, row['ProcessId'])
        code = w.DWORD()
        if h and kernel.GetExitCodeProcess(h,ctypes.byref(code)) and code.value == 259:
            protected.append((row,h))
        elif h: kernel.CloseHandle(h)
    (evidence/'protected.json').write_text(json.dumps([row for row,_ in protected],indent=2),encoding='utf-8')
    def protect():
        for row,h in protected:
            code = w.DWORD()
            assert kernel.GetExitCodeProcess(h,ctypes.byref(code)) and code.value == 259, ('pre-existing process changed; stop testing',row)
    def inspect():
        protect()
        return json.loads(ps("& '"+str(repo/'scripts/startup-driver.ps1')+"' -Action inspect"))
    def close_owned(state):
        protect()
        assert state['avatar'] not in [row['ProcessId'] for row,_ in protected]
        actual = w.DWORD()
        user.GetWindowThreadProcessId(state['window'],ctypes.byref(actual))
        # state was just obtained by the project-path ownership verifier. Do
        # not do slow CIM/port scans between a burst of three WM_CLOSE events.
        assert actual.value == state['avatar']

        sent = time.monotonic()
        assert user.PostMessageW(state['window'], 0x0010, 0, 0) # WM_CLOSE, never focus/keyboard.
        return sent
    def wait(fn, timeout=30):
        end = time.monotonic()+timeout
        while time.monotonic()<end:
            value = fn()
            if value: return value
            time.sleep(.15)
        raise AssertionError('bounded wait timed out')
    def tts_state():
        # A new redirector/worker can bind between the process and socket
        # snapshots. Production safely defers; the observer retries only this
        # bounded identity race, never assumes the port belongs to us.
        for attempt in range(3):
            try: return json.loads(ps("& '"+str(repo/'scripts/tts-driver.ps1')+"'"))
            except AssertionError as exc:
                if 'Foreign/unverified TTS port owner' not in str(exc) or attempt==2: raise
                time.sleep(.3)
    def clean():
        state = inspect()
        ordinary = not state['avatar'] and not state['cores'] and not state['watchers']
        if ordinary and voice_test:
            ts=tts_state(); return not ts['tts'] and not ts['watchers']
        return ordinary
    def voice_ready():
        try:
            opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
            with opener.open(f'http://127.0.0.1:{port}/health',timeout=4) as r:
                return json.load(r)['tts']['available']
        except OSError: return False
    clip = repo/'apps/avatar-runtime/assets/motions/farewell_reference_v1.tres'
    approved = clip.read_bytes()
    assert hashlib.sha256(approved).hexdigest() == 'aa9684cdf8e8927a601bbed3c47bf6abc38fc7dc4b85b8432f0239889542bea7'
    core = repo/'services/agent-core'
    if not core.exists():
        shutil.copytree(source/'services/agent-core/agent_core',core/'agent_core',ignore=shutil.ignore_patterns('__pycache__'))
        venv.EnvBuilder(with_pip=False).create(core/'.venv')
    if a.tts_real_copy:
        (core/'.venv/Lib/site-packages/source-dependencies.pth').write_text(str(source/'services/agent-core/.venv/Lib/site-packages')+'\n')
    godot_dir = Path(env['LOCALAPPDATA'])/'Godot'
    godot_dir.mkdir(exist_ok=True)
    binary = source.parent/'tools/godot-4.7.2/Godot_v4.7.2-stable_win64.exe'
    if not (godot_dir/binary.name).exists(): shutil.copy2(binary,godot_dir/binary.name)
    results = []
    try:
        for scenario in a.scenarios:
            protect()
            assert clean(), 'only the isolated session must start empty'
            output = evidence/scenario; output.mkdir()
            env['FAREWELL_SCENARIO'] = scenario
            env['FAREWELL_EVIDENCE'] = str(output)
            if scenario == 'missing': clip.unlink()
            elif scenario == 'corrupt': clip.write_bytes(b'not the approved animation')
            else: clip.write_bytes(approved)
            with (output/'entry.log').open('w',encoding='utf-8') as log:
                command = "& '"+str(repo/'start-anime-agent.cmd')+"'; exit $LASTEXITCODE"
                result = subprocess.run([ps_exe,'-NoProfile','-ExecutionPolicy','Bypass','-Command',command],env=env,
                                        stdin=subprocess.DEVNULL,stdout=log,stderr=log,timeout=200,
                                        creationflags=subprocess.CREATE_NO_WINDOW)
            assert result.returncode == 0, (output/'entry.log').read_text(encoding='utf-8',errors='replace')
            state = inspect()
            assert state['visible'] and state['responding'] and state['avatar'] and state['watchers']
            voice_metrics={}
            if voice_test:
                wait(voice_ready,35)
                ts=tts_state(); assert ts['listener'] and len(ts['watchers'])==1
                assert 'Voice ready: real model warmup completed' in (output/'entry.log').read_text(errors='replace')
                if a.tts_real_copy:
                    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
                    with opener.open(env['TTS_SERVICE_URL']+'/health',timeout=3) as response:
                        vh=json.load(response)
                    assert vh['device']=='cuda' and vh['selfCheck']['enabled'] and vh['selfCheck']['threshold']==.9
                    voice_metrics['device']=vh['device']
                    voice_metrics['selfCheckThreshold']=vh['selfCheck']['threshold']
                if a.voice_faults:
                    original_core=state['cores']
                    before_tts=ts['listener']
                    old_watch=ts['watchers'][0]
                    ps("& '"+str(repo/'scripts/tts-driver.ps1')+f"' -Action stop-watch -TargetId {old_watch['ProcessId']} -TargetTicks {old_watch['Ticks']}")
                    def supervisor_repaired():
                        current=tts_state()
                        return len(current['watchers'])==1 and current['watchers'][0]['ProcessId']!=old_watch['ProcessId']
                    wait(supervisor_repaired,45)
                    assert tts_state()['listener']==before_tts, 'watcher repair restarted healthy TTS'
                    assert inspect()['cores']==original_core, 'TTS watcher fault changed Core'
                    print('VOICE_FAULT_PASS supervisor-kill-recovered-without-Core-or-TTS-restart',flush=True)
                    voice_metrics['watcherDeathRecovered']=True
                    if scenario=='repeated':
                        old_watch=tts_state()['watchers'][0]
                        ps("& '"+str(repo/'scripts/tts-driver.ps1')+f"' -Action suspend-watch -TargetId {old_watch['ProcessId']} -TargetTicks {old_watch['Ticks']}")
                        wait(supervisor_repaired,80)
                        assert tts_state()['listener']==before_tts, 'frozen watcher repair restarted healthy voice'
                        assert inspect()['cores']==original_core
                        print('VOICE_FAULT_PASS frozen-supervisor-heartbeat-recovered',flush=True)
                        voice_metrics['frozenWatcherRecovered']=True
                    ts=tts_state(); old=next(row for row in ts['tts'] if row['ProcessId']==ts['listener'])
                    began=time.monotonic()
                    ps("& '"+str(repo/'scripts/tts-driver.ps1')+f"' -Action stop -TargetId {old['ProcessId']} -TargetTicks {old['Ticks']}")
                    wait(lambda:tts_state()['listener'] not in (0,old['ProcessId']),60)
                    wait(voice_ready,180)
                    assert inspect()['cores']==original_core, 'sidecar fault changed Core'
                    print('VOICE_FAULT_PASS sidecar-kill-ready-again seconds='+str(round(time.monotonic()-began,3)),flush=True)
                    voice_metrics['sidecarRecoverySeconds']=round(time.monotonic()-began,3)
                if a.session_stress:
                    voice_metrics['compoundFaults'] = stress.run_session_stress(
                        repo=repo, env=env, output=output, ps=ps, inspect=inspect,
                        tts_state=tts_state, wait=wait, protect=protect,
                        voice_ready=voice_ready, scenario=scenario)
                    state = inspect()  # Core may recover; the avatar must remain the same.
                if a.close_race:
                    voice_metrics['closeRace'] = stress.run_close_race(
                        repo=repo, env=env, output=output, ps=ps, inspect=inspect,
                        tts_state=tts_state, wait=wait, protect=protect,
                        voice_ready=voice_ready, close_owned=close_owned)
                    state = inspect()
                # One synthetic exchange through the real Core and real Godot.
                # No paid provider, microphone, production DB or audible output.
                from websockets.sync.client import connect
                with connect(f'ws://127.0.0.1:{port}/ws',proxy=None) as ws:
                    def until(kind):
                        for _ in range(60):
                            value=json.loads(ws.recv(timeout=15))
                            if value.get('type')==kind: return value
                        raise AssertionError('missing '+kind)
                    ws.send(json.dumps({'type':'client.hello','role':'ui'})); until('client.ready')
                    ws.send(json.dumps({'type':'session.new'})); session=until('session.switched')['conversationId']
                    ws.send(json.dumps({'type':'chat.message','messageId':'tts-isolated','text':'你好','conversationId':session}))
                    response=until('chat.response')
                    assert response['text'] and any('\u4e00'<=ch<='\u9fff' for ch in response['text'])
                    # Verify the actual muted AudioStreamPlayer, not just a port.
                    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
                    def produced():
                        with opener.open(env['TTS_SERVICE_URL']+'/health',timeout=3) as r:
                            return json.load(r)['synthCount']>0
                    wait(produced,110 if a.tts_real_copy else 20)
                    def played():
                        path=output/'tts-playback.jsonl'
                        if not path.exists(): return False
                        rows=[json.loads(line) for line in path.read_text().splitlines()]
                        starts={row['utterance'] for row in rows if row['event']=='started' and row['playing']}
                        completed=any(row['event']=='finished' and row['utterance'] in starts for row in rows)
                        if a.audible:
                            completed=completed and any(row['event']=='audio-mix' and row['peak']>.001 and not row['muted'] and row['driver']!='Dummy' for row in rows)
                        return completed
                    wait(played,110 if a.tts_real_copy else 20)
                    ws.send(json.dumps({'type':'session.delete','conversationId':session}))
                    until('session.deleted')
            logs = list((Path(env['LOCALAPPDATA'])/'AnimeAgent/logs').glob('avatar-*.stdout.log'))
            log_path = max(logs,key=lambda x:x.stat().st_mtime)
            wait(lambda:'FAREWELL_PROBE_READY' in log_path.read_text(encoding='utf-8',errors='replace'))
            start = close_owned(state)
            if scenario == 'repeated':
                # Three Windows close requests without activation or broad targeting.
                for _ in range(2): close_owned(state)
            wait(clean,35)
            duration = time.monotonic()-start
            text = log_path.read_text(encoding='utf-8',errors='replace')
            (output/'avatar.log').write_text(text,encoding='utf-8')
            expected = 'farewell_unavailable' if scenario in ('missing','corrupt') else 'farewell_deadline' if scenario in ('paused','zero_scale') else 'animation_finished'
            assert text.count('GODOT_FAREWELL_EXIT ' + expected) == 1, text
            assert text.count('GODOT_FAREWELL_STARTED') == (0 if scenario in ('missing','corrupt') else 1), text
            data = [json.loads(line) for line in (output/'frames.jsonl').read_text().splitlines()] if (output/'frames.jsonl').exists() else []
            if expected == 'animation_finished':
                assert len(data) >= 20 and max(x['seconds'] for x in data) >= 4.0
                wave = [x for x in data if 1.0 <= x['seconds'] <= 3.16]
                assert wave and all(abs(x['eyes']-1)<1e-5 and abs(x['smile']-.65)<1e-5 for x in wave)
                assert all(not x['authored_playing'] for x in data), 'two animation writers'
                assert 4.0 <= duration < 35
            elif expected == 'farewell_deadline':
                assert duration >= 8 and duration < 35
            errors = list((Path(env['LOCALAPPDATA'])/'AnimeAgent/logs').glob('avatar-*.stderr.log'))
            assert all('SCRIPT ERROR' not in f.read_text(encoding='utf-8',errors='replace') for f in errors)
            protect()
            row = {'scenario':scenario,'result':'PASS','elapsed_with_cleanup':round(duration,3),'frames':len(data),'reason':expected,'isolated_avatar_pid':state['avatar']}
            if voice_test:
                row['tts']='canonical entry, ready, Core exchange, Godot playback+finished, scoped cleanup PASS'
                row['voiceSource']='real GPT-SoVITS' if a.tts_real_copy else 'synthetic test WAV'
                row['audibleMixChecked']=a.audible
                row['faultsChecked']=a.voice_faults or a.session_stress or a.close_race
                row['faultModes']={'individual':a.voice_faults,'compound':a.session_stress,'closeRace':a.close_race}
                row['voiceMetrics']=voice_metrics
            results.append(row)
            (evidence/'results.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
            print(json.dumps(row),flush=True)
    finally:
        clip.write_bytes(approved) # restore only the fixture, never source assets
        state = inspect()
        if state['avatar']:
            close_owned(state)
            wait(clean,35)
        assert clean()
        protect()
        for _,h in protected: kernel.CloseHandle(h)
    print('FAREWELL_WINDOWS_E2E_PASS '+str(evidence),flush=True)


if __name__ == '__main__':
    main()
