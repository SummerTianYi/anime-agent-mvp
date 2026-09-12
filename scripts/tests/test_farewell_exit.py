"""Codex: isolated original-CMD/WM_CLOSE exit test; NEVER operates existing windows.
Run with --repo <already-prepared-isolated-copy> --source <real-repo>.
Only this harness's isolated repo may contain .farewell-test-fixture.
"""
import argparse
import ctypes
from ctypes import wintypes as w
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import time
import venv


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo', type=Path, required=True)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--scenarios', nargs='+', default=['idle','listen','think','pirouette','speaking','repeated','paused','zero_scale','missing','corrupt'])
    a = p.parse_args()
    repo, source = a.repo.resolve(), a.source.resolve()
    assert repo != source and repo.name == 'fixture'
    assert (repo / '.farewell-test-fixture').is_file()
    # start-mvp's optional voice-chain hooks must be unreachable, even if real
    # TTS is running. Do not merely disable an env flag those hooks don't check.
    assert not (repo.parent / 'tianyi-tts').exists()
    evidence = repo.parent / ('e2e-' + time.strftime('%H%M%S'))
    evidence.mkdir()
    print('EVIDENCE=' + str(evidence), flush=True)
    ps_exe = str(Path(os.environ['SystemRoot']) / 'System32/WindowsPowerShell/v1.0/powershell.exe')
    env = {k:v for k,v in os.environ.items() if not k.startswith(('GLM_', 'DEEPSEEK_', 'STEPFUN_', 'AGENT_CORE_', 'ANIME_AGENT_', 'FAREWELL_', 'LLM_'))}
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
    def ps(command, timeout=30):
        out = subprocess.run([ps_exe,'-NoProfile','-ExecutionPolicy','Bypass','-Command',command], env=env,
                             capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=timeout,
                             creationflags=subprocess.CREATE_NO_WINDOW)
        assert out.returncode == 0, out.stdout + out.stderr
        return out.stdout.strip()
    # Read-only inventory, never print credential-bearing process command lines.
    existing = json.loads(ps("Get-CimInstance Win32_Process | Where-Object { $_.Name -like 'Godot*' -or $_.CommandLine -match 'agent_core.main|core_watchdog.ps1|watch-tts-session.ps1' } | Select-Object ProcessId,Name,@{n='Ticks';e={$_.CreationDate.Ticks}} | ConvertTo-Json -Compress"))
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
    def clean():
        state = inspect()
        return not state['avatar'] and not state['cores'] and not state['watchers']
    clip = repo/'apps/avatar-runtime/assets/motions/farewell_reference_v1.tres'
    approved = clip.read_bytes()
    assert hashlib.sha256(approved).hexdigest() == 'aa9684cdf8e8927a601bbed3c47bf6abc38fc7dc4b85b8432f0239889542bea7'
    core = repo/'services/agent-core'
    if not core.exists():
        shutil.copytree(source/'services/agent-core/agent_core',core/'agent_core',ignore=shutil.ignore_patterns('__pycache__'))
        venv.EnvBuilder(with_pip=False).create(core/'.venv')
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
