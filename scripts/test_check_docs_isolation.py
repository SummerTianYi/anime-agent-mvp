"""Synthetic sentinel checks; import no application code in the parent."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).with_name("check_docs_consistency.py")


def probe(kind, temporary):
    spec = importlib.util.spec_from_file_location("docs_check", SCRIPT)
    check = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(check)
    # The parent owns cleanup after this child releases its audit hook.
    base = Path(temporary).resolve()
    default = base / "synthetic-default"
    default.mkdir()
    sentinel = default / "private.env"
    sentinel.write_text("SYNTHETIC_PRIVATE_SENTINEL", encoding="utf-8")
    dedicated = base / "dedicated"
    dedicated.mkdir()
    os.environ.update(check.prepare_isolation(dedicated))
    os.environ["LOCALAPPDATA"] = str(default)
    accesses = []
    def audit(event, args):
        if event in {"open", "sqlite3.connect", "os.mkdir"} and isinstance(args[0], (str, bytes)):
            path = Path(os.fsdecode(args[0])).resolve()
            if path.is_relative_to(default):
                accesses.append(event)
                raise RuntimeError("synthetic default sentinel accessed")
    sys.addaudithook(audit)
    if kind == "wrong-config":
        os.environ["ANIME_AGENT_CONFIG_PATH"] = str(sentinel)
    elif kind == "wrong-data":
        os.environ["ANIME_AGENT_DATA_DIR"] = str(default)
    elif kind == "missing-config":
        del os.environ["ANIME_AGENT_CONFIG_PATH"]
    elif kind == "tampered-config":
        (dedicated / "isolated.env").write_text("LLM_PROVIDER=glm\n", encoding="utf-8")
    elif kind == "missing-owner":
        (dedicated / "owner").unlink()
    sys.argv = [str(SCRIPT), "--isolated"]
    result = check.main()
    print(json.dumps({"kind": kind, "exit": result, "sentinel_accesses": accesses,
                      "core_imported": "agent_core.main" in sys.modules}))
    if "agent_core.main" in sys.modules:
        sys.modules["agent_core.main"].memory.close()


class IsolationTests(unittest.TestCase):
    def run_probe(self, kind):
        with tempfile.TemporaryDirectory(prefix="docs-sentinel-") as temporary:
            result = subprocess.run([sys.executable, str(Path(__file__).resolve()), "--probe", kind, temporary],
                                    capture_output=True, text=True, encoding="utf-8", check=False)
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        data = json.loads(result.stdout.splitlines()[-1])
        self.assertEqual(data["sentinel_accesses"], [])
        return data

    def test_wrong_configuration_is_rejected_before_import(self):
        for kind in ("wrong-config", "wrong-data", "missing-config", "tampered-config", "missing-owner"):
            with self.subTest(kind=kind):
                data = self.run_probe(kind)
                self.assertEqual(data["exit"], 2)
                self.assertFalse(data["core_imported"])

    def test_valid_isolation_runs_real_discovery(self):
        data = self.run_probe("valid")
        self.assertEqual(data["exit"], 0)
        self.assertTrue(data["core_imported"])

    def test_public_entry_replaces_inherited_wrong_configuration(self):
        with tempfile.TemporaryDirectory(prefix="docs-inherited-") as temporary:
            root = Path(temporary)
            sentinel = root / "private.env"
            sentinel.write_text("SYNTHETIC_PRIVATE_SENTINEL", encoding="utf-8")
            env = os.environ | {"ANIME_AGENT_DATA_DIR": str(root / "forbidden"),
                "ANIME_AGENT_CONFIG_PATH": str(sentinel), "LOCALAPPDATA": str(root / "default"),
                "LLM_PROVIDER": "glm", "PYTHONUTF8": "1"}
            result = subprocess.run([sys.executable, str(SCRIPT)], env=env, capture_output=True,
                                    text=True, encoding="utf-8", check=False)
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            self.assertIn("DOCS_ISOLATION_OK", result.stdout)
            self.assertFalse((root / "forbidden").exists())
            self.assertFalse((root / "default").exists())
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "SYNTHETIC_PRIVATE_SENTINEL")


if __name__ == "__main__":
    if sys.argv[1:2] == ["--probe"]:
        probe(sys.argv[2], sys.argv[3])
    else:
        unittest.main()
