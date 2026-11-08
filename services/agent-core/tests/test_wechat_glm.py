"""Codex: shared account config and real launcher guard, isolated/fake credentials."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from agent_core import main as core


SETTINGS = {
    "GLM_CREDENTIAL_SOURCE": "deepseek", "GLM_MODEL": "GLM-5.2",
    "DEEPSEEK_BASE_URL": "https://chatapi.weixin.qq.com/openai/v1",
    "DEEPSEEK_MODEL": "Deepseek-v4-flash", "DEEPSEEK_API_KEY": "fake-shared",
    "GLM_API_KEY": "fake-obsolete", "GLM_BASE_URL": "https://old.test/v1",
}


class WeChatGlmTests(unittest.TestCase):
    def test_factory_uses_shared_endpoint_and_key(self):
        with patch.dict(os.environ, SETTINGS, clear=True), patch.object(core, "LLM_PROVIDER", "glm"):
            provider = core.build_provider()
        self.assertIsInstance(provider, core.OpenAICompatibleProvider)
        self.assertEqual((provider.base_url, provider.model, provider.api_key),
                         (SETTINGS["DEEPSEEK_BASE_URL"], "GLM-5.2", "fake-shared"))
        self.assertEqual(provider.completion_url, SETTINGS["DEEPSEEK_BASE_URL"] + "/chat/completions")

    def test_deepseek_default_unchanged(self):
        with patch.dict(os.environ, SETTINGS, clear=True), patch.object(core, "LLM_PROVIDER", "deepseek"):
            provider = core.build_provider()
        self.assertEqual((provider.name, provider.model, provider.api_key),
                         ("deepseek", "Deepseek-v4-flash", "fake-shared"))

    def test_missing_shared_key_never_falls_back_to_old_glm_key(self):
        with patch.dict(os.environ, {**SETTINGS, "DEEPSEEK_API_KEY": ""}, clear=True):
            self.assertEqual(core._provider_config("glm")[2], "")

    def test_original_glm_account_remains_supported(self):
        with patch.dict(os.environ, {**SETTINGS, "GLM_CREDENTIAL_SOURCE": "glm"}, clear=True):
            self.assertEqual(core._provider_config("glm"), ("https://old.test/v1", "GLM-5.2", "fake-obsolete"))

    def test_invalid_source_fails_closed(self):
        with patch.dict(os.environ, {**SETTINGS, "GLM_CREDENTIAL_SOURCE": "typo"}, clear=True):
            with self.assertRaises(ValueError):
                core._provider_config("glm")

    def test_reload_uses_shared_file_settings_and_preserves_case(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, SETTINGS, clear=True):
            file = Path(tmp) / ".env"
            file.write_text("GLM_CREDENTIAL_SOURCE= DeepSeek \nDEEPSEEK_BASE_URL=https://new.test/v1\n"
                            "DEEPSEEK_API_KEY=fake-new\nGLM_MODEL=GLM-5.2\n", encoding="utf-8")
            self.assertEqual(core._reload_provider_config("glm", file),
                             ("https://new.test/v1", "GLM-5.2", "fake-new"))
            file.write_text("GLM_CREDENTIAL_SOURCE=deepseek\n", encoding="utf-8")
            with patch.dict(os.environ, {"DEEPSEEK_API_KEY": ""}):
                self.assertIsNone(core._reload_provider_config("glm", file))

    @unittest.skipUnless(os.name == "nt" and shutil.which("powershell.exe"), "Windows launcher guard")
    def test_real_startup_guard_accepts_shared_account_without_zhipu_key(self):
        # Extract only the actual config validation; never initialize/start/stop
        # any real service, access the owner's .env or acquire session locks.
        file = Path(__file__).resolve().parents[3] / "scripts/start-mvp.ps1"
        text = file.read_text(encoding="utf-8")
        guard = text[text.index("    $providerName ="):text.index("    Write-Host", text.index("    $providerName ="))]
        script = "$ErrorActionPreference='Stop'; function Get-AgentSetting($name,$default='') { " \
                 "$v=[Environment]::GetEnvironmentVariable($name); if($null -eq $v){$default}else{$v} }; "
        for source, key, expected in (("deepseek", "fake-shared", 0), ("deepseek", "", 1), ("typo", "fake-shared", 1)):
            with self.subTest(source=source, key_present=bool(key)):
                env = {k: v for k, v in os.environ.items() if k != "PSModulePath"}
                env.update(SETTINGS, LLM_PROVIDER="glm", GLM_CREDENTIAL_SOURCE=source,
                           DEEPSEEK_API_KEY=key, GLM_API_KEY="")
                result = subprocess.run(["powershell.exe", "-NoProfile", "-Command",
                                         script + "try { " + guard + "; exit 0 } catch { exit 1 }"],
                                        env=env, capture_output=True, timeout=15)
                self.assertEqual(result.returncode, expected, result.stderr.decode(errors="replace"))
