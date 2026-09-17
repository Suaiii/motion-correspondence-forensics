"""Reminder decisions are tested entirely in memory; no notifications or state writes."""
import copy
import unittest

from milestones import evaluate, next_window, parse_time, record_receipts


class MilestoneTests(unittest.TestCase):
    def setUp(self):
        task = {
            "id": "A", "milestone": "M1", "title": "data acceptance", "assignee": "researchagent",
            "parents": [], "status": "todo", "gate_result": "not_evaluated",
            "hypothesis": "H", "work": ["audit"], "acceptance": ["evidence"], "artifacts": ["report.json"],
        }
        self.project = {
            "plan_version": "test-v1", "timezone": "Asia/Shanghai",
            "status_values": ["todo", "ready", "running", "review", "done", "blocked"],
            "tasks": [task],
            "milestones": [{
                "id": "K1", "title": "foundation", "due_at": "2026-09-24T22:00:00+08:00",
                "status": "pending", "task_ids": ["A"], "owner": "researchagent",
                "next_action": "finish source audit", "reminder_days": [1, 0],
            }],
            "reminders": {"final_archive_task_id": "A"},
        }
        self.state = {"schema_version": 1, "events": {}}

    def check_at(self, day):
        return evaluate(self.project, self.state, parse_time(day + "T19:00:00+08:00"))

    def test_completed_is_quiet_and_archive_requests_pause(self):
        self.project["tasks"][0].update(status="done", gate_result="pass")
        result = self.check_at("2026-09-23")
        self.assertTrue(result["quiet"])
        self.assertTrue(result["should_pause"])

    def test_near_deadline_and_today(self):
        self.assertEqual(len(self.check_at("2026-09-23")["notifications"]), 1)
        self.assertEqual(len(self.check_at("2026-09-24")["notifications"]), 1)
        self.assertTrue(self.check_at("2026-09-22")["quiet"])

    def test_critical_has_three_day_reminder(self):
        self.project["milestones"][0]["reminder_days"] = [3, 1, 0]
        self.assertEqual(len(self.check_at("2026-09-21")["notifications"]), 1)

    def test_duplicate_is_suppressed_without_mutating_inputs(self):
        before = copy.deepcopy((self.project, self.state))
        result = self.check_at("2026-09-23")
        self.assertEqual((self.project, self.state), before)
        self.state = record_receipts(self.state, result, parse_time("2026-09-23T19:01:00+08:00"), "test-turn")
        self.assertTrue(self.check_at("2026-09-23")["quiet"])
        self.assertEqual(len(self.check_at("2026-09-24")["notifications"]), 1)

    def test_overdue_once_until_material_change(self):
        result = self.check_at("2026-09-25")
        self.assertEqual(len(result["notifications"]), 1)
        self.state = record_receipts(self.state, result, parse_time("2026-09-25T19:01:00+08:00"), "test-turn")
        self.assertTrue(self.check_at("2026-09-26")["quiet"])
        self.project["tasks"][0].update(status="blocked", blocker="new missing source metadata")
        self.assertEqual(len(self.check_at("2026-09-26")["notifications"]), 1)

    def test_deferred_is_quiet(self):
        self.project["milestones"][0]["status"] = "deferred"
        self.assertTrue(self.check_at("2026-09-25")["quiet"])

    def test_unknown_task_is_an_error_not_false_completion(self):
        self.project["milestones"][0]["task_ids"] = ["missing"]
        with self.assertRaises(ValueError):
            self.check_at("2026-09-23")

    def test_utc_converts_to_shanghai_and_next_window_is_explicit(self):
        result = evaluate(self.project, self.state, parse_time("2026-09-23T11:00:00Z"))
        self.assertEqual(result["checked_at"], "2026-09-23T19:00:00+08:00")
        self.assertEqual(next_window(self.project, self.state, parse_time("2026-09-17T19:00:00+08:00")),
                         "2026-09-23T19:00:00+08:00")

    def test_multiple_due_items_are_one_result_batch(self):
        other = copy.deepcopy(self.project["milestones"][0])
        other.update(id="K2", title="second deadline")
        self.project["milestones"].append(other)
        self.assertEqual(len(self.check_at("2026-09-23")["notifications"]), 2)


if __name__ == "__main__":
    unittest.main()
