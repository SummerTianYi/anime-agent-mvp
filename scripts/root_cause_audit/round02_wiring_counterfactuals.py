"""Read-only source probes with synthetic Win32 and provider constructors.

No foreground title, config secret, database, network or Core startup is read.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import patch


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--production", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source = args.production.resolve() / "services/agent-core/agent_core"
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(source.parent))
    from agent_core import tools
    assert Path(tools.__file__).resolve() == source / "tools.py"
    rows = []
    calls = []

    class User32:
        def GetForegroundWindow(self):
            calls.append("GetForegroundWindow")
            return 7319

        def GetWindowTextLengthW(self, handle):
            assert handle == 7319
            calls.append("GetWindowTextLengthW")
            return len("R2 synthetic window")

        def GetWindowTextW(self, handle, buffer, length):
            assert handle == 7319 and length == len("R2 synthetic window") + 1
            calls.append("GetWindowTextW")
            buffer.value = "R2 synthetic window"
            return len(buffer.value)

    class Loader:
        user32 = User32()

        def __getattr__(self, name):
            calls.append("loader_lookup:" + name)
            raise OSError("R2 synthetic loader has no DLL named " + name)

    for label, dll in (("actual-library-loader-shape", Loader()), ("selected-user32-counterfactual", User32())):
        calls.clear()
        with patch.object(tools, "os", SimpleNamespace(name="nt")), patch.object(tools.ctypes, "windll", dll, create=True):
            result = tools.active_window()
        rows.append({"case": label, "result": result, "calls": list(calls)})
    assert rows[0]["result"]["ok"] is False and rows[0]["calls"] == ["loader_lookup:GetForegroundWindow"]
    assert rows[1]["result"] == {"ok": True, "title": "R2 synthetic window"}
    main_path = source / "main.py"
    tree = ast.parse(main_path.read_text(encoding="utf-8"))
    factory = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "build_provider")
    module = ast.fix_missing_locations(ast.Module(body=[factory], type_ignores=[]))
    code = compile(module, str(main_path), "exec")

    def constructor(kind):
        def make(**kwargs):
            return {"kind": kind, "kwargs": kwargs}
        return make

    for name, key in (("deepseek", "R2_FAKE"), ("glm", "R2_FAKE"), ("stepfun", "R2_FAKE"), ("glm", ""), ("unknown", "R2_FAKE")):
        namespace = {
            "ChatProvider": object, "LLM_PROVIDER": name, "LLM_TIMEOUT_SECONDS": 10,
            "_provider_config": lambda value, synthetic_key=key: ("https://r2.invalid", "R2-model", synthetic_key),
            "_reload_provider_config": lambda: (_ for _ in ()).throw(AssertionError("reload callback must not run")),
            "MockProvider": constructor("mock"), "OpenAICompatibleProvider": constructor("openai"),
            "AnthropicCompatibleProvider": constructor("anthropic"),
            "os": SimpleNamespace(getenv=lambda key, default=None: default),
            "memory": SimpleNamespace(add_event=lambda *args: None),
        }
        exec(code, namespace)
        built = namespace["build_provider"]()
        rows.append({"case": "factory-wiring", "provider": name, "synthetic_key_present": bool(key),
                     "kind": built["kind"], "constructor_keywords": sorted(built["kwargs"]),
                     "reload_config_supplied": "reload_config" in built["kwargs"]})
    assert [r["kind"] for r in rows[2:]] == ["openai", "openai", "anthropic", "mock", "mock"]
    assert all(not r["reload_config_supplied"] for r in rows[2:])
    report = {"schema": "r2-wiring-counterfactuals-v1", "layer": "isolated source with synthetic dependencies",
              "observations": rows, "model_api_calls": 0, "real_foreground_queries": 0,
              "limits": ["Does not inspect the running provider object", "User32 control substitutes the library object; no production fix", "Factory probe does not trigger live credential reload"],
              "source_sha256": {name: hashlib.sha256((source / name).read_bytes()).hexdigest() for name in ("main.py", "tools.py")},
              "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    with args.output.open("x", encoding="utf-8") as output:
        json.dump(report, output, ensure_ascii=False, indent=2)
    print(json.dumps({"observations": len(rows), "model_api_calls": 0, "real_foreground_queries": 0}))


if __name__ == "__main__":
    main()
