from __future__ import annotations

import json
import unittest

from agent_core.harness import CharacterHarness, behavior_events


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


if __name__ == "__main__":
    unittest.main()
