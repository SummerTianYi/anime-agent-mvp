"""Provider hot-reload: swap the API key in .env and the next request just works.

Covers the key-exhaustion workflow: GLM answers 401/403/429, the provider
re-reads the .env file, and retries the same request once with the fresh
credentials — no Core restart needed.
"""
from __future__ import annotations

import asyncio
import io
import json
import os
import unittest
import unittest.mock
import urllib.error
import urllib.request
from pathlib import Path

os.environ.setdefault("ANIME_AGENT_WAKE_WORD", "0")

from agent_core import main as core
from agent_core.main import OpenAICompatibleProvider, ProviderError, _reload_provider_config


def _http_error(code: int) -> urllib.error.HTTPError:
    body = json.dumps({"error": {"message": f"http {code}"}}).encode("utf-8")
    return urllib.error.HTTPError("https://example.test/v1/chat/completions", code, "err", {}, io.BytesIO(body))


def _ok_response(text: str) -> bytes:
    return json.dumps({"choices": [{"message": {"content": text}}]}).encode("utf-8")


class _ScriptedHttp:
    """Stands in for the real HTTP layer with a scripted list of outcomes."""

    def __init__(self, outcomes: list) -> None:
        self.outcomes = list(outcomes)
        self.requests: list[urllib.request.Request] = []
        # the retried Request is mutated in place, so record the wire-time header
        self.auth_at_call: list[str | None] = []

    def __call__(self, request: urllib.request.Request) -> bytes:
        self.requests.append(request)
        self.auth_at_call.append(request.get_header("Authorization"))
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def _make_provider(outcomes: list, reload_result) -> tuple[OpenAICompatibleProvider, _ScriptedHttp, list[bool]]:
    reload_calls: list[bool] = []

    def reload_config():
        reload_calls.append(True)
        return reload_result

    provider = OpenAICompatibleProvider(
        name="glm",
        base_url="https://example.test/v1",
        model="test-model",
        api_key="old-key",
        timeout_seconds=5,
        reload_config=reload_config,
    )
    fake = _ScriptedHttp(outcomes)
    provider._request = fake
    return provider, fake, reload_calls


def _run(awaitable):
    return asyncio.run(awaitable)


class ProviderHotReloadTests(unittest.TestCase):
    def test_429_reloads_env_and_retries_with_new_key(self) -> None:
        fresh = ("https://example.test/v1", "test-model", "new-key")
        provider, fake, reload_calls = _make_provider(
            [_http_error(429), _ok_response("换弹匣成功")], fresh
        )
        result = _run(provider.complete([{"role": "user", "content": "hi"}]))
        self.assertEqual(result, "换弹匣成功")
        self.assertEqual(len(fake.requests), 2)
        self.assertEqual(reload_calls, [True])
        self.assertEqual(provider.api_key, "new-key")
        self.assertEqual(
            fake.auth_at_call, ["Bearer old-key", "Bearer new-key"]
        )

    def test_unchanged_config_means_no_retry(self) -> None:
        same = ("https://example.test/v1", "test-model", "old-key")
        provider, fake, reload_calls = _make_provider([_http_error(429)], same)
        with self.assertRaises(ProviderError):
            _run(provider.complete([{"role": "user", "content": "hi"}]))
        self.assertEqual(len(fake.requests), 1)
        self.assertEqual(reload_calls, [True])

    def test_auth_codes_reload_but_500_does_not(self) -> None:
        for code in (401, 403):
            with self.subTest(code=code):
                provider, fake, reload_calls = _make_provider(
                    [_http_error(code), _ok_response("ok")],
                    ("https://example.test/v1", "test-model", "new-key"),
                )
                result = _run(provider.complete([{"role": "user", "content": "hi"}]))
                self.assertEqual(result, "ok")
                self.assertEqual(len(fake.requests), 2)
        provider, fake, reload_calls = _make_provider(
            [_http_error(500), _ok_response("ok")],
            ("https://example.test/v1", "test-model", "new-key"),
        )
        with self.assertRaises(ProviderError):
            _run(provider.complete([{"role": "user", "content": "hi"}]))
        self.assertEqual(len(fake.requests), 1)
        self.assertEqual(reload_calls, [])

    def test_tool_turn_reloads_and_retries(self) -> None:
        fresh = ("https://example.test/v1", "test-model", "new-key")
        provider, fake, _ = _make_provider(
            [_http_error(429), _ok_response("最终回复")], fresh
        )
        result = _run(provider.complete_with_tools([{"role": "user", "content": "hi"}], []))
        self.assertEqual(result["content"], "最终回复")
        self.assertEqual(result["tool_calls"], [])
        self.assertEqual(len(fake.requests), 2)
        self.assertEqual(provider.api_key, "new-key")

    def test_reload_without_key_does_not_retry(self) -> None:
        provider, fake, _ = _make_provider([_http_error(429)], None)
        with self.assertRaises(ProviderError):
            _run(provider.complete([{"role": "user", "content": "hi"}]))
        self.assertEqual(len(fake.requests), 1)


class ReloadProviderConfigTests(unittest.TestCase):
    def test_reads_swapped_key_from_env_file(self) -> None:
        with unittest.mock.patch.object(core, "ENV_PATH", Path(self._tmp.name) / ".env"):
            Path(core.ENV_PATH).write_text(
                "# comment\nGLM_BASE_URL=https://example.test/v2\n"
                "GLM_MODEL=other-model\nGLM_API_KEY=\"file-key\"\n",
                encoding="utf-8",
            )
            config = _reload_provider_config("glm")
        self.assertEqual(config, ("https://example.test/v2", "other-model", "file-key"))

    def test_missing_entries_fall_back_to_process_env(self) -> None:
        os.environ["GLM_API_KEY"] = "env-key"
        self.addCleanup(os.environ.pop, "GLM_API_KEY", None)
        with unittest.mock.patch.object(core, "ENV_PATH", Path(self._tmp.name) / "absent.env"):
            config = _reload_provider_config("glm")
        self.assertEqual(config[2], "env-key")

    def test_no_key_anywhere_returns_none(self) -> None:
        os.environ.pop("GLM_API_KEY", None)
        with unittest.mock.patch.object(core, "ENV_PATH", Path(self._tmp.name) / "absent.env"):
            config = _reload_provider_config("glm")
        self.assertIsNone(config)

    def setUp(self) -> None:
        import tempfile

        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)

    @staticmethod
    def _run(awaitable):
        return asyncio.run(awaitable)

    def _raises_provider_error(self):
        return self.assertRaises(ProviderError)


if __name__ == "__main__":
    unittest.main()
