"""R2 reviewer counterexamples: isolated source methods and synthetic inputs.

Never imports main/Core, never connects to a service, and intercepts commands.
This records defects as observations, not product passes or fixed behavior.
"""
import argparse
import ast
import asyncio
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import urllib.error
import urllib.request
from unittest.mock import patch


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--production", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source = args.production.resolve() / "services/agent-core/agent_core"
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(source.parent))
    from agent_core import tools, harness, storage
    for module in (tools, harness, storage):
        if Path(module.__file__).resolve() != source / (module.__name__.split(".")[-1] + ".py"):
            raise RuntimeError("Wrong source imported")
    rows = []
    with tempfile.TemporaryDirectory(prefix="tianyi-r2-edges-") as directory:
        root = Path(directory)
        with patch.dict(os.environ, {"ANIME_AGENT_TOOLS_ROOTS": str(root)}):
            for first_byte in (b"A", b"\xff"):
                payload = first_byte + b"A" * 65534 + "甲END".encode()
                file = root / "mixed-utf8.txt"
                file.write_bytes(payload)
                first = tools.read_file(str(file))
                second = tools.read_file(str(file), first["next_offset"])
                joined = first["content"] + second["content"]
                expected = payload.decode("utf-8", errors="replace")
                rows.append({"case": "read-mixed-utf8", "first_byte_hex": first_byte.hex(),
                             "next_offset": first["next_offset"], "joined_tail": joined[-12:],
                             "expected_tail": expected[-12:], "preserves_valid_suffix": joined == expected})
        with patch.dict(os.environ, {"ANIME_AGENT_ALLOWED_COMMANDS": "r2_echo.exe"}):
            for command in (r'"C:\R2\r2_echo.exe" --mode "synthetic value"',
                            r'"C:\R2 Fixture\r2_echo.exe" --mode "synthetic value"'):
                with patch.object(subprocess, "run", return_value=subprocess.CompletedProcess([], 0, "R2", "")) as run:
                    result = tools.run_command(command)
                    rows.append({"case": "command-quoted-path", "command": command, "result": result,
                                 "mock_calls": run.call_count, "argv": run.call_args.args[0] if run.called else None})
        db = storage.MemoryStore(root / "db")
        try:
            session = db.create_session("R2 context")['id']
            for number in range(25):
                db.add_message("user" if number % 2 == 0 else "assistant", f"R2-{number:02}", conversation_id=session)
            character = harness.CharacterHarness.__new__(harness.CharacterHarness)
            character.catalog = SimpleNamespace(search=lambda value: [], format_context=lambda value: "")
            messages = character.build_messages(db.load_messages(20, session), "R2-24")
            normalized = [json.loads(m["content"])["reply"] if m["role"] == "assistant" else m["content"]
                          for m in messages[1:]]
            rows.append({"case": "history-harness-window", "roles": [m["role"] for m in messages],
                         "contents_without_system": normalized, "latest_occurrences": normalized.count("R2-24"),
                         "exact_window": normalized == [f"R2-{n:02}" for n in range(5, 25)]})
        finally:
            db.close()
    for raw in ('{"reply":"R2正常"}', '{"reply":null}', '{"reply":175}', '{', '{"reply":""}'):
        rows.append({"case": "parse-reply-type", "raw": raw, "parsed": asdict(harness.CharacterHarness.parse_reply(raw))})

    # Extract ONLY the two actual adapter methods. No module-level initialization.
    main_path = source / "main.py"
    tree = ast.parse(main_path.read_text(encoding="utf-8"))
    provider = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "OpenAICompatibleProvider")
    methods = [node for node in provider.body if isinstance(node, ast.AsyncFunctionDef) and
               node.name in {"complete", "complete_with_tools"}]

    class ProviderError(RuntimeError):
        pass

    class ToolsUnsupportedError(RuntimeError):
        pass

    namespace = dict(json=json, urllib=urllib, ProviderError=ProviderError, ToolsUnsupportedError=ToolsUnsupportedError,
                     TRANSPORT_ERRORS=(OSError,), network_message=lambda name, exc: f"{name}: {type(exc).__name__}")
    exec(compile(ast.Module(body=methods, type_ignores=[]), str(main_path), "exec"), namespace)

    async def check():
        for content in ("R2正常", None, "", 175, [{"text": "R2"}]):
            payload = {"choices": [{"message": {"content": content}}]}
            for method in ("complete", "complete_with_tools"):
                await one(method, payload)
        for method in ("complete", "complete_with_tools"):
            await one(method, {"choices": [{"message": None}]})

    async def one(method, payload):
        calls = []

        async def fake_send(request):
            calls.append({"url": request.full_url, "body": json.loads(request.data)})
            return json.dumps(payload, ensure_ascii=False).encode("utf-8")

        fake = SimpleNamespace(api_key="R2-SYNTHETIC-NOT-A-CREDENTIAL", name="R2-fake", model="R2-fake",
                               completion_url="https://r2.invalid/v1/chat/completions", _send_with_config_reload=fake_send)
        try:
            call_args = [fake, [{"role": "user", "content": "R2"}]]
            if method == "complete_with_tools":
                call_args.append([])
            result = await namespace[method](*call_args)
            outcome = {"value": result}
        except Exception as exc:
            outcome = {"exception": type(exc).__name__, "message": str(exc)}
        rows.append({"case": "adapter-null-and-types", "method": method, "payload": payload,
                     "outcome": outcome, "fake_transport_calls": calls})

    asyncio.run(check())
    report = {"layer": "isolated synthetic reviewer counterexamples", "api_calls": 0, "live_database_access": False,
              "temporary_objects_cleaned": True, "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "source_hashes": {name: hashlib.sha256((source / name).read_bytes()).hexdigest()
                                for name in ("tools.py", "storage.py", "harness.py", "main.py")}, "rows": rows}
    with args.output.open("x", encoding="utf-8") as output:
        json.dump(report, output, ensure_ascii=False, indent=2)
    print(json.dumps({"observations": len(rows), "api_calls": 0}))


if __name__ == "__main__":
    main()
