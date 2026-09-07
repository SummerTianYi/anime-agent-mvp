from __future__ import annotations

import unittest

from agent_core.main import _fact_promotion_status


class PromotionPolicyTests(unittest.TestCase):
    def test_explicit_remember_forces_confirmed(self) -> None:
        self.assertEqual(
            _fact_promotion_status("用户十月要去杭州出差", "记住，我十月要去杭州出差"),
            "confirmed",
        )
        self.assertEqual(
            _fact_promotion_status("用户妹妹下个月结婚", "帮我记一下，我妹妹下个月结婚"),
            "confirmed",
        )

    def test_marker_candidate_stays_confirmed(self) -> None:
        self.assertEqual(_fact_promotion_status("用户最喜欢的颜色是蓝色", "我最喜欢蓝色"), "confirmed")

    def test_plain_event_stays_pending(self) -> None:
        self.assertEqual(_fact_promotion_status("用户侄子刚上小学", "今天家里事真多"), "pending")
