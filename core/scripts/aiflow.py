#!/usr/bin/env python3
import os
import re
import shutil
import json
from datetime import datetime, timezone
from pathlib import Path
from textwrap import dedent

VALID_STATUSES = ["inbox", "ready", "active", "review", "done", "rejected"]
VALID_COMPLEXITY = ["simple", "medium", "complex"]
VALID_LANE = ["fast", "project"]

TASK_CANONICAL = {
    "docs": "docs",
    "ppt": "ppt",
    "spreadsheet": "spreadsheet",
    "coding": "coding",
    "code": "coding",
    "research": "research",
    "mixed": "mixed",
}

TASK_TO_WORKSPACE = {
    "docs": "docs",
    "ppt": "ppt",
    "spreadsheet": "spreadsheets",
    "coding": "code",
    "mixed": "research",
}


class AiFlowError(Exception):
    pass


def find_control_root(start: Path) -> Path:
    if (start / "core" / "scripts" / "aiflow.py").exists():
        return start

    for parent in [start] + list(start.parents):
        if (parent / "core" / "scripts" / "aiflow.py").exists():
            return parent
        if (parent / ".git").exists():
            candidate = parent
            if (candidate / "core" / "scripts" / "aiflow.py").exists():
                return candidate

    return start


def resolve_root(argv: list[str]) -> Path:
    env_root = os.environ.get("AI_FLOW_ROOT")
    if env_root:
        return Path(env_root)

    for idx, arg in enumerate(argv):
        if arg == "--root" and idx + 1 < len(argv):
            return Path(argv[idx + 1])

    script_path = Path(__file__).resolve()
    candidate = script_path.parent.parent.parent
    return find_control_root(candidate)


ROOT = Path(os.environ.get("AI_FLOW_ROOT", str(Path(__file__).resolve().parent.parent.parent)))
CORE = ROOT / "core"
WORKSPACES = ROOT / "workspaces"
TICKETS = CORE / "tickets"
TEMPLATES = CORE / "templates"
STATE = CORE / "state"
LOGS = CORE / "logs"
DOCS = CORE / "docs"


def ensure_root(root: Path) -> None:
    if not (root / "core").exists() or not (root / "workspaces").exists():
        raise AiFlowError(f"Missing AI Flow scaffold under: {root}")


def canonical_task_type(task_type: str | None) -> str:
    value = (task_type or "").strip().lower()
    if not value:
        return "research"
    if value not in TASK_CANONICAL:
        raise AiFlowError(f"Unknown task type: {task_type}")
    return TASK_CANONICAL[value]


def workspace_for_task(task_type: str) -> str:
    return TASK_TO_WORKSPACE.get(task_type, "research")


def safe_slug(text: str, max_length: int = 60) -> str:
    text = text.lower().strip()
    allowed = []
    prev_dash = False
    for ch in text:
        if ch.isalnum() or ch in ["-", "."]:
            allowed.append(ch)
            prev_dash = False
        elif ch in [" ", "_", "/", "\\"]:
            if not prev_dash and allowed:
                allowed.append("-")
                prev_dash = True
    slug = "".join(allowed).strip("-")
    return slug[:max_length] if slug else "task"


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def now_stamp() -> str:
    return datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d_%H%M%S")


def parse_ticket_text(text: str) -> dict[str, str]:
    data: dict[str, str] = {"goal": "", "task_type": "", "complexity": "", "status": ""}
    lines = text.splitlines()

    for line in lines:
        stripped = line.strip()
        if stripped.lower().startswith("status:"):
            data["status"] = stripped.split(":", 1)[1].strip()
        elif stripped.lower().startswith("task type:"):
            data["task_type"] = stripped.split(":", 1)[1].strip()
        elif stripped.lower().startswith("complexity:"):
            data["complexity"] = stripped.split(":", 1)[1].strip()

    in_goal = False
    collected: list[str] = []
    for line in lines:
        if line.strip().lower() == "## goal":
            in_goal = True
            collected = []
            continue
        if in_goal:
            if line.startswith("## "):
                break
            collected.append(line)

    data["goal"] = " ".join(part.strip() for part in collected if part.strip())
    return data


def ticket_title_from_path(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    parsed = parse_ticket_text(text)
    goal = parsed["goal"]
    if goal and not goal.startswith("<"):
        return goal
    stem = path.stem
    if "_" in stem:
        return stem.split("_", 2)[-1].replace("-", " ").strip().title()
    return stem


def find_ticket_path(root: Path, ticket_id: str) -> Path | None:
    tickets_dir = root / "core" / "tickets"
    normalized = ticket_id.strip()

    for status in VALID_STATUSES:
        candidate = tickets_dir / status / f"{normalized}.md"
        if candidate.exists():
            return candidate

    candidates: list[Path] = []
    for status in VALID_STATUSES:
        candidates.extend(tickets_dir.glob(f"{status}/{normalized}*.md"))

    candidates = [
        candidate
        for candidate in candidates
        if candidate.stem == normalized or candidate.stem.startswith(f"{normalized}_")
    ]

    if len(candidates) == 1:
        return candidates[0]

    if len(candidates) > 1:
        raise AiFlowError(f"Ambiguous ticket id '{ticket_id}': {', '.join(sorted(p.stem for p in candidates))}")

    return None


def max_af_number_from_paths(paths: list[Path]) -> int:
    max_num = 0
    for path in paths:
        match = re.search(r"AF-(\d+)", path.stem)
        if match:
            max_num = max(max_num, int(match.group(1)))
    return max_num


def load_stored_ticket_number(root: Path) -> int:
    sequence_path = root / "core" / "state" / "id_sequence.json"
    if not sequence_path.exists():
        return 0
    try:
        data = json.loads(sequence_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return 0
    value = data.get("last_ticket_number", 0)
    return value if isinstance(value, int) else 0


def save_stored_ticket_number(root: Path, number: int) -> None:
    sequence_path = root / "core" / "state" / "id_sequence.json"
    sequence_path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "ticket_prefix": "AF",
        "last_ticket_number": number,
        "updated_at": now_iso(),
        "note": "AI Flow local ticket sequence. Dates/timestamps use ISO 8601.",
    }
    sequence_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def next_ticket_number(root: Path) -> int:
    tickets_dir = root / "core" / "tickets"
    logs_dir = root / "core" / "logs"
    examples_dir = root / "core" / "docs" / "examples"

    search_paths: list[Path] = []

    for status in VALID_STATUSES:
        search_paths.extend(tickets_dir.glob(f"{status}/AF-*.md"))

    for log_dir in [logs_dir / "builder_runs", logs_dir / "planner_reviews"]:
        if log_dir.exists():
            search_paths.extend(log_dir.glob("AF-*.md"))

    if examples_dir.exists():
        search_paths.extend(examples_dir.glob("AF-*.md"))
        search_paths.extend(examples_dir.glob("demo_AF-*.md"))

    highest_seen = max(max_af_number_from_paths(search_paths), load_stored_ticket_number(root))
    return highest_seen + 1


def build_ticket_id(num: int) -> str:
    return f"AF-{num:04d}"


def skill_for_task(task_type: str) -> str:
    mapping = {
        "docs": "docs.md",
        "ppt": "ppt.md",
        "spreadsheet": "spreadsheets.md",
        "coding": "coding.md",
        "research": "research.md",
        "mixed": "research.md",
    }
    return mapping.get(task_type, "research.md")


def unique_path(path: Path) -> Path:
    if not path.exists():
        return path

    stem = path.stem
    suffix = path.suffix
    parent = path.parent
    counter = 1
    while True:
        candidate = parent / f"{stem}_{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def write_ticket(root: Path, title: str, task_type: str, complexity: str, lane: str) -> Path:
    tickets_dir = root / "core" / "tickets"
    workspaces_dir = root / "workspaces"

    task_type = canonical_task_type(task_type)
    if complexity not in VALID_COMPLEXITY:
        raise AiFlowError(f"Invalid complexity: {complexity}")

    num = next_ticket_number(root)
    ticket_id = build_ticket_id(num)
    slug = safe_slug(title)
    iso_date = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d")
    filename = f"{ticket_id}_{iso_date}_{slug}.md"
    workspace_name = workspace_for_task(task_type)
    planned_workspace = f"workspaces/{workspace_name}/{ticket_id}"
    planned_workspace_path = workspaces_dir / workspace_name / ticket_id
    skill_path = f"core/skills/{skill_for_task(task_type)}"

    lines = [
        f"# Ticket: {ticket_id}",
        "",
        "Status: ready",
        f"Task type: {task_type}",
        f"Complexity: {complexity}",
        "Owner: Builder",
        f"Planned workspace: {planned_workspace}",
        f"Lane: {lane}",
        f"Skill: {skill_path}",
        "Created from: core/scripts/aiflow.py",
        f"Created at: {now_iso()}",
        "",
        "## Goal",
        "",
        title.strip(),
        "",
        "## Context",
        "",
        "Add only the facts Builder needs to execute this ticket.",
        "",
        "## Allowed areas",
        "",
        "- assigned workspace only",
        "- source files explicitly referenced in this ticket",
        "",
        "## Do not touch",
        "",
        "- files outside assigned workspace unless approved",
        "- unrelated features or refactors",
        "",
        "## Requirements",
        "",
        "- stay inside ticket scope",
        "- follow relevant skill file",
        "- record verification performed",
        "",
        "## Non-goals",
        "",
        "- unrelated improvements",
        "- scope expansion without approval",
        "",
        "## Acceptance criteria",
        "",
        "- deliverable matches the goal",
        "- required checks or verification completed",
        "- builder report completed",
        "",
        "## Verification",
        "",
        "- outputs exist in the planned workspace",
        "- report written and stored under core/logs/builder_runs",
        "- any explicit checks requested by the ticket were performed",
        "",
        "## Required Builder report",
        "",
        "- Summary",
        "- Files changed",
        "- Commands or checks run",
        "- Verification done",
        "- Issues found",
        "- Out-of-scope observations",
        "- Suggested follow-up tickets",
        "- Confidence: High | Medium | Low",
    ]

    out_path = tickets_dir / "ready" / filename
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    planned_workspace_path.mkdir(parents=True, exist_ok=True)
    save_stored_ticket_number(root, num)
    return out_path


def set_front_status(path: Path, status: str) -> None:
    lines = path.read_text(encoding="utf-8").splitlines()
    out = []
    for line in lines:
        if line.lower().startswith("status:"):
            out.append(f"Status: {status}")
        else:
            out.append(line)
    path.write_text("\n".join(out) + "\n", encoding="utf-8")


def list_tickets(root: Path, status_filter: str | None = None) -> str:
    tickets_dir = root / "core" / "tickets"
    normalized_status = (status_filter or "").strip().lower() or None
    if normalized_status and normalized_status not in VALID_STATUSES:
        raise AiFlowError(f"Invalid status: {status_filter}")

    rows = []
    for status in VALID_STATUSES:
        if normalized_status and status != normalized_status:
            continue
        for path in sorted(tickets_dir.glob(f"{status}/*.md")):
            title = ticket_title_from_path(path)
            rows.append(f"{path.stem}\t{status}\t{title}")
    if not rows:
        return "No tickets found."
    return "\n".join(["ticket_id\tstatus\ttitle"] + rows)


def move_ticket(root: Path, ticket_id: str, new_status: str) -> str:
    tickets_dir = root / "core" / "tickets"
    if new_status not in VALID_STATUSES:
        raise AiFlowError(f"Invalid status: {new_status}")
    path = find_ticket_path(root, ticket_id)
    if path is None:
        raise AiFlowError(f"Ticket not found: {ticket_id}")
    current_status = path.parent.name
    if current_status == new_status:
        return f"{path.stem} already in {new_status}."
    dest_dir = tickets_dir / new_status
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / path.name
    if dest_path.exists():
        raise AiFlowError(f"Destination ticket already exists: {dest_path}")
    path.rename(dest_path)
    set_front_status(dest_path, new_status)
    return f"Moved {path.stem}: {current_status} -> {new_status}"


def write_builder_report(root: Path, ticket_id: str) -> Path:
    path = find_ticket_path(root, ticket_id)
    if path is None:
        raise AiFlowError(f"Ticket not found: {ticket_id}")

    parsed = parse_ticket_text(path.read_text(encoding="utf-8"))
    ticket_stem = path.stem
    goal = parsed["goal"] or ticket_stem
    task_type = parsed["task_type"] or "unknown"
    workspace_value = ""
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip().lower().startswith("planned workspace:"):
            workspace_value = line.split(":", 1)[1].strip()
            break

    report_dir = root / "core" / "logs" / "builder_runs"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = unique_path(report_dir / f"{ticket_stem}_builder_report_{now_stamp()}.md")

    lines = [
        "# Builder Report",
        "",
        f"Ticket: {ticket_stem}",
        f"Goal: {goal}",
        f"Date: {now_iso()}",
        f"Task type: {task_type}",
        f"Workspace: {workspace_value}",
        "",
        "## Summary",
        "",
        "Describe what was actually done.",
        "",
        "## Files changed",
        "",
        "- file path or area",
        "",
        "## Commands or checks run",
        "",
        "- command or check",
        "",
        "## Result",
        "",
        "Pass | Partial | Failed",
        "",
        "## Verification",
        "",
        "- verification performed",
        "",
        "## Issues found",
        "",
        "- issue or None",
        "",
        "## Out-of-scope observations",
        "",
        "- observation or None",
        "",
        "## Suggested follow-up tickets",
        "",
        "- follow-up suggestion",
        "",
        "## Confidence",
        "",
        "High | Medium | Low",
    ]

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report_path


def write_review(root: Path, ticket_id: str) -> Path:
    path = find_ticket_path(root, ticket_id)
    if path is None:
        raise AiFlowError(f"Ticket not found: {ticket_id}")

    parsed = parse_ticket_text(path.read_text(encoding="utf-8"))
    ticket_stem = path.stem
    goal = parsed["goal"] or ticket_stem

    review_dir = root / "core" / "logs" / "planner_reviews"
    review_dir.mkdir(parents=True, exist_ok=True)
    review_path = unique_path(review_dir / f"{ticket_stem}_planner_review_{now_stamp()}.md")

    lines = [
        "# Planner Review",
        "",
        f"Ticket: {ticket_stem}",
        f"Goal: {goal}",
        f"Date: {now_iso()}",
        "Decision: Approved | Needs Fix | Rejected",
        "",
        "## Acceptance criteria check",
        "",
        "- criterion: Met | Not met",
        "",
        "## Evidence check",
        "",
        "- Report complete: Yes | No",
        "- Files changed match scope: Yes | No",
        "- Verification performed: Yes | No",
        "",
        "## Problems",
        "",
        "- problem or None",
        "",
        "## Required fixes",
        "",
        "- fix or None",
        "",
        "## Follow-up tickets",
        "",
        "- follow-up suggestion",
        "",
        "## State updates",
        "",
        "- state file and update required",
    ]

    review_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return review_path


def create_workspace_for_ticket(root: Path, ticket_id: str, expected_task_type: str | None = None) -> tuple[Path, str]:
    path = find_ticket_path(root, ticket_id)
    if path is None:
        raise AiFlowError(f"Ticket not found: {ticket_id}")

    parsed = parse_ticket_text(path.read_text(encoding="utf-8"))
    task_type = canonical_task_type(parsed["task_type"])
    if expected_task_type is not None:
        expected_canonical = canonical_task_type(expected_task_type)
        if expected_canonical != task_type:
            raise AiFlowError(f"Ticket {path.stem} is {task_type}, not {expected_canonical}.")

    workspace_value = ""
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip().lower().startswith("planned workspace:"):
            workspace_value = line.split(":", 1)[1].strip()
            break

    if workspace_value:
        workspace_root = Path(workspace_value)
        if not workspace_root.is_absolute():
            workspace_root = root / workspace_root
    else:
        workspace_root = root / "workspaces" / workspace_for_task(task_type) / path.stem

    workspace_root.mkdir(parents=True, exist_ok=True)
    notes = workspace_root / "notes.md"
    if not notes.exists():
        notes.write_text(f"# Notes for {path.stem}\n\nUse this file as workspace scratch notes.\n", encoding="utf-8")

    return workspace_root, task_type


def route_task(task_type: str) -> str:
    task_type = canonical_task_type(task_type)
    skill = f"core/skills/{skill_for_task(task_type)}"
    workspace = f"workspaces/{workspace_for_task(task_type)}"
    return f"Task type: {task_type}\nSkill: {skill}\nWorkspace: {workspace}\nFast lane: small single-pass tasks\nProject lane: ticketed tasks with review"


def move_if_exists(source: Path, destination: Path) -> Path | None:
    if not source.exists():
        return None
    destination.parent.mkdir(parents=True, exist_ok=True)
    final_destination = unique_path(destination)
    shutil.move(str(source), str(final_destination))
    return final_destination


def delete_if_exists(path: Path) -> bool:
    if path.is_dir():
        shutil.rmtree(path)
        return True
    if path.exists():
        path.unlink()
        return True
    return False


def add_demo_tickets(root: Path) -> None:
    tickets_dir = root / "core" / "tickets"
    logs_dir = root / "core" / "logs"
    workspaces_dir = root / "workspaces"
    examples_dir = root / "core" / "docs" / "examples"
    examples_dir.mkdir(parents=True, exist_ok=True)

    workspace_ticket_ids = set()
    for status in VALID_STATUSES:
        for path in tickets_dir.glob(f"{status}/AF-*.md"):
            workspace_ticket_ids.add(path.stem)

    moved: list[str] = []

    for status in VALID_STATUSES:
        for path in sorted(tickets_dir.glob(f"{status}/*.md")):
            target = examples_dir / f"demo_{path.name}"
            final = move_if_exists(path, target)
            if final is not None:
                moved.append(str(final))

    for log_type in ["builder_runs", "planner_reviews"]:
        log_dir = logs_dir / log_type
        if log_dir.exists():
            for path in sorted(log_dir.glob("*.md")):
                target = examples_dir / f"demo_{path.name}"
                final = move_if_exists(path, target)
                if final is not None:
                    moved.append(str(final))

    for workspace_type_dir in workspaces_dir.iterdir():
        if not workspace_type_dir.is_dir():
            continue
        for workspace_dir in workspace_type_dir.iterdir():
            if not workspace_dir.is_dir():
                continue
            if workspace_dir.name not in workspace_ticket_ids:
                delete_if_exists(workspace_dir)

    cache_dir = root / "core" / "scripts" / "__pycache__"
    if cache_dir.exists():
        delete_if_exists(cache_dir)

    if not moved:
        print("No demo items moved.")
        return

    print("Moved demo items:")
    for item in moved:
        print(f"- {item}")


def usage() -> str:
    return dedent("""\
    AI Flow CLI

    Commands:
      usage
      demo
      plan "title" --type <type> --complexity <complexity>
      new "title" --type <type> --complexity <complexity>
      list [--status <status>]
      move <ticket-id> <status>
      report <ticket-id>
      review <ticket-id>
      workspace <ticket-id> [--task-type <type>]
      route <task-type>

    Options:
      --root <path>     override detected AI Flow root

    Env:
      AI_FLOW_ROOT      override detected AI Flow root

    Ticket conventions:
      - ticket id: AF-0001, AF-0002, ...
      - ticket filenames: AF-0001_YYYY-MM-DD_slug.md
      - created at: timezone-aware ISO 8601 timestamp
      - report/review filenames include ISO date/time stamp
      - ticket IDs are globally unique across tickets, logs, and examples
    """)


def parse_args(argv: list[str]) -> dict:
    positional: list[str] = []
    options: dict[str, str] = {}

    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--root" and i + 1 < len(argv):
            options["root"] = argv[i + 1]
            i += 2
        elif arg.startswith("--") and i + 1 < len(argv):
            options[arg[2:]] = argv[i + 1]
            i += 2
        else:
            positional.append(arg)
            i += 1

    return {"command": positional[0] if positional else "usage", "positional": positional, "options": options}


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        import sys
        argv = sys.argv[1:]

    try:
        args = parse_args(argv)
        root = resolve_root(argv)
        global ROOT, CORE, WORKSPACES, TICKETS, TEMPLATES, STATE, LOGS, DOCS
        ROOT = root
        CORE = ROOT / "core"
        WORKSPACES = ROOT / "workspaces"
        TICKETS = CORE / "tickets"
        TEMPLATES = CORE / "templates"
        STATE = CORE / "state"
        LOGS = CORE / "logs"
        DOCS = CORE / "docs"

        ensure_root(root)
        command = args.get("command", "usage")
        options = args.get("options", {})

        if command == "usage":
            print(usage())
            return 0

        if command == "demo":
            add_demo_tickets(root)
            return 0

        if command in {"plan", "new"}:
            positional = args.get("positional", [])
            if len(positional) < 2:
                raise AiFlowError("Title is required.")
            title = positional[1]
            task_type = canonical_task_type(options.get("type"))
            complexity = options.get("complexity", "medium")
            lane = "project" if command == "plan" else "fast"
            path = write_ticket(root, title, task_type, complexity, lane)
            print(f"Created ticket: {path}")
            return 0

        if command == "list":
            print(list_tickets(root, options.get("status")))
            return 0

        if command == "move":
            positional = args.get("positional", [])
            if len(positional) < 3:
                raise AiFlowError("Usage: move <ticket-id> <status>")
            ticket_id, new_status = positional[1], positional[2]
            print(move_ticket(root, ticket_id, new_status))
            return 0

        if command == "report":
            positional = args.get("positional", [])
            if len(positional) < 2:
                raise AiFlowError("Usage: report <ticket-id>")
            path = write_builder_report(root, positional[1])
            print(f"Created report: {path}")
            return 0

        if command == "review":
            positional = args.get("positional", [])
            if len(positional) < 2:
                raise AiFlowError("Usage: review <ticket-id>")
            path = write_review(root, positional[1])
            print(f"Created review: {path}")
            return 0

        if command == "workspace":
            positional = args.get("positional", [])
            if len(positional) < 2:
                raise AiFlowError("Usage: workspace <ticket-id> [--task-type <type>]")
            ticket_id = positional[1]
            expected_task_type = options.get("task-type")
            path, resolved_type = create_workspace_for_ticket(root, ticket_id, expected_task_type)
            print(f"Workspace ready: {path} ({resolved_type})")
            return 0

        if command == "route":
            positional = args.get("positional", [])
            if len(positional) < 2:
                raise AiFlowError("Usage: route <task-type>")
            print(route_task(positional[1]))
            return 0

        raise AiFlowError(f"Unknown command: {command}")

    except AiFlowError as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
