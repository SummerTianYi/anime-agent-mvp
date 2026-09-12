"""Codex: compound faults against a marked disposable canonical-entry fixture.

Never point this harness at the live application. Synthetic synthesis replaces
only GPU computation; launchers, HTTP, Core, websocket and Godot are real.
"""
from concurrent.futures import ThreadPoolExecutor
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import subprocess
import time


def launch_entries(repo, env, output, count, protect):
    assert (repo / '.tts-test-fixture').is_file()
    assert Path(env['ANIME_AGENT_DATA_DIR']).resolve().is_relative_to(repo.parent)
    ps_exe = str(Path(os.environ['SystemRoot']) / 'System32/WindowsPowerShell/v1.0/powershell.exe')
    output.mkdir(exist_ok=True)

    def launch(index):
        protect()
        with (output / f'entry-{index}.log').open('w', encoding='utf-8') as log:
            result = subprocess.run(
                [ps_exe, '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command',
                 "& '" + str(repo / 'start-anime-agent.cmd') + "'; exit $LASTEXITCODE"],
                env=env, stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                timeout=240, creationflags=subprocess.CREATE_NO_WINDOW)
        protect()
        return result.returncode

    with ThreadPoolExecutor(max_workers=count) as pool:
        codes = list(pool.map(launch, range(count)))
    assert codes == [0] * count, ('canonical launch failures', codes, str(output))
    return codes


def run_session_stress(*, repo, env, output, ps, inspect, tts_state,
                       wait, protect, voice_ready, scenario):
    """Returns durable, per-case evidence; fails immediately on live-process loss."""
    assert (repo / '.tts-test-fixture').is_file()
    tts_root = Path(env['TTS_WORKSPACE']).resolve()
    assert tts_root.parent == repo.parent and (tts_root / '.tts-test-fixture').is_file()
    assert env['LLM_PROVIDER'] == 'mock' and env['ANIME_AGENT_TOOLS'] == '0'
    assert env['ANIME_AGENT_WAKE_WORD'] == '0' and env['ANIME_AGENT_MCP_SERVERS'] == ''
    port = int(env['AGENT_CORE_PORT'])
    assert port not in (8765, 8770)
    cases = []
    report = output / 'compound-faults.json'

    def action(name):
        protect()
        return ps("& '" + str(repo / 'scripts/startup-driver.ps1') + "' -Action " + name)

    def tts_action(name, row):
        protect()
        return ps("& '" + str(repo / 'scripts/tts-driver.ps1') +
                  f"' -Action {name} -TargetId {row['ProcessId']} -TargetTicks {row['Ticks']}")

    def stable():
        state = inspect()
        ts = tts_state()
        return state if (state['avatar'] and state['visible'] and state['responding']
                         and len(state['watchers']) == 1 and ts['listener']
                         and len(ts['watchers']) == 1 and voice_ready()) else False

    def playback(label):
        # A fresh private Mock reply after EACH fault must reach AudioStreamPlayer.
        from websockets.sync.client import connect
        path = output / 'tts-playback.jsonl'
        old = len(path.read_text().splitlines()) if path.exists() else 0
        with connect(f'ws://127.0.0.1:{port}/ws', proxy=None) as ws:
            def until(kind):
                for _ in range(80):
                    value = json.loads(ws.recv(timeout=15))
                    if value.get('type') == kind:
                        return value
                raise AssertionError('missing private websocket event: ' + kind)
            ws.send(json.dumps({'type': 'client.hello', 'role': 'ui'}))
            until('client.ready')
            ws.send(json.dumps({'type': 'session.new'}))
            session = until('session.switched')['conversationId']
            ws.send(json.dumps({'type': 'chat.message', 'messageId': label,
                                'text': '你好', 'conversationId': session}))
            assert until('chat.response')['text']

        def completed():
            if not path.exists():
                return False
            rows = [json.loads(line) for line in path.read_text().splitlines()[old:]]
            starts = {row['utterance'] for row in rows
                      if row['event'] == 'started' and row['playing']}
            return any(row['event'] == 'finished' and row['utterance'] in starts for row in rows)
        wait(completed, 35)

    def record(name, start, **extra):
        protect()
        cases.append(dict(case=name, result='PASS', seconds=round(time.monotonic()-start, 3), **extra))
        report.write_text(json.dumps(cases, indent=2), encoding='utf-8')
        print('COMPOUND_PASS ' + json.dumps(cases[-1]), flush=True)

    try:
        state = stable()
        assert state
        ts = tts_state()
        avatar, core, voice = state['avatar'], state['listener'], ts['listener']

        start = time.monotonic()
        launch_entries(repo, env, output / 'concurrent-live', 6, protect)
        assert wait(stable, 35)['avatar'] == avatar
        assert inspect()['listener'] == core and tts_state()['listener'] == voice
        playback('concurrent-live')
        record('six-concurrent-canonical-entries', start, sameAvatarCoreTts=True, playback=True)

        # Fail the supervisor AND its service, not one fault followed by a repair.
        start = time.monotonic()
        ts = tts_state()
        old_watch = ts['watchers'][0]
        old_voice = next(row for row in ts['tts'] if row['ProcessId'] == ts['listener'])
        tts_action('suspend-watch', old_watch)
        tts_action('stop', old_voice)
        wait(lambda: tts_state()['listener'] not in (0, old_voice['ProcessId']), 125)
        assert wait(stable, 45)['avatar'] == avatar
        assert inspect()['listener'] == core
        assert tts_state()['watchers'][0]['ProcessId'] != old_watch['ProcessId']
        playback('frozen-watch-and-sidecar-death')
        record('frozen-tts-supervisor-plus-sidecar-death', start, sameAvatarCore=True, playback=True)

        start = time.monotonic()
        ts = tts_state()
        old_voice = next(row for row in ts['tts'] if row['ProcessId'] == ts['listener'])
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(action, 'crash'), pool.submit(tts_action, 'stop', old_voice)]
            for future in futures:
                future.result()
        wait(lambda: inspect()['listener'] not in (0, core), 100)
        assert wait(stable, 100)['avatar'] == avatar
        assert tts_state()['listener'] != old_voice['ProcessId']
        playback('core-and-sidecar-death')
        record('simultaneous-core-and-tts-death', start, sameAvatar=True, playback=True)

        # Losing the outer supervisor is a different failure boundary: the
        # user's same command must reinstall it without restarting healthy apps.
        start = time.monotonic()
        before, before_voice = inspect(), tts_state()['listener']
        action('watch-crash')
        assert not inspect()['watchers']
        launch_entries(repo, env, output / 'outer-watch-repair', 3, protect)
        after = wait(stable, 45)
        assert after['avatar'] == avatar and after['listener'] == before['listener']
        assert tts_state()['listener'] == before_voice
        assert after['watchers'][0] not in before['watchers']
        playback('outer-watch-reinstalled')
        record('outer-watch-death-then-three-canonical-entries', start, sameAvatarCoreTts=True,
               playback=True, recovery='explicit same-command retry, NOT automatic')

        if scenario == 'repeated':
            start = time.monotonic()
            for iteration in range(3):
                ts = tts_state()
                old_voice = next(row for row in ts['tts'] if row['ProcessId'] == ts['listener'])
                tts_action('stop', old_voice)
                wait(lambda: tts_state()['listener'] not in (0, old_voice['ProcessId']), 150)
                wait(voice_ready, 45)
                playback('repeated-sidecar-crash-' + str(iteration))
            assert inspect()['avatar'] == avatar
            record('three-more-sidecar-crashes-with-playback-after-each', start, playback=True)
        return cases
    except BaseException as exc:
        cases.append(dict(case='compound-suite', result='FAIL', error=str(exc)))
        report.write_text(json.dumps(cases, indent=2), encoding='utf-8')
        raise


def run_close_race(*, repo, env, output, ps, inspect, tts_state,
                   wait, protect, voice_ready, close_owned):
    """Force an old watcher to wake only AFTER a new real Godot exists."""
    assert (repo / '.tts-test-fixture').is_file()
    assert Path(env['TTS_WORKSPACE']).resolve().parent == repo.parent
    before, ts = inspect(), tts_state()
    old = ts['watchers'][0]
    start = time.monotonic()
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD,wintypes.BOOL,wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.GetExitCodeProcess.argtypes = [wintypes.HANDLE,ctypes.POINTER(wintypes.DWORD)]
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel.OpenProcess(0x1000,False,before['avatar'])
    assert handle
    suspended = False
    report = output / 'close-race.json'

    def watcher_action(name):
        protect()
        ps("& '"+str(repo/'scripts/tts-driver.ps1')+
           f"' -Action {name} -TargetId {old['ProcessId']} -TargetTicks {old['Ticks']}")

    def exited():
        code = wintypes.DWORD()
        assert kernel.GetExitCodeProcess(handle,ctypes.byref(code))
        return code.value != 259

    try:
        watcher_action('suspend-watch'); suspended = True
        close_owned(before)
        wait(exited,20)
        # Don't wait for Core/TTS cleanup. Launch immediately after the OS
        # confirms Godot exited, while the obsolete TTS watcher is still frozen.
        with ThreadPoolExecutor(max_workers=1) as pool:
            batch = pool.submit(launch_entries,repo,env,output/'close-race-reopen',3,protect)
            try:
                def new_avatar():
                    protect()
                    current = json.loads(ps("& '"+str(repo/'scripts/startup-driver.ps1')+"' -Action inspect-avatar"))
                    return current if current['avatar'] not in (None,0,before['avatar']) else False
                current = wait(new_avatar,70)
                # Prove old cleanup runs after the replacement exists.
                watcher_action('resume-watch'); suspended = False
            finally:
                if suspended:
                    watcher_action('resume-watch'); suspended = False
            batch.result()
        wait(voice_ready,80)
        def transferred():
            now=tts_state()
            return len(now['watchers'])==1 and now['watchers'][0]['ProcessId']!=old['ProcessId']
        wait(transferred,45)
        after=inspect()
        assert after['avatar']==current['avatar'] and after['visible'] and after['responding']
        assert len(after['watchers'])==1
        protect()
        result=dict(result='PASS',seconds=round(time.monotonic()-start,3),
                    oldAvatar=before['avatar'],newAvatar=after['avatar'],
                    oldTtsWatcher=old['ProcessId'],concurrentReopens=3,
                    lateOldSupervisorResumedAfterNewAvatar=True)
        report.write_text(json.dumps(result,indent=2),encoding='utf-8')
        print('CLOSE_RACE_PASS '+json.dumps(result),flush=True)
        return result
    except BaseException as exc:
        report.write_text(json.dumps(dict(result='FAIL',error=str(exc)),indent=2),encoding='utf-8')
        raise
    finally:
        if suspended:
            watcher_action('resume-watch')
        kernel.CloseHandle(handle)
