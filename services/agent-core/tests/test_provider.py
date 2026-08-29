from __future__ import annotations

import io
import unittest
from urllib.error import HTTPError

from agent_core.main import OpenAICompatibleProvider


class ProviderErrorTests(unittest.TestCase):
    def test_http_error_detail_extracts_safe_provider_message(self) -> None:
        error = HTTPError(
            "https://example.invalid/chat/completions",
            429,
            "Too Many Requests",
            {},
            io.BytesIO(
                '{"error":{"code":"1113","message":"余额不足或无可用资源包,请充值。"}}'.encode()
            ),
        )
        self.assertEqual(
            OpenAICompatibleProvider._http_error_detail(error),
            "余额不足或无可用资源包,请充值。",
        )

    def test_http_error_detail_ignores_unrecognized_body(self) -> None:
        error = HTTPError(
            "https://example.invalid/chat/completions",
            500,
            "Server Error",
            {},
            io.BytesIO(b"not-json"),
        )
        self.assertEqual(OpenAICompatibleProvider._http_error_detail(error), "")


if __name__ == "__main__":
    unittest.main()
