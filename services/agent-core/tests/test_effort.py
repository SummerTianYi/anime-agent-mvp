from __future__ import annotations

import unittest

from agent_core.main import (
    DEFAULT_EFFORT,
    EFFORT_LEVELS,
    EFFORT_PROMPT_NOTES,
    MAX_TOOL_STEPS,
    effort_prompt_note,
    resolve_effort,
)


class ResolveEffortTest(unittest.TestCase):
    def test_default_is_deep(self) -> None:
        self.assertEqual(DEFAULT_EFFORT, "deep")
        self.assertEqual(resolve_effort(None), "deep")
        self.assertEqual(resolve_effort(""), "deep")

    def test_unknown_value_falls_back_to_deep(self) -> None:
        self.assertEqual(resolve_effort("turbo"), "deep")
        self.assertEqual(resolve_effort(123), "deep")

    def test_known_values_pass_through_case_insensitive(self) -> None:
        self.assertEqual(resolve_effort("chill"), "chill")
        self.assertEqual(resolve_effort("  STANDARD  "), "standard")


class EffortLadderTest(unittest.TestCase):
    def test_deep_keeps_historical_step_budget(self) -> None:
        self.assertEqual(EFFORT_LEVELS["deep"]["max_steps"], MAX_TOOL_STEPS)

    def test_step_ladder_is_1_3_5(self) -> None:
        self.assertEqual(EFFORT_LEVELS["chill"]["max_steps"], 1)
        self.assertEqual(EFFORT_LEVELS["standard"]["max_steps"], 3)
        self.assertEqual(EFFORT_LEVELS["deep"]["max_steps"], 5)

    def test_every_level_stays_a_full_agent(self) -> None:
        # the dial must never scope the toolset: all levels keep the complete
        # registry plus MCP, only the step budget and behavior note differ
        for name, cfg in EFFORT_LEVELS.items():
            self.assertGreaterEqual(cfg["max_steps"], 1, name)
            self.assertIn("label", cfg, name)


class EffortPromptNotesTest(unittest.TestCase):
    def test_every_level_has_a_note(self) -> None:
        for name, cfg in EFFORT_LEVELS.items():
            note = effort_prompt_note(name)
            self.assertTrue(note.strip(), f"missing behavior note for {name}")
            self.assertIn(cfg["label"], note)

    def test_unknown_level_yields_empty_note(self) -> None:
        self.assertEqual(effort_prompt_note("turbo"), "")

    def test_chill_note_keeps_replies_short_and_single_lookup(self) -> None:
        note = effort_prompt_note("chill")
        self.assertIn("1~3 句", note)
        self.assertIn("1 次往返", note)

    def test_same_question_contracts_visibly_differ(self) -> None:
        # 同一个问题三档的回答形态必须一眼可辨：短口语 vs 完整段落 vs 结构化交付
        self.assertIn("不列表", effort_prompt_note("chill"))
        self.assertIn("不写长篇分析", effort_prompt_note("standard"))
        self.assertIn("列要点", effort_prompt_note("deep"))


if __name__ == "__main__":
    unittest.main()
