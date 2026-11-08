"""Run the repository's Core regression or documentation check in a fresh private directory."""
import argparse
import json
import os
from pathlib import Path
import runpy
import socket
import sys
import tempfile
import time
import unittest
import weakref

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CORE = ROOT / "services/agent-core"
AFFECTED = ("test_companion_channels", "test_conversation_context", "test_companion_persona",
            "test_harness", "test_deepseek_official")


def sandbox(box):
    for key in list(os.environ):
        if key.startswith(("ANIME_AGENT_", "LLM_", "GLM_", "DEEPSEEK_", "STEPFUN_", "TTS_", "STT_")):
            del os.environ[key]
    cfg = box / "fixture.env"
    cfg.write_text("# Isolated fixture\n", encoding="utf-8")
    for name in ("tmp", "profile", "profile/Desktop", "local", "roaming", "data", "logs"):
        (box / name).mkdir()
    os.environ.update(ANIME_AGENT_CONFIG_PATH=str(cfg), ANIME_AGENT_DATA_DIR=str(box / "data"),
                      LOCALAPPDATA=str(box / "local"), APPDATA=str(box / "roaming"),
                      USERPROFILE=str(box / "profile"), TEMP=str(box / "tmp"), TMP=str(box / "tmp"),
                      ANIME_AGENT_TTS="0", ANIME_AGENT_WAKE_WORD="0", ANIME_AGENT_VOICE_INPUT_MODE="manual",
                      ANIME_AGENT_IDLE_THRESHOLD="0", ANIME_AGENT_FAREWELL_PRECACHE="0",
                      ANIME_AGENT_MCP_SERVERS="", ANIME_AGENT_TOOLS_ROOTS=str(box),
                      ANIME_AGENT_WRITE_ROOTS=str(box), ANIME_AGENT_ALLOWED_COMMANDS="",
                      TTS_SERVICE_URL="http://127.0.0.1:1", LLM_PROVIDER="mock",
                      HF_HUB_OFFLINE="1", NO_PROXY="127.0.0.1,localhost,::1")
    tempfile.tempdir = str(box / "tmp")


def offline_fence(box):
    sockets = weakref.WeakSet()
    local = {"127.0.0.1", "::1", "localhost"}
    def guard(event, args):
        if event == "sqlite3.connect":
            db = str(args[0])
            if db != ":memory:" and not Path(db).resolve().is_relative_to(box):
                raise RuntimeError("Non-fixture database")
        if event == "socket.getaddrinfo" and args[0] not in (*local, None):
            raise OSError("Offline DNS")
        if event == "socket.bind":
            sock, address = args
            if address[0] not in local or address[1] != 0:
                raise OSError("Only test-owned ephemeral listeners")
            sockets.add(sock)
        if event == "socket.connect":
            _, address = args
            if address[0] in local:
                for listener in list(sockets):
                    try:
                        if listener.getsockname()[1] == address[1] and listener.getsockopt(
                                socket.SOL_SOCKET, socket.SO_ACCEPTCONN):
                            return
                    except OSError:
                        pass
            raise ConnectionRefusedError("Offline connection outside this process's listeners")
        if event in {"os.startfile", "os.system"}:
            raise RuntimeError("Desktop or shell action outside fixture")
    sys.addaudithook(guard)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("affected", "full", "docs"))
    parser.add_argument("box", type=Path, help="New private directory outside the repository")
    args = parser.parse_args()
    box = args.box.resolve()
    if box.is_relative_to(ROOT):
        parser.error("Use a new directory outside the repository")
    box.mkdir(parents=True, exist_ok=False)
    sandbox(box)
    offline_fence(box)
    sys.path[:0] = [str(CORE), str(CORE / "tests")]
    os.chdir(CORE)
    if args.mode == "docs":
        runpy.run_path(str(ROOT / "scripts/check_docs_consistency.py"), run_name="__main__")
        return
    from agent_core import main as core
    assert core.provider.name == "mock" and not core.TTS_ENABLED and not core.mcp_host.tool_entries()
    loader = unittest.defaultTestLoader
    suite = (loader.discover(str(CORE / "tests")) if args.mode == "full"
             else loader.loadTestsFromNames(AFFECTED))
    started = time.monotonic()
    with (box / "logs/unittest.txt").open("w", encoding="utf-8") as log:
        result = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
    print(json.dumps(dict(mode=args.mode, run=result.testsRun, seconds=round(time.monotonic()-started, 3),
                          skipped=[t.id() for t, _ in result.skipped],
                          failures=[t.id() for t, _ in result.errors + result.failures],
                          ok=result.wasSuccessful())))
    core.memory.close()
    raise SystemExit(int(not result.wasSuccessful()))


if __name__ == "__main__":
    main()
