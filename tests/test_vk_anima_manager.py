import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "vk_anima_manager.py"
SPEC = importlib.util.spec_from_file_location("vk_anima_manager", MODULE_PATH)
manager = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(manager)


class VKAnimaManagerTests(unittest.TestCase):
    def test_content_plan_is_valid_and_unique(self):
        plan = json.loads(
            (ROOT / "operations" / "vk-anima-tactus" / "content-plan.json").read_text(encoding="utf-8")
        )
        manager.validate_plan(plan)
        ids = [item["id"] for item in plan["posts"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertGreaterEqual(len(ids), 12)
        self.assertEqual(sum(bool(item.get("pin")) for item in plan["posts"]), 1)

    def test_message_navigation_is_intentional(self):
        self.assertIn("ЧУВСТВА", manager.reply_for("СТАРТ"))
        self.assertIn("тремя короткими строками", manager.reply_for(" чувства "))
        self.assertIn("экстренную службу", manager.reply_for("ПАУЗА"))
        self.assertIsNone(manager.reply_for("случайный текст"))

    def test_random_id_is_stable_and_positive(self):
        first = manager.stable_random_id(123, 456)
        self.assertEqual(first, manager.stable_random_id(123, 456))
        self.assertGreater(first, 0)
        self.assertLessEqual(first, 0x7FFFFFFF)

    def test_destructive_methods_are_blocked(self):
        expected = {
            "wall.delete",
            "video.delete",
            "photos.delete",
            "board.deleteTopic",
            "market.delete",
            "docs.delete",
            "groups.removeUser",
            "groups.leave",
        }
        self.assertTrue(expected.issubset(manager.DESTRUCTIVE_METHODS))
        source = MODULE_PATH.read_text(encoding="utf-8")
        for method in expected:
            self.assertNotIn(f'call("{method}"', source)
            self.assertNotIn(f"call('{method}'", source)

    def test_no_personal_data_output_fields(self):
        source = MODULE_PATH.read_text(encoding="utf-8")
        self.assertNotIn("peer_id\":", source)
        self.assertNotIn("message_text", source)
        self.assertIn("member_or_message_data_persisted", source)


if __name__ == "__main__":
    unittest.main()
