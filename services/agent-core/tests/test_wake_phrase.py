from __future__ import annotations

import unittest

from agent_core.wake_word import is_wake_phrase


class WakePhraseTests(unittest.TestCase):
    def test_exact_name_with_greeting(self) -> None:
        self.assertTrue(is_wake_phrase("嗨，天依"))

    def test_common_mishearings_are_accepted(self) -> None:
        for text in ["嗨 天依", "嗨 田一", "嗨 天忆", "嗨天依", "天依你在吗"]:
            self.assertTrue(is_wake_phrase(text), text)

    def test_non_wake_sentences_rejected(self) -> None:
        for text in ["你好", "今天天气不错", "忆", "播放音乐"]:
            self.assertFalse(is_wake_phrase(text), text)

    def test_tonight_real_mishearings_accepted(self) -> None:
        """2026-09-08 事件表实证的误听变体（zcode 补全）。"""
        for text in ["嗨 天忆", "嗨 便宜", "嗨便宜", "嗨 天翼", "嗨，甜依", "便宜帮个忙"]:
            self.assertTrue(is_wake_phrase(text), text)

    def test_greeting_now_optional(self) -> None:
        self.assertTrue(is_wake_phrase("天依你在吗"))

    def test_still_rejects_unrelated_speech(self) -> None:
        for text in ["你好", "今天天气不错", "忆", "播放音乐", "拜託", "播放点别的"]:
            self.assertFalse(is_wake_phrase(text), text)
