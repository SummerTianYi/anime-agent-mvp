from __future__ import annotations

import json
import unittest

from agent_core.harness import CharacterHarness, behavior_events, default_title


class SongCatalogTests(unittest.TestCase):
    def setUp(self) -> None:
        self.harness = CharacterHarness()

    def test_catalog_contains_only_original_seed_songs(self) -> None:
        self.assertGreaterEqual(len(self.harness.catalog.songs), 20)
        self.assertTrue(all(song.original for song in self.harness.catalog.songs))

    def test_exact_title_retrieval_finds_creator(self) -> None:
        results = self.harness.catalog.search("《勾指起誓》是谁创作的？")
        self.assertEqual(results[0].title, "勾指起誓")
        self.assertIn("ilem", results[0].creators)

    def test_generic_music_query_returns_representative_order(self) -> None:
        results = self.harness.catalog.search("你唱过哪些原创歌？", limit=3)
        self.assertEqual(
            [song.title for song in results],
            ["勾指起誓", "权御天下", "普通DISCO"],
        )

    def test_non_music_prompt_does_not_inject_song_records(self) -> None:
        messages = self.harness.build_messages(
            [{"role": "user", "content": "今天天气怎么样？"}],
            "今天天气怎么样？",
        )
        self.assertNotIn("【本轮歌曲资料】", messages[0]["content"])

    def test_music_prompt_injects_only_relevant_records(self) -> None:
        messages = self.harness.build_messages(
            [{"role": "user", "content": "勾指起誓是谁写的？"}],
            "勾指起誓是谁写的？",
        )
        system_prompt = messages[0]["content"]
        self.assertIn("【本轮歌曲资料】", system_prompt)
        self.assertIn("创作者：ilem", system_prompt)

    def test_assistant_history_is_normalized_to_output_contract(self) -> None:
        messages = self.harness.build_messages(
            [
                {"role": "user", "content": "你好"},
                {"role": "assistant", "content": "你好呀。"},
                {"role": "user", "content": "今天怎么样？"},
            ],
            "今天怎么样？",
        )
        assistant_payload = json.loads(messages[2]["content"])
        self.assertEqual(assistant_payload["reply"], "你好呀。")
        self.assertEqual(assistant_payload["gesture"], "none")


class StructuredReplyTests(unittest.TestCase):
    def test_valid_reply_is_parsed_and_clamped(self) -> None:
        raw = json.dumps(
            {
                "reply": "当然记得呀。",
                "emotion": "happy",
                "emotion_intensity": 1.8,
                "gesture": "nod",
                "memory_candidate": None,
            },
            ensure_ascii=False,
        )
        reply = CharacterHarness.parse_reply(raw)
        self.assertEqual(reply.reply, "当然记得呀。")
        self.assertEqual(reply.emotion, "happy")
        self.assertEqual(reply.emotion_intensity, 1.0)
        self.assertEqual(reply.gesture, "nod")
        self.assertEqual(
            [event_name for event_name, _ in behavior_events(reply)],
            ["avatar.smile", "avatar.nod"],
        )

    def test_prose_with_trailing_json_recovers_contract(self) -> None:
        raw = (
            "现在是下午 4 点整，星期一哦～今天过得怎么样？"
            '{"reply":"现在是下午 4 点整，星期一哦～","emotion":"happy","emotion_intensity":0.4,'
            '"gesture":"none","memory_candidate":null}'
        )
        reply = CharacterHarness.parse_reply(raw)
        self.assertEqual(reply.reply, "现在是下午 4 点整，星期一哦～")
        self.assertEqual(reply.emotion, "happy")
        self.assertEqual(reply.gesture, "none")

    def test_invalid_metadata_falls_back_to_safe_values(self) -> None:
        raw = json.dumps(
            {
                "reply": "你好。",
                "emotion": "overexcited",
                "emotion_intensity": "invalid",
                "gesture": "delete_files",
            },
            ensure_ascii=False,
        )
        reply = CharacterHarness.parse_reply(raw)
        self.assertEqual(reply.emotion, "neutral")
        self.assertEqual(reply.emotion_intensity, 0.35)
        self.assertEqual(reply.gesture, "none")
        self.assertEqual(behavior_events(reply), [])

    def test_plain_text_provider_response_remains_usable(self) -> None:
        reply = CharacterHarness.parse_reply("这是一条普通回复。")
        self.assertEqual(reply.reply, "这是一条普通回复。")
        self.assertEqual(reply.emotion, "neutral")


class SessionTitleTests(unittest.TestCase):
    def test_parse_reply_extracts_and_sanitizes_session_title(self) -> None:
        raw = json.dumps(
            {
                "reply": "好呀。",
                "emotion": "happy",
                "emotion_intensity": 0.5,
                "gesture": "none",
                "memory_candidate": None,
                "session_title": "「天气话题」",
            },
            ensure_ascii=False,
        )
        reply = CharacterHarness.parse_reply(raw)
        self.assertEqual(reply.session_title, "天气话题")

    def test_parse_reply_without_title_field_yields_none(self) -> None:
        reply = CharacterHarness.parse_reply('{"reply":"你好呀","emotion":"neutral"}')
        self.assertIsNone(reply.session_title)

    def test_build_messages_adds_title_instruction_only_when_requested(self) -> None:
        harness = CharacterHarness()
        history = [{"role": "user", "content": "你好呀"}]
        with_title = harness.build_messages(history, "你好呀", request_session_title=True)
        without_title = harness.build_messages(history, "你好呀")
        self.assertIn("【会话标题】", with_title[0]["content"])
        self.assertIn("session_title", with_title[0]["content"])
        self.assertNotIn("【会话标题】", without_title[0]["content"])

    def test_default_title_truncates_user_text(self) -> None:
        self.assertEqual(len(default_title("帮我" * 40)), 12)
        self.assertEqual(default_title("   "), "")


if __name__ == "__main__":
    unittest.main()


class InnerQuoteRepairTests(unittest.TestCase):
    def test_parse_reply_repairs_unescaped_inner_quotes(self) -> None:
        raw = (
            '{"reply": "嘿嘿，简单说呀～我只会"看"，不会替你点击或改文件。", '
            '"emotion":"happy","emotion_intensity":0.5,"gesture":"none",'
            '"memory_candidate":"null","session_title":"洛天依能做什么"}'
        )
        reply = CharacterHarness.parse_reply(raw)
        self.assertEqual(reply.reply, '嘿嘿，简单说呀～我只会"看"，不会替你点击或改文件。')
        self.assertEqual(reply.emotion, "happy")
        self.assertEqual(reply.session_title, "洛天依能做什么")

    def test_trailing_json_recovery_also_repairs_inner_quotes(self) -> None:
        raw = (
            '好呀，我来介绍一下自己！\n{"reply": "我只会"看"，不会改。", '
            '"emotion":"neutral"}'
        )
        reply = CharacterHarness.parse_reply(raw)
        self.assertEqual(reply.reply, '我只会"看"，不会改。')

    def test_already_escaped_quotes_parse_unchanged(self) -> None:
        raw = '{"reply": "我说\\"看\\"这个字。", "emotion": "happy"}'
        reply = CharacterHarness.parse_reply(raw)
        self.assertEqual(reply.reply, '我说"看"这个字。')

    def test_memory_candidate_null_string_is_dropped(self) -> None:
        raw = '{"reply": "好。", "emotion": "happy", "memory_candidate": "null"}'
        reply = CharacterHarness.parse_reply(raw)
        self.assertIsNone(reply.memory_candidate)
        reply2 = CharacterHarness.parse_reply('{"reply": "好。", "memory_candidate": "None"}')
        self.assertIsNone(reply2.memory_candidate)
