#!/usr/bin/env python3
"""Read-only milestone decisions; explicit ack records a locally emitted reminder."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import board

ROOT = Path(__file__).resolve().parent
SHANGHAI = timezone(timedelta(hours=8), name="Asia/Shanghai")


def parse_time(value: str) -> datetime:
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("Timestamp must include a UTC offset")
    return result.astimezone(SHANGHAI)


def digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def validate_schedule(project: dict) -> None:
    errors = board.validate(project)
    if errors:
        raise ValueError("; ".join(errors))
    if project.get("timezone") != "Asia/Shanghai":
        raise ValueError("This schedule requires Asia/Shanghai")
    tasks = board.index(project)
    seen = set()
    for item in project.get("milestones", []):
        if not item.get("id") or item["id"] in seen:
            raise ValueError("Missing or duplicate milestone id")
        seen.add(item["id"])
        parse_time(item["due_at"])
        if item.get("status") not in {"pending", "completed", "deferred", "cancelled"}:
            raise ValueError(f"{item['id']}: invalid milestone status")
        if not item.get("task_ids") or any(t not in tasks for t in item["task_ids"]):
            raise ValueError(f"{item['id']}: unknown or empty task_ids")
        if set(item.get("reminder_days", [])) - {0, 1, 3}:
            raise ValueError(f"{item['id']}: unsupported reminder lead")
    final_id = project.get("reminders", {}).get("final_archive_task_id")
    if final_id and final_id not in tasks:
        raise ValueError("Unknown final archive task")


def evaluate(project: dict, state: dict, at: datetime) -> dict:
    """Pure function: never mutates project/state or emits a notification."""
    validate_schedule(project)
    if at.tzinfo is None:
        raise ValueError("Evaluation time must include a UTC offset")
    at = at.astimezone(SHANGHAI)
    tasks = board.index(project)
    notifications = []
    receipts = state.get("events", {})
    for item in project["milestones"]:
        if item["status"] in {"completed", "deferred", "cancelled"}:
            continue
        remaining = [tasks[t] for t in item["task_ids"] if tasks[t]["status"] != "done"]
        if not remaining:
            continue
        due = parse_time(item["due_at"])
        days = (due.date() - at.date()).days
        if at > due:
            window = "overdue"
            reason = "首次逾期或逾期后实质变化"
        elif days in item["reminder_days"]:
            window = f"D-{days}"
            reason = "当日仍未完成" if days == 0 else f"提前{days}天"
        else:
            continue
        significant = {
            "due_at": item["due_at"],
            "owner": item["owner"],
            "next_action": item["next_action"],
            "blocker": item.get("blocker"),
            "remaining": [
                {k: t.get(k) for k in ("id", "title", "status", "gate_result", "blocker", "next_action")}
                for t in remaining
            ],
        }
        key = f"{item['id']}|{due.isoformat()}|{window}"
        fingerprint = digest(significant)
        if receipts.get(key, {}).get("fingerprint") == fingerprint:
            continue
        notifications.append({
            "milestone_id": item["id"],
            "title": item["title"],
            "due_at": due.isoformat(),
            "reason": reason,
            "owner": item["owner"],
            "missing": [{"task_id": t["id"], "title": t["title"], "status": t["status"]} for t in remaining],
            "next_action": item["next_action"],
            "receipt": {"key": key, "fingerprint": fingerprint},
        })
    final_id = project.get("reminders", {}).get("final_archive_task_id")
    return {
        "plan_version": project["plan_version"],
        "checked_at": at.isoformat(),
        "timezone": "Asia/Shanghai",
        "notifications": notifications,
        "quiet": not notifications,
        "should_pause": bool(final_id and tasks[final_id]["status"] == "done"),
    }


def next_window(project: dict, state: dict, after: datetime) -> str | None:
    candidates = set()
    for item in project["milestones"]:
        due = parse_time(item["due_at"])
        for lead in item["reminder_days"] + [-1]:
            day = due.date() - timedelta(days=lead)
            moment = datetime(day.year, day.month, day.day, 19, tzinfo=SHANGHAI)
            if moment > after:
                candidates.add(moment)
    for moment in sorted(candidates):
        if evaluate(project, state, moment)["notifications"]:
            return moment.isoformat()
    return None


def record_receipts(state: dict, result: dict, emitted_at: datetime, delivery_id: str) -> dict:
    if not delivery_id.strip() or not result.get("notifications"):
        raise ValueError("ack requires a delivery id and an actually emitted nonempty reminder")
    updated = copy.deepcopy(state)
    updated.setdefault("schema_version", 1)
    updated.setdefault("events", {})
    for item in result["notifications"]:
        receipt = item["receipt"]
        updated["events"][receipt["key"]] = {
            "fingerprint": receipt["fingerprint"],
            "milestone_id": item["milestone_id"],
            "emitted_at": emitted_at.astimezone(SHANGHAI).isoformat(),
            "delivery_id": delivery_id,
            "meaning": "local emission record; not OS push delivery confirmation",
        }
    return updated


def atomic_write(path: Path, value: dict, expected_bytes: bytes | None) -> None:
    current = path.read_bytes() if path.exists() else None
    if current != expected_bytes:
        raise RuntimeError("Reminder state changed concurrently; reread before acknowledging")
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as handle:
            temporary = Path(handle.name)
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        current = path.read_bytes() if path.exists() else None
        if current != expected_bytes:
            raise RuntimeError("Reminder state changed while preparing acknowledgement")
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["check", "ack"])
    parser.add_argument("--project", type=Path, default=ROOT / "project.json")
    parser.add_argument("--state", type=Path, default=ROOT / "reminder_state.json")
    parser.add_argument("--at", help="ISO timestamp with offset; check only")
    parser.add_argument("--receipt", type=Path, help="Saved JSON output of a check whose reminder was emitted")
    parser.add_argument("--delivery-id", help="Actual thread turn/run identifier for the emitted reminder")
    args = parser.parse_args()
    project = json.loads(args.project.read_text(encoding="utf-8"))
    state_bytes = args.state.read_bytes() if args.state.exists() else None
    state = json.loads(state_bytes) if state_bytes is not None else {"schema_version": 1, "events": {}}
    now = datetime.now(timezone.utc).astimezone(SHANGHAI)
    if args.command == "check":
        at = parse_time(args.at) if args.at else now
        result = evaluate(project, state, at)
        result["next_planned_notification_at"] = next_window(project, state, at)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    if args.at or not args.receipt or not args.delivery_id:
        parser.error("ack requires --receipt and --delivery-id; simulated --at is forbidden")
    result = json.loads(args.receipt.read_text(encoding="utf-8"))
    if result.get("plan_version") != project["plan_version"]:
        raise ValueError("Stale plan version in notification receipt")
    checked_at = parse_time(result["checked_at"])
    if checked_at > now or (now - checked_at) > timedelta(days=2):
        raise ValueError("Receipt timestamp is future or too old")
    fresh = evaluate(project, {"events": {}}, checked_at)
    valid = {(n["receipt"]["key"], n["receipt"]["fingerprint"]) for n in fresh["notifications"]}
    if any((n["receipt"]["key"], n["receipt"]["fingerprint"]) not in valid for n in result["notifications"]):
        raise ValueError("Receipt no longer matches the plan; recheck before acknowledging")
    updated = record_receipts(state, result, now, args.delivery_id)
    atomic_write(args.state, updated, state_bytes)
    print(json.dumps({"recorded": len(result["notifications"]), "state": str(args.state)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
