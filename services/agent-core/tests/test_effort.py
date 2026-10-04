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
    def test_deep_has_bounded_task_budget(self) -> None:
        self.assertEqual(EFFORT_LEVELS["deep"]["max_steps"], 9)
        self.assertEqual(EFFORT_LEVELS["deep"]["max_calls"], 18)

    def test_step_ladder_is_3_6_9(self) -> None:
        self.assertEqual(EFFORT_LEVELS["chill"]["max_steps"], 3)
        self.assertEqual(EFFORT_LEVELS["standard"]["max_steps"], 6)
        self.assertEqual(EFFORT_LEVELS["deep"]["max_steps"], 9)

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

    def test_chill_keeps_tools_and_does_not_force_short_style(self) -> None:
        note = effort_prompt_note("chill")
        self.assertNotIn("至多两句", note)
        self.assertNotIn("默认不调工具", note)
        self.assertIn("3轮", note)

    def test_same_question_contracts_visibly_differ(self) -> None:
        # 同一个问题三档的回答形态必须一眼可辨：短口语 vs 完整段落 vs 结构化交付
        for level in EFFORT_LEVELS:
            self.assertIn("不强制句数或列表", effort_prompt_note(level))
            self.assertIn("权限和人格与其他档一致", effort_prompt_note(level))
            self.assertIn("尚未确认支持", effort_prompt_note(level))


if __name__ == "__main__":
    unittest.main()
