"""Meaningful failure-path checks for the read-only task DAG validator."""
import copy
import unittest
import board


class BoardTests(unittest.TestCase):
    def setUp(self):
        self.project = {
            "status_values": ["todo", "ready", "running", "review", "done", "blocked"],
            "tasks": [{"id": "A", "milestone": "M0", "title": "audit", "assignee": "researcher", "parents": [], "status": "ready", "hypothesis": "H", "work": ["inspect"], "acceptance": ["evidence"], "artifacts": ["a.json"]}],
        }

    def test_valid(self):
        self.assertEqual(board.validate(self.project), [])
        self.assertEqual([t["id"] for t in board.available(self.project)], ["A"])

    def test_missing_id(self):
        del self.project["tasks"][0]["id"]
        self.assertTrue(board.validate(self.project))

    def test_unknown_parent_no_crash(self):
        self.project["tasks"][0]["parents"] = ["missing"]
        self.assertTrue(any("unknown parent" in e for e in board.validate(self.project)))

    def test_duplicate(self):
        self.project["tasks"].append(copy.deepcopy(self.project["tasks"][0]))
        self.assertIn("duplicate task id", board.validate(self.project))

    def test_cycle(self):
        self.project["tasks"][0]["parents"] = ["A"]
        self.project["tasks"][0]["status"] = "todo"
        self.assertTrue(any("cycle" in e for e in board.validate(self.project)))

    def test_parent_gate(self):
        child = copy.deepcopy(self.project["tasks"][0])
        child.update(id="B", parents=["A"], status="ready")
        self.project["tasks"].append(child)
        self.assertTrue(any("unfinished parents" in e for e in board.validate(self.project)))
        self.assertEqual([t["id"] for t in board.available(self.project)], ["A"])

    def test_remote_placeholder(self):
        child = copy.deepcopy(self.project["tasks"][0])
        child.update(id="B", parents=["A"], status="todo")
        self.project["tasks"].append(child)
        self.assertEqual(board.export_plan(self.project)[1]["arguments"]["parents"], ["<HERMES_ID_FOR_A>"])

    def test_completed_failed_experiment_does_not_release_success_branch(self):
        self.project["tasks"][0].update(status="done", gate_result="fail")
        child = copy.deepcopy(self.project["tasks"][0])
        child.update(id="B", parents=["A"], requires_pass=["A"], status="todo", gate_result="not_evaluated")
        self.project["tasks"].append(child)
        self.assertEqual(board.validate(self.project), [])
        self.assertEqual(board.available(self.project), [])
        child["status"] = "ready"
        self.assertTrue(any("requires passed gates" in e for e in board.validate(self.project)))

    def test_passed_parent_releases_success_branch(self):
        self.project["tasks"][0].update(status="done", gate_result="pass")
        child = copy.deepcopy(self.project["tasks"][0])
        child.update(id="B", parents=["A"], requires_pass=["A"], status="todo", gate_result="not_evaluated")
        self.project["tasks"].append(child)
        self.assertEqual(board.validate(self.project), [])
        self.assertEqual([t["id"] for t in board.available(self.project)], ["B"])

    def test_decision_task_can_review_failed_experiment(self):
        self.project["tasks"][0].update(status="done", gate_result="fail")
        child = copy.deepcopy(self.project["tasks"][0])
        child.update(id="B", parents=["A"], status="ready", gate_result="not_evaluated")
        self.project["tasks"].append(child)
        self.assertEqual(board.validate(self.project), [])
        self.assertEqual([t["id"] for t in board.available(self.project)], ["B"])

    def test_required_gate_must_be_a_parent(self):
        self.project["tasks"][0]["requires_pass"] = ["missing"]
        self.assertTrue(any("subset of parents" in e for e in board.validate(self.project)))


if __name__ == "__main__":
    unittest.main()
