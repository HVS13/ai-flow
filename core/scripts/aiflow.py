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


def parse_prompt(prompt: str, ai_flow_root: Path | None = None) -> dict[str, str]:
    """Parse a raw user prompt into structured routing fields.

    Returns dict with keys: role, task_type, complexity, target_workspace,
    suspected_area, ticket_id, title.
    Empty string means not detected.
    """
    text = prompt.strip()
    lower = text.lower()
    result: dict[str, str] = {
        "role": "",
        "task_type": "",
        "complexity": "",
        "target_workspace": "",
        "suspected_area": "",
        "ticket_id": "",
        "title": "",
    }

    # --- Ticket ID ---
    ticket_match = re.search(r"\bAF-(\d+)\b", text, re.IGNORECASE)
    if ticket_match:
        result["ticket_id"] = f"AF-{ticket_match.group(1)}"

    # --- Role detection (case-insensitive) ---
    planner_patterns = [
        r"\byou\s+are\s+the\s+planner\b",
        r"\bact\s+as\s+planner\b",
        r"\bbe\s+the\s+planner\b",
        r"\bas\s+the\s+planner\b",
        r"\bplanner\s*[,!]",
        r"\bswitch\s+to\s+planner\b",
        r"\bplanner\s+mode\b",
        r"\bi\s+need\s+you\s+to\s+be\s+the\s+planner\b",
        r"\byou'?re\s+the\s+planner\b",
    ]
    builder_patterns = [
        r"\byou\s+are\s+the\s+builder\b",
        r"\bact\s+as\s+builder\b",
        r"\bbe\s+the\s+builder\b",
        r"\bas\s+the\s+builder\b",
        r"\bbuilder\s*[,!]",
        r"\bswitch\s+to\s+builder\b",
        r"\bbuilder\s+mode\b",
        r"\bi\s+need\s+you\s+to\s+be\s+the\s+builder\b",
        r"\byou'?re\s+the\s+builder\b",
    ]

    is_planner = any(re.search(p, lower) for p in planner_patterns)
    is_builder = any(re.search(p, lower) for p in builder_patterns)

    if is_planner and not is_builder:
        result["role"] = "planner"
    elif is_builder and not is_planner:
        result["role"] = "builder"
    elif result["ticket_id"]:
        result["role"] = "builder"  # ticket-ID shortcut
    # else: no role detected, leave empty (caller defaults to planner)

    # --- External workspace detection ---
    detected_path = ""

    # Strategy 1: Find path markers and extract path after them
    # Handles paths with spaces: "Use C:\AI Flow", "Workspace: C:\Project\NMU"
    marker_re = re.compile(
        r"(?:use|gunakan|workspace\s*:\s*|project\s+(?:is\s+)?at\s+|"
        r"the\s+code\s+is\s+in\s+|working\s+on\s+|repo\s+(?:at|di)\s+)",
        re.IGNORECASE,
    )
    for m in marker_re.finditer(text):
        after = text[m.end():]
        # Try Windows path: drive letter + colon + backslash + path chars
        wp = re.match(r"([A-Z]:\\(?:[\w][\w \\-]*[\w]|[\w]))", after, re.IGNORECASE)
        if wp:
            candidate = wp.group(1).strip()
            # Verify it's not followed by more path chars (cross-sentence bleed)
            rest = after[wp.end():]
            if not rest or rest[0] in ".,;:!?\n" or rest.startswith(" ") or rest.lower().startswith(("especially", "terutama", "look", "specifically")):
                # Skip if this is the AI Flow repo itself
                if ai_flow_root:
                    try:
                        if Path(candidate).resolve() == ai_flow_root.resolve():
                            continue
                    except Exception:
                        pass
                detected_path = candidate
                break
        # Try Unix path
        up = re.match(r"(/[\w][\w/ _-]*[\w/])", after)
        if up:
            candidate = up.group(1).strip()
            rest = after[up.end():]
            if not rest or rest[0] in ".,;:!?\n" or rest.startswith(" "):
                detected_path = candidate
                break
        # Try tilde path
        tp = re.match(r"(~/[\w][\w/ _-]*[\w/])", after)
        if tp:
            candidate = tp.group(1).strip()
            rest = after[tp.end():]
            if not rest or rest[0] in ".,;:!?\n" or rest.startswith(" "):
                detected_path = candidate
                break

    # Strategy 2: Bare path without spaces (no marker needed)
    if not detected_path:
        win_path = re.search(r"\b([A-Z]:\\[^\s,;\"']+)", text)
        unix_path = re.search(r"\b(/(?:home|var|opt|usr|mnt|tmp)/[^\s,;\"']+)", text)
        tilde_path = re.search(r"\b(~/[^\s,;\"']+)", text)
        candidate = ""
        match_obj = None
        if win_path:
            candidate = win_path.group(1).rstrip(".")
            match_obj = win_path
        elif unix_path:
            candidate = unix_path.group(1).rstrip(".")
            match_obj = unix_path
        elif tilde_path:
            candidate = tilde_path.group(1).rstrip(".")
            match_obj = tilde_path
        if candidate:
            # Skip if this is a fragment of a longer path with spaces
            # e.g., "C:\AI" from "C:\AI Flow" — next char is space+letter
            skip = False
            if match_obj:
                end_pos = match_obj.end()
                if end_pos < len(text) and text[end_pos] == " " and end_pos + 1 < len(text) and text[end_pos + 1].isalpha():
                    skip = True
            if not skip:
                # Skip if this is the AI Flow repo itself
                if ai_flow_root:
                    try:
                        if Path(candidate).resolve() != ai_flow_root.resolve():
                            detected_path = candidate
                    except Exception:
                        detected_path = candidate
                else:
                    detected_path = candidate

    if detected_path:
        result["target_workspace"] = detected_path

    # Fallback: non-path workspace references (e.g., "Workspace: inventory module")
    if not result["target_workspace"]:
        for pattern in [
            r"workspace\s*:\s*([^\n.]+?)(?:\s*[.,;]|\s*$|\s+\bespecially\b|\s+\bterutama\b)",
            r"project\s+(?:is\s+)?at\s+([^\n.]+?)(?:\s*[.,;]|\s*$|\s+\bespecially\b|\s+\bterutama\b)",
        ]:
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                candidate = m.group(1).strip().rstrip(".")
                if len(candidate) > 3 and not candidate.lower().startswith(("c:\\", "d:\\", "/home", "/var", "~/")):
                    result["target_workspace"] = candidate
                    break

    # --- Suspected area detection ---
    # CamelCase class names
    camel = re.findall(r"\b([A-Z][a-z]+(?:[A-Z][a-z]+)+)\b", text)
    if camel:
        result["suspected_area"] = camel[0]

    # File names with extensions (e.g., PreAccounting.java)
    if not result["suspected_area"]:
        file_match = re.search(r"\b(\w+\.(?:java|py|js|ts|xml|json|sql|cs|cpp|h|go|rb|php|swift|kt))\b", text, re.IGNORECASE)
        if file_match:
            result["suspected_area"] = file_match.group(1)

    # "especially the X" / "terutama X" / "specifically X"
    if not result["suspected_area"]:
        for pattern in [
            r"especially\s+(?:the\s+)?([A-Z][\w]*(?:\s+[A-Z][\w]*)*)",
            r"terutama\s+(?:class\s+)?([A-Z][\w]*(?:\s+[A-Z][\w]*)*)",
            r"specifically\s+(?:the\s+)?([A-Z][\w]*(?:\s+[A-Z][\w]*)*)",
            r"suspected\s*:\s*([^\n]+)",
        ]:
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                result["suspected_area"] = m.group(1).strip().rstrip(".")
                break

    # --- Task type detection ---
    coding_bug_kw = [
        "bug", "error", "fix", "crash", "exception", "stacktrace",
        "not working", "broken", "broke", "problem", "fails", "failed",
        "gagal", "tidak bisa", "tidak jalan", "bermasalah",
        "tampil error", "muncul error", "keluar error", "ada error",
    ]
    coding_feature_kw = ["implement", "add feature", "create function", "build", "refactor", "develop"]
    docs_kw = ["summarize", "write", "document", "sop", "guide", "report", "documentation", "buat dokumen", "tulis"]
    ppt_kw = ["slides", "deck", "presentation", "pitch", "ppt", "buat presentasi"]
    spreadsheet_kw = ["excel", "csv", "spreadsheet", "reconcile", "filter data", "buat laporan"]
    research_kw = ["analyze", "compare", "research", "evaluate", "investigate", "analisis", "bandingkan"]

    has_bug = any(kw in lower for kw in coding_bug_kw)
    has_feature = any(kw in lower for kw in coding_feature_kw)
    has_docs = any(kw in lower for kw in docs_kw)
    has_ppt = any(kw in lower for kw in ppt_kw)
    has_spreadsheet = any(kw in lower for kw in spreadsheet_kw)
    has_research = any(kw in lower for kw in research_kw)

    # Contextual "issue": check for code/save/workspace context
    has_issue = "issue" in lower
    code_context_kw = [
        "save", "load", "code", "class", "file", "java", "python",
        "script", "module", "function", ".java", ".py", ".js", ".ts", ".cs",
        "preposting", "inventory", "transaksi",
    ]
    has_code_context = any(kw in lower for kw in code_context_kw)
    has_write_context = any(kw in lower for kw in ["write", "report", "document", "summarize", "tulis", "buat"])

    # Precedence: bug beats research, issue contextual
    if has_bug:
        result["task_type"] = "coding"
    elif has_issue and has_write_context:
        result["task_type"] = "docs"
    elif has_issue and has_code_context:
        result["task_type"] = "coding"
    elif has_issue:
        result["task_type"] = "coding"  # safe default
    elif has_feature:
        result["task_type"] = "coding"
    elif has_ppt:
        result["task_type"] = "ppt"
    elif has_spreadsheet:
        result["task_type"] = "spreadsheet"
    elif has_docs:
        result["task_type"] = "docs"
    elif has_research:
        result["task_type"] = "research"

    # --- Complexity detection ---
    simple_kw = ["simple", "mudah", "small", "quick", "trivial", "one file", "single file"]
    complex_kw = ["complex", "rumit", "large", "multi-step", "cross-system", "uncertain", "many files"]

    if any(kw in lower for kw in simple_kw):
        result["complexity"] = "simple"
    elif any(kw in lower for kw in complex_kw):
        result["complexity"] = "complex"
    else:
        result["complexity"] = "medium"

    # --- Title extraction (first sentence or first 80 chars) ---
    first_line = text.split("\n")[0].strip()
    # Remove role prefix if present
    for prefix in ["you are the planner", "you are the builder", "act as planner",
                    "act as builder", "be the planner", "be the builder",
                    "as the planner", "as the builder", "planner,", "builder,"]:
        if first_line.lower().startswith(prefix):
            first_line = first_line[len(prefix):].lstrip(" ,.!:").strip()
            break
    # Remove "use <path>" prefix
    first_line = re.sub(r"^[Uu]se\s+[^.]*\.?\s*", "", first_line).strip()
    first_line = re.sub(r"^[Gg]unakan\s+[^.]*\.?\s*", "", first_line).strip()
    # Stop at workspace/project markers
    first_line = re.split(r"\s+(?:Workspace|Project|Repo)\s*:", first_line, maxsplit=1, flags=re.IGNORECASE)[0]
    # Stop at "especially" / "terutama"
    first_line = re.split(r"\s+(?:especially|terutama)\s+", first_line, maxsplit=1, flags=re.IGNORECASE)[0]
    result["title"] = first_line[:120].strip().rstrip(".,;") if first_line else text[:120]

    return result


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


def write_ticket(
    root: Path,
    title: str,
    task_type: str,
    complexity: str,
    lane: str,
    target_workspace: str = "",
    suspected_area: str = "",
) -> Path:
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
        f"Target workspace: {target_workspace or planned_workspace}",
    ]

    if suspected_area:
        lines.append(f"Suspected area: {suspected_area}")

    lines += [
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
    ]

    if suspected_area:
        lines += [
            f"- {suspected_area}",
            "- directly related files in the same module",
            "- assigned workspace",
        ]
    else:
        lines += [
            "- assigned workspace only",
            "- source files explicitly referenced in this ticket",
        ]

    lines += [
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
    ]

    if task_type == "coding" and suspected_area:
        lines += [
            "- reproduce the error first",
            "- identify root cause before proposing fix",
            "- document findings in the ticket",
        ]

    lines += [
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
    ]

    if task_type == "coding" and suspected_area:
        lines += [
            "- root cause identified",
            "- fix proposed or applied",
            "- no unrelated changes",
        ]

    lines += [
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


def bootstrap(root: Path) -> None:
    dirs = [
        root / "core" / "tickets" / "inbox",
        root / "core" / "tickets" / "ready",
        root / "core" / "tickets" / "active",
        root / "core" / "tickets" / "review",
        root / "core" / "tickets" / "done",
        root / "core" / "tickets" / "rejected",
        root / "core" / "logs" / "builder_runs",
        root / "core" / "logs" / "planner_reviews",
        root / "core" / "logs" / "incidents",
        root / "workspaces" / "docs",
        root / "workspaces" / "ppt",
        root / "workspaces" / "spreadsheets",
        root / "workspaces" / "code",
        root / "workspaces" / "research",
        root / "core" / "docs" / "examples",
    ]

    created = 0
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
        gitkeep = d / ".gitkeep"
        if not gitkeep.exists():
            gitkeep.write_text("", encoding="utf-8")
            created += 1

    sequence_path = root / "core" / "state" / "id_sequence.json"
    if not sequence_path.exists():
        save_stored_ticket_number(root, 0)
        created += 1

    print(f"Bootstrap complete. Created {created} missing items.")

    issues = doctor(root, quiet=True)
    if issues:
        print(f"Warning: {len(issues)} issue(s) found. Run 'doctor' for details.")


def doctor(root: Path, quiet: bool = False) -> list[str]:
    issues: list[str] = []

    required_files = [
        root / "AGENTS.md",
        root / "README.md",
        root / ".gitignore",
        root / "core" / "README.md",
        root / "core" / "WORKFLOW.md",
        root / "core" / "ROUTER.md",
        root / "core" / "roles" / "PLANNER.md",
        root / "core" / "roles" / "BUILDER.md",
        root / "core" / "templates" / "ticket_template.md",
        root / "core" / "templates" / "builder_report_template.md",
        root / "core" / "templates" / "planner_review_template.md",
        root / "core" / "skills" / "coding.md",
        root / "core" / "skills" / "docs.md",
        root / "core" / "skills" / "ppt.md",
        root / "core" / "skills" / "research.md",
        root / "core" / "skills" / "spreadsheets.md",
        root / "core" / "state" / "file_map.md",
        root / "core" / "state" / "id_sequence.json",
        root / "core" / "scripts" / "aiflow.py",
    ]

    required_dirs = [
        root / "core" / "tickets" / "inbox",
        root / "core" / "tickets" / "ready",
        root / "core" / "tickets" / "active",
        root / "core" / "tickets" / "review",
        root / "core" / "tickets" / "done",
        root / "core" / "tickets" / "rejected",
        root / "core" / "logs" / "builder_runs",
        root / "core" / "logs" / "planner_reviews",
        root / "core" / "logs" / "incidents",
        root / "workspaces" / "docs",
        root / "workspaces" / "ppt",
        root / "workspaces" / "spreadsheets",
        root / "workspaces" / "code",
        root / "workspaces" / "research",
        root / "core" / "docs" / "examples",
    ]

    for f in required_files:
        if not f.exists():
            issues.append(f"Missing file: {f.relative_to(root)}")

    for d in required_dirs:
        if not d.exists():
            issues.append(f"Missing directory: {d.relative_to(root)}")

    if not quiet:
        if not issues:
            print("Doctor check passed. No issues found.")
        else:
            print(f"Doctor found {len(issues)} issue(s):")
            for issue in issues:
                print(f"  - {issue}")

    return issues


def usage() -> str:
    return dedent("""\
    AI Flow CLI

    Commands:
      usage
      bootstrap
      doctor
      demo
      plan "title" --type <type> --complexity <complexity>
      new "title" --type <type> --complexity <complexity>
      plan-prompt "full user prompt"
      new-prompt "full user prompt"
      list [--status <status>]
      move <ticket-id> <status>
      report <ticket-id>
      review <ticket-id>
      workspace <ticket-id> [--task-type <type>]
      route <task-type>
      parse "full user prompt"

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

        if command == "bootstrap":
            bootstrap(root)
            return 0

        if command == "doctor":
            issues = doctor(root)
            return 1 if issues else 0

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

        if command in {"plan-prompt", "new-prompt"}:
            positional = args.get("positional", [])
            if len(positional) < 2:
                raise AiFlowError("Prompt text is required.")
            raw_prompt = positional[1]
            parsed = parse_prompt(raw_prompt, ai_flow_root=root)

            if parsed["role"] == "builder" and parsed["ticket_id"]:
                raise AiFlowError(
                    f"This looks like a Builder prompt for ticket {parsed['ticket_id']}. "
                    f"Use 'move {parsed['ticket_id']} active' to start work, or reword as a Planner request."
                )
            if parsed["role"] == "builder":
                raise AiFlowError(
                    "This looks like a Builder prompt. "
                    "Use 'plan-prompt' with a task description instead, or reword as a Planner request."
                )

            task_type = canonical_task_type(parsed["task_type"] or "research")
            complexity = parsed["complexity"] or "medium"
            lane = "project" if command == "plan-prompt" else "fast"
            title = parsed["title"] or raw_prompt[:80]
            path = write_ticket(
                root,
                title=title,
                task_type=task_type,
                complexity=complexity,
                lane=lane,
                target_workspace=parsed["target_workspace"],
                suspected_area=parsed["suspected_area"],
            )
            print(f"Created ticket: {path}")
            print(f"  Role hint: {parsed['role'] or 'planner (default)'}")
            print(f"  Task type: {task_type}")
            print(f"  Complexity: {complexity}")
            print(f"  Lane: {lane}")
            if parsed["target_workspace"]:
                print(f"  Target workspace: {parsed['target_workspace']}")
            if parsed["suspected_area"]:
                print(f"  Suspected area: {parsed['suspected_area']}")
            if parsed["ticket_id"]:
                print(f"  Ticket ID found: {parsed['ticket_id']}")
            return 0

        if command == "parse":
            positional = args.get("positional", [])
            if len(positional) < 2:
                raise AiFlowError("Prompt text is required.")
            raw_prompt = positional[1]
            parsed = parse_prompt(raw_prompt, ai_flow_root=root)
            for key, value in parsed.items():
                print(f"{key}: {value or '(not detected)'}")
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
