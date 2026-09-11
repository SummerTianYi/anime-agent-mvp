"""Codex: real Windows processes/windows, original .cmd entry in a disposable copy.
No real Provider, mic, TTS, MCP, production DB or model edits. Requires local assets.
"""
import concurrent.futures
import argparse
import ctypes
from ctypes import wintypes
import json
import hashlib
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
import venv

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--startup-crash-only', action='store_true')
    parser.add_argument('--stress-round', type=int, choices=(1, 2))
    options = parser.parse_args()
    REPO = Path(__file__).resolve().parents[2]
    PS = str(Path(os.environ["SystemRoot"]) / "System32/WindowsPowerShell/v1.0/powershell.exe")
    report = []
    bench = Path(tempfile.mkdtemp(prefix="tianyi startup "))
    log = bench / "evidence"
    log.mkdir()
    env = os.environ.copy()
    for key in list(env):
        if key.startswith(("GLM_", "DEEPSEEK_", "AGENT_CORE_", "ANIME_AGENT_")):
            env.pop(key)
    env.update(LLM_PROVIDER="mock", ANIME_AGENT_TTS="1", ANIME_AGENT_WAKE_WORD="0",
               ANIME_AGENT_MCP_SERVERS="", ANIME_AGENT_TOOLS="0",
               ANIME_AGENT_DATA_DIR=str(bench / "data"),
               PYTHONPATH=str(REPO / "services/agent-core/.venv/Lib/site-packages"),
               APPDATA=str(bench / "roaming"), LOCALAPPDATA=str(bench / "local"))
    for name in ("APPDATA", "LOCALAPPDATA"):
        Path(env[name]).mkdir()
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    env["AGENT_CORE_PORT"] = str(port)
    env["AGENT_CORE_HOST"] = "127.0.0.1"
    # Reserve a non-listening local socket: optional TTS is provably absent,
    # even if the owner's real sidecar is brought online during a test.
    absent_tts = socket.socket()
    absent_tts.bind(('127.0.0.1', 0))
    env['TTS_SERVICE_URL'] = f'http://127.0.0.1:{absent_tts.getsockname()[1]}'
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    foreign = None
    lock_holder = None
    bystander = None


    def ps(command, timeout=45):
        return subprocess.run([PS, "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command],
                              env=env, stdin=subprocess.DEVNULL, capture_output=True,
                              text=True, encoding="utf-8", errors="replace", timeout=timeout)


    def action(name="inspect"):
        r = ps("& '" + str(bench / "scripts/startup-driver.ps1") + "' -Action " + name)
        if r.returncode:
            raise AssertionError(r.stdout + r.stderr)
        return json.loads(r.stdout.strip()) if name == "inspect" else None


    def launch(name, args=""):
        start = time.monotonic()
        command = "& '" + str(bench / "start-anime-agent.cmd") + "' " + args + "; exit $LASTEXITCODE"
        # Windows detached children may inherit pipe handles even after the parent
        # exits. File-backed capture measures the entry process, not pipe EOF.
        path = log / (name + ".log")
        with path.open('w', encoding='utf-8') as output:
            r = subprocess.run([PS, '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', command],
                               env=env, stdin=subprocess.DEVNULL, stdout=output, stderr=output, timeout=240)
        r.stdout = path.read_text(encoding='utf-8', errors='replace')
        r.stderr = ''
        r.finished_at = time.monotonic()
        print(f"{name}: exit={r.returncode} seconds={time.monotonic()-start:.2f}", flush=True)
        return r


    def passed(name, **facts):
        row = dict(case=name, result="PASS", **facts)
        report.append(row)
        (log / "results.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(row), flush=True)


    def health():
        try:
            with opener.open(f"http://127.0.0.1:{port}/health/live", timeout=1) as r:
                return json.load(r)
        except Exception:
            return None


    def wait_for(fn, seconds=45):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            value = fn()
            if value:
                return value
            time.sleep(.4)
        raise AssertionError("condition timed out")


    def exited():
        state = action()
        return not state["cores"] and not state["avatar"] and not state["watchers"]


    def alive(pid):
        k = ctypes.WinDLL("kernel32", use_last_error=True)
        k.OpenProcess.restype = ctypes.c_void_p
        k.CloseHandle.argtypes = [ctypes.c_void_p]
        handle = k.OpenProcess(0x1000, False, int(pid))
        if not handle:
            return False
        code = ctypes.c_ulong()
        k.GetExitCodeProcess.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong)]
        k.GetExitCodeProcess(handle, ctypes.byref(code))
        k.CloseHandle(handle)
        return code.value == 259


    print("BENCH=" + str(bench), flush=True)
    try:
        (bench / ".startup-test-fixture").touch()
        (bench / "scripts").mkdir()
        for name in ("start-mvp", "core_watchdog", "run-avatar-runtime"):
            src = REPO / "scripts" / (name + ".ps1")
            shutil.copy2(src, bench / "scripts" / (name + ".ps1"))
        shutil.copy2(REPO / "scripts/startup-common.ps1", bench / "scripts/startup-common.ps1")
        shutil.copy2(REPO / "scripts/tests/startup-driver.ps1", bench / "scripts/startup-driver.ps1")
        shutil.copy2(REPO / "start-anime-agent.cmd", bench / "start-anime-agent.cmd")
        core = bench / "services/agent-core"
        shutil.copytree(REPO / "services/agent-core/agent_core", core / "agent_core",
                        ignore=shutil.ignore_patterns("__pycache__"))
        venv.EnvBuilder(with_pip=False).create(core / ".venv")
        shutil.copytree(REPO / "apps/avatar-runtime", bench / "apps/avatar-runtime",
                        ignore=shutil.ignore_patterns('shader_cache'))
        # Copy the installed engine into this bench; the entry/locator is unchanged.
        binaries = list((Path(os.environ["LOCALAPPDATA"]) / "Godot").glob("Godot*_win64.exe"))
        binaries += list((REPO.parent / "tools/godot-4.7.2").glob("Godot*_win64.exe"))
        if binaries:
            (bench / "local/Godot").mkdir()
            shutil.copy2(binaries[0], bench / "local/Godot" / binaries[0].name)
        (bench / ".env").write_text("LLM_PROVIDER=mock\nANIME_AGENT_MCP_SERVERS=\n", encoding="utf-8")

        if options.stress_round:
            bystander = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(3600)'],
                                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                         stderr=subprocess.DEVNULL)
        if options.stress_round == 2:
            # A terminal dies while owning the real named mutex. The command
            # must acquire the abandoned lock, rather than wait forever.
            lock_holder = subprocess.Popen([PS, '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
                                            str(bench / 'scripts/startup-driver.ps1'), '-Action', 'hold-lock'],
                                           env=env, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                           stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW)
            wait_for(lambda: (bench / 'lock-held.txt').exists())
            key = hashlib.sha256((str(bench).lower() + ':' + str(port)).encode()).hexdigest()[:24].upper()
            kernel = ctypes.WinDLL('kernel32', use_last_error=True)
            kernel.OpenMutexW.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.LPCWSTR]
            kernel.OpenMutexW.restype = wintypes.HANDLE
            kernel.CloseHandle.argtypes = [wintypes.HANDLE]
            held_handle = kernel.OpenMutexW(0x00100000, False, 'Local\\AnimeAgent-' + key + '-startup')
            assert held_handle, ctypes.get_last_error()
            try:
                # This reference keeps the abandoned object alive even if the
                # waiting entry has not opened it yet; it cannot be recreated.
                with concurrent.futures.ThreadPoolExecutor(1) as pool:
                    waiting = pool.submit(launch, '00-abandoned-startup-lock')
                    lock_holder.terminate(); lock_holder.wait(10); lock_holder = None
                    assert waiting.result(timeout=240).returncode == 0
            finally:
                kernel.CloseHandle(held_handle)
            passed('real-abandoned-startup-mutex-recovers')
            action('close'); wait_for(exited)

        if options.startup_crash_only or options.stress_round == 2:
            with concurrent.futures.ThreadPoolExecutor(1) as pool:
                future = pool.submit(launch, '01-Core-crash-while-Godot-loading')
                victim = wait_for(health)['pid']
                action('crash')
                injected_at = time.monotonic()
                r = future.result(timeout=240)
            # CIM/taskkill latency can move the injected crash past Ready. A
            # valid Ready cannot promise survival of a subsequent external kill.
            # Still require actual recovery, a new worker and avatar reconnection.
            def recovered_health():
                h = health()
                return h if h and h['pid'] != victim and h['roles']['avatar'] == 1 else None
            if injected_at <= r.finished_at:
                recovered = recovered_health()
                assert recovered, 'Ready was reported before the injected startup crash had recovered'
            else:
                recovered = wait_for(recovered_health, 75)
            (log / 'startup-crash-timing.json').write_text(json.dumps({
                'command_finished_before_injection_completed': r.finished_at < injected_at,
                'victim': victim, 'recovered': recovered['pid'],
            }, indent=2), encoding='utf-8')
        else:
            r = launch("01-cold")
        assert r.returncode == 0, r.stdout + r.stderr
        initial = action()
        assert initial["visible"] and initial["responding"] and health()["roles"]["avatar"] == 1, initial
        passed("cold-start-visible-avatar-and-bridge-TTS-absent", **initial)
        from PIL import ImageGrab
        rect = wintypes.RECT()
        user32 = ctypes.WinDLL('user32')
        user32.SetProcessDPIAware() # Test process only; align window bounds with captured pixels.
        user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
        assert user32.GetWindowRect(initial['window'], ctypes.byref(rect))
        ImageGrab.grab(bbox=(rect.left, rect.top, rect.right, rect.bottom)).save(log / 'cold-avatar.png')
        if options.startup_crash_only:
            assert launch('01-repeat-after-startup-recovery').returncode == 0
            action('close')
            wait_for(exited)
            passed('startup-crash-recovery-repeat-and-exit')
            print('STARTUP_FOCUSED_E2E_OK', flush=True)
            raise SystemExit(0)
        duplicates = 6 if options.stress_round else 2
        with concurrent.futures.ThreadPoolExecutor(duplicates) as pool:
            runs = list(pool.map(lambda i: launch(f"02-duplicate-{i}"), range(duplicates)))
        assert all(r.returncode == 0 for r in runs)
        current = action()
        assert current["avatar"] == initial["avatar"] and current["listener"] == initial["listener"], current
        assert len(current["watchers"]) == 1, current
        passed("concurrent-duplicate-one-avatar-one-core-one-watchdog", commands=duplicates, **current)

        if options.stress_round == 2:
            # Freeze the old watcher across close/reopen, then revive it only
            # after the new session is ready. It must not kill the new Core.
            action('watch-suspend')
            old_watch = current['watchers'][0]
            action('close')
            assert launch('02-reopen-with-delayed-old-watchdog').returncode == 0
            replacement = action()
            action('watch-resume')
            wait_for(lambda: not alive(old_watch))
            current = action()
            assert current['avatar'] == replacement['avatar'] and current['listener'] == replacement['listener']
            assert len(current['watchers']) == 1 and health()['roles']['avatar'] == 1, current
            initial = current
            passed('old-generation-watcher-cannot-clean-new-session', **current)

        old_watcher = current['watchers'][0]
        action('watch-crash')
        assert launch('02-replace-dead-watchdog').returncode == 0
        current = action()
        assert current['avatar'] == initial['avatar'] and len(current['watchers']) == 1
        assert current['watchers'][0] != old_watcher
        passed('stale-watchdog-ack-cannot-hide-dead-watchdog', **current)

        for i in range(3):
            action("close")
            wait_for(exited)
            passed(f"normal-close-cleans-entire-session-{i}")
            assert launch(f"03-reopen-{i}").returncode == 0
            assert health()["roles"]["avatar"] == 1
        for i in range(5 if options.stress_round else 2):
            old = action()["avatar"]
            action("close")
            assert launch(f"04-rapid-reopen-{i}").returncode == 0
            state = action()
            assert state["avatar"] != old and health()["roles"]["avatar"] == 1, state
            passed(f"rapid-close-reopen-{i}", **state)

        before = action()
        action("crash")
        new = wait_for(lambda: (h if (h := health()) and h["pid"] != before["listener"] and
                               h["roles"]["avatar"] == 1 else None), 75)
        assert action()["avatar"] == before["avatar"]
        passed("watchdog-recovers-crashed-Core-avatar-unchanged", old=before["listener"], new=new["pid"])

        # Exact no-argument entry; default startup grace protects slow imports, then
        # three failed probes must recover this genuinely suspended own worker.
        action("suspend")
        assert launch("05-suspended-Core").returncode == 0
        new_state = action()
        assert new_state["listener"] != new["pid"] and health()["roles"]["avatar"] == 1
        passed("same-command-recovers-suspended-own-Core", **new_state)

        watchlog = bench / 'local/AnimeAgent/logs/core-watchdog.log'
        starts = watchlog.read_text(encoding='utf-8', errors='replace').count('recovery-start')
        action('suspend')
        wait_for(lambda: watchlog.read_text(encoding='utf-8', errors='replace').count('recovery-start') > starts, 45)
        close_start = time.monotonic()
        action("close")
        wait_for(exited, 25)
        passed('close-during-recovery-cancels-and-cleans', seconds=round(time.monotonic()-close_start,2))

        errors = []
        for path in (bench / 'local/AnimeAgent/logs').glob('avatar-*.stderr.log'):
            if 'SCRIPT ERROR' in path.read_text(encoding='utf-8', errors='replace'):
                errors.append(path.name)
        assert not errors, errors
        passed('all-avatar-startup-logs-free-of-script-errors')

        # Foreign listener must survive even though it holds our configured port.
        foreign = subprocess.Popen([sys.executable, "-m", "http.server", str(port), "--bind", "127.0.0.1"],
                                   env=env, cwd=bench, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        def foreign_ready():
            try:
                with opener.open(f"http://127.0.0.1:{port}/", timeout=1): return True
            except Exception: return False
        wait_for(foreign_ready)
        r = launch("06-foreign-port")
        assert r.returncode != 0 and "NOT stopped" in r.stdout + r.stderr and foreign.poll() is None
        passed("foreign-port-refused-without-killing-other-program")
        foreign.terminate(); foreign.wait(10); foreign = None

        if options.stress_round == 2:
            impostor_env = dict(env, STARTUP_FIXTURE_MODE='impostor')
            foreign = subprocess.Popen([sys.executable, str(REPO / 'scripts/tests/startup-fixture-core.py')],
                                       env=impostor_env, cwd=bench, stdin=subprocess.DEVNULL,
                                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            wait_for(health)
            r = launch('06-healthy-looking-foreign-impostor')
            assert r.returncode != 0 and 'NOT stopped' in r.stdout and foreign.poll() is None
            passed('HTTP-success-is-not-process-ownership-foreign-impostor-preserved')
            foreign.terminate(); foreign.wait(10); foreign = None
            for bad_port in ('0', '65536', 'not-a-port'):
                env['AGENT_CORE_PORT'] = bad_port
                r = launch('06-invalid-port-' + bad_port)
                assert r.returncode != 0 and 'AGENT_CORE_PORT must be' in r.stdout
            env['AGENT_CORE_PORT'] = str(port)
            assert exited()
            passed('three-invalid-configs-fail-without-process-leaks')

        # Real lightweight process for legacy health compatibility and descendant cleanup.
        shutil.copy2(REPO / "scripts/tests/startup-fixture-core.py", core / "agent_core/main.py")
        env["STARTUP_FIXTURE_MODE"] = "legacy"
        env["HTTP_PROXY"] = env["HTTPS_PROXY"] = "http://127.0.0.1:1"
        assert launch("07-legacy", "-SkipAvatar").returncode == 0
        old = action()
        start = time.monotonic()
        assert launch("07-legacy-reuse", "-SkipAvatar").returncode == 0
        assert action()["listener"] == old["listener"]
        passed("legacy-slow-TTS-health-reused-with-broken-proxy", elapsed=round(time.monotonic()-start,2))
        child = int((bench / "data/fixture-child.pid").read_text())
        assert alive(child)
        action("cleanup")
        wait_for(lambda: not alive(child))
        passed("Core-descendant-process-is-also-terminated")
        env.pop("HTTP_PROXY"); env.pop("HTTPS_PROXY")
        env["STARTUP_FIXTURE_MODE"] = "exit"
        r = launch("08-import-crash", "-SkipAvatar")
        assert r.returncode != 0 and "exited" in (r.stdout+r.stderr).lower()
        passed("startup-crash-propagates-nonzero-command-exit")
        if bystander:
            assert bystander.poll() is None
            passed('unrelated-Python-survives-all-faults-and-cleanup')
        print("STARTUP_REAL_E2E_OK " + str(log), flush=True)
    finally:
        env['AGENT_CORE_PORT'] = str(port)
        if lock_holder and lock_holder.poll() is None:
            lock_holder.terminate(); lock_holder.wait(10)
        if foreign and foreign.poll() is None:
            foreign.terminate(); foreign.wait(10)
        cleanup_error = None
        try:
            if options.stress_round == 2:
                action('watch-resume')
            action("cleanup")
            wait_for(exited, 30)
        except Exception as exc:
            print("cleanup:", exc, flush=True)
            cleanup_error = exc
        if bystander and bystander.poll() is None:
            bystander.terminate(); bystander.wait(10)
        absent_tts.close()
        print("EVIDENCE=" + str(log), flush=True)
        if cleanup_error:
            raise AssertionError('Isolated session cleanup was not verified') from cleanup_error


if __name__ == '__main__':
    main()
