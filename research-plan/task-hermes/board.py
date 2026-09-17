#!/usr/bin/env python3
"""Read-only project board validator and Hermes Kanban export planner."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEFAULT_PROJECT = ROOT / "project.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def index(data: dict) -> dict[str, dict]:
    return {task["id"]: task for task in data["tasks"]}


def validate(data: dict) -> list[str]:
    errors: list[str] = []
    if not isinstance(data, dict) or not isinstance(data.get("tasks"), list):
        return ["project requires a tasks list"]
    required = {"id", "milestone", "title", "assignee", "parents", "status", "hypothesis", "work", "acceptance", "artifacts"}
    if not isinstance(data.get("status_values"), list):
        return ["project requires status_values list"]
    for task in data["tasks"]:
        if not isinstance(task, dict):
            errors.append("task must be an object")
            continue
        missing = required - set(task)
        if missing:
            errors.append(f"{task.get('id', '?')}: missing {sorted(missing)}")
        for field in ("parents", "work", "acceptance", "artifacts", "requires_pass"):
            if field in task and (not isinstance(task[field], list) or any(not isinstance(v, str) for v in task[field])):
                errors.append(f"{task.get('id', '?')}: {field} must be a list of strings")
        if not isinstance(task.get("id"), str) or not task.get("id"):
            errors.append("task id must be a nonempty string")
        if task.get("gate_result", "not_evaluated") not in {"not_evaluated", "pass", "fail", "not_applicable"}:
            errors.append(f"{task.get('id', '?')}: invalid gate_result")
        if isinstance(task.get("requires_pass", []), list) and isinstance(task.get("parents"), list):
            if any(parent not in task["parents"] for parent in task.get("requires_pass", [])):
                errors.append(f"{task.get('id', '?')}: requires_pass must be a subset of parents")
    if errors:
        return errors
    tasks = index(data)
    if len(tasks) != len(data["tasks"]):
        errors.append("duplicate task id")
    allowed = set(data["status_values"])
    for task in data["tasks"]:
        missing = {"id", "title", "parents", "status", "acceptance", "artifacts"} - set(task)
        if missing:
            errors.append(f"{task.get('id', '?')}: missing {sorted(missing)}")
        if task.get("status") not in allowed:
            errors.append(f"{task.get('id', '?')}: invalid status")
        for parent in task.get("parents", []):
            if parent not in tasks:
                errors.append(f"{task['id']}: unknown parent {parent}")
    if errors:
        return errors
    for task in data["tasks"]:
        if task["status"] in {"ready", "running", "review", "done"}:
            unfinished = [p for p in task["parents"] if tasks[p]["status"] != "done"]
            if unfinished:
                errors.append(f"{task['id']}: active/completed task has unfinished parents {unfinished}")
            failed_gates = [p for p in task.get("requires_pass", []) if tasks[p].get("gate_result") != "pass"]
            if failed_gates:
                errors.append(f"{task['id']}: active/completed task requires passed gates {failed_gates}")

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(task_id: str) -> None:
        if task_id in visiting:
            errors.append(f"cycle involving {task_id}")
            return
        if task_id in visited:
            return
        visiting.add(task_id)
        for parent in tasks[task_id].get("parents", []):
            visit(parent)
        visiting.remove(task_id)
        visited.add(task_id)

    for task_id in tasks:
        visit(task_id)
    return errors


def available(data: dict) -> list[dict]:
    tasks = index(data)
    return [
        task
        for task in data["tasks"]
        if task["status"] in {"todo", "ready"}
        and all(tasks[parent]["status"] == "done" for parent in task["parents"])
        and all(tasks[parent].get("gate_result") == "pass" for parent in task.get("requires_pass", []))
    ]


def artifact_check(task: dict) -> list[str]:
    findings = []
    for name in task["artifacts"]:
        path = ROOT / name
        if not path.is_file() or path.stat().st_size == 0:
            findings.append(f"MISSING {name}")
        else:
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            findings.append(f"OK {name} sha256={digest}")
    return findings


def export_plan(data: dict) -> list[dict]:
    """Export structured calls; parent ids remain placeholders until Hermes returns ids."""
    return [
        {
            "local_id": task["id"],
            "tool": "kanban_create",
            "arguments": {
                "title": f"[{task['milestone']}] {task['title']}",
                "assignee": task["assignee"],
                "parents": [f"<HERMES_ID_FOR_{parent}>" for parent in task["parents"]],
                "body": json.dumps(
                    {
                        "local_id": task["id"],
                        "hypothesis": task.get("hypothesis"),
                        "work": task.get("work", []),
                        "acceptance": task["acceptance"],
                        "artifacts": task["artifacts"],
                        "research_metadata": {k: task[k] for k in ("dataset_version", "split_hash", "seed", "budget", "config_hash", "checkpoint_hash", "code_revision") if k in task},
                        "local_status": task["status"],
                        "gate_result": task.get("gate_result", "not_evaluated"),
                        "requires_pass": task.get("requires_pass", []),
                        "due_at": task.get("due_at"),
                    },
                    ensure_ascii=False,
                ),
            },
        }
        for task in data["tasks"]
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["validate", "next", "artifacts", "export"])
    parser.add_argument("--task")
    parser.add_argument("--project", type=Path, default=DEFAULT_PROJECT)
    parser.add_argument("--output", type=Path, help="Write export plan to a local file; never creates remote tasks.")
    args = parser.parse_args()
    data = load(args.project)
    errors = validate(data)
    if errors:
        print("INVALID")
        print("\n".join(errors))
        return 1
    if args.command == "validate":
        print(f"VALID {len(data['tasks'])} tasks")
    elif args.command == "next":
        for task in available(data):
            print(f"{task['id']}\t{task['assignee']}\t{task['title']}")
    elif args.command == "artifacts":
        tasks = index(data)
        if not args.task or args.task not in tasks:
            parser.error("artifacts requires --task with a valid local task id")
        print("\n".join(artifact_check(tasks[args.task])))
    else:
        output = json.dumps(export_plan(data), ensure_ascii=False, indent=2)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(output + "\n", encoding="utf-8")
            print(f"Exported {len(data['tasks'])} local call-plan entries; no remote tasks created.")
        else:
            print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
