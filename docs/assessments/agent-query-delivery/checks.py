"""Offline verification in a new directory. Never import Core before isolation."""
import argparse
import os
from pathlib import Path
import runpy
import socket
import sys
import tempfile
import unittest
import weakref

ROOT = Path(__file__).resolve().parents[3]
CORE = ROOT / "services/agent-core"


def isolate(path):
    path.mkdir(parents=True, exist_ok=False)
    for k in list(os.environ):
        if k.startswith(("ANIME_AGENT_", "LLM_", "GLM_", "DEEPSEEK_", "STEPFUN_", "TAVILY_", "TTS_", "STT_", "AGENT_CORE_")):
            os.environ.pop(k)
    for part in ("data", "home/Desktop", "local", "roaming", "temp"):
        (path / part).mkdir(parents=True)
    config = path / "settings.env"
    config.touch()
    os.environ.update(ANIME_AGENT_CONFIG_PATH=str(config), ANIME_AGENT_DATA_DIR=str(path / "data"),
        LOCALAPPDATA=str(path / "local"), APPDATA=str(path / "roaming"), USERPROFILE=str(path / "home"),
        TEMP=str(path / "temp"), TMP=str(path / "temp"), LLM_PROVIDER="mock", ANIME_AGENT_TTS="0",
        ANIME_AGENT_WAKE_WORD="0", ANIME_AGENT_PROACTIVE="0", ANIME_AGENT_FAREWELL_PRECACHE="0",
        ANIME_AGENT_IDLE_THRESHOLD="0", ANIME_AGENT_VOICE_INPUT_MODE="manual", ANIME_AGENT_TTS_NARRATE="0",
        ANIME_AGENT_MCP_SERVERS="", ANIME_AGENT_WRITE_ROOTS=str(path), ANIME_AGENT_TOOLS_ROOTS=str(path),
        ANIME_AGENT_ALLOWED_COMMANDS="", TTS_SERVICE_URL="http://127.0.0.1:1", HF_HUB_OFFLINE="1")
    tempfile.tempdir = str(path / "temp")
    sys.path[:0] = [str(CORE), str(CORE / "tests")]


def offline(path):
    listeners = weakref.WeakSet()
    local = ("localhost", "127.0.0.1", "::1")
    def guard(event, args):
        if event == "sqlite3.connect" and str(args[0]) != ":memory:" and not Path(args[0]).resolve().is_relative_to(path):
            raise RuntimeError("Database outside test directory")
        if event == "socket.getaddrinfo" and args[0] not in (*local, None):
            raise OSError("External DNS disabled")
        if event == "socket.bind":
            s, addr = args
            if addr[0] not in local or addr[1]:
                raise OSError("Only test-owned ephemeral listeners")
            listeners.add(s)
        if event == "socket.connect":
            for listener in tuple(listeners):
                try:
                    if args[1][0] in local and listener.getsockname()[1] == args[1][1] and listener.getsockopt(socket.SOL_SOCKET, socket.SO_ACCEPTCONN):
                        return
                except OSError:
                    continue
            raise ConnectionRefusedError("Connection outside test process")
        if event in ("os.startfile", "os.system"):
            raise RuntimeError("Desktop actions disabled")
    sys.addaudithook(guard)


if __name__ == "__main__":
    cli = argparse.ArgumentParser()
    cli.add_argument("state", type=Path)
    cli.add_argument("tests", nargs="*")
    args = cli.parse_args()
    box = args.state.resolve()
    isolate(box)
    offline(box)
    os.chdir(CORE)
    if args.tests == ["docs"]:
        runpy.run_path(str(ROOT / "scripts/check_docs_consistency.py"), run_name="__main__")
    else:
        from agent_core import main as core
        assert core.memory.path.resolve().is_relative_to(box) and core.provider.name == "mock"
        assert not core.TTS_ENABLED and not core.mcp_host.tool_entries()
        loader = unittest.defaultTestLoader
        suite = loader.loadTestsFromNames(args.tests) if args.tests else loader.discover("tests")
        with (box / "unittest.txt").open("w", encoding="utf-8") as log:
            result = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
        print("tests", result.testsRun, "skipped", len(result.skipped), "failed", [t.id() for t, _ in result.failures + result.errors])
        sys.exit(not result.wasSuccessful())
