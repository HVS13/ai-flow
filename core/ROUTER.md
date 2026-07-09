# Task Router

This file classifies user requests into AI Flow workflow actions.

## Detection Rules

### Precedence

When multiple rules compete, apply in this order:

1. **Role shortcut**: Ticket ID present + no role → Builder (overrides default Planner)
2. **Bug beats research**: If both error/bug/fix/fail/problem keywords AND investigate/analyze keywords are present → coding, not research
3. **Contextual issue**: "issue" alone → check context:
   - paired with error/bug/fix/fail/crash/broken/problem/save/load/code/class/file/workspace → coding
   - paired with write/document/report/summarize → docs
   - no context clue → coding (safe default for this workflow)
4. **Explicit beats implicit**: User-specified task type, complexity, or workspace overrides inference
5. **Default role**: No role + no ticket ID → Planner

### Role Detection

Case-insensitive. Match any of these patterns:

**Planner triggers:**
- "you are the planner"
- "act as planner"
- "be the planner"
- "as the planner"
- "planner," (followed by comma)
- "switch to planner"
- "planner mode"
- "i need you to be the planner"
- "you're the planner"
- no role specified + no ticket ID → Planner (default)

**Builder triggers:**
- "you are the builder"
- "act as builder"
- "be the builder"
- "as the builder"
- "builder," (followed by comma)
- "switch to builder"
- "builder mode"
- "i need you to be the builder"
- "you're the builder"

**Shortcut (highest role priority):**
- If a ticket ID (e.g., `AF-0001`) is present but no role is specified → Builder

### Task Type Detection

Case-insensitive. Match keywords anywhere in the prompt.

**Coding (bug/error — takes priority over research):**
bug, error, fix, crash, exception, stacktrace, not working, broken, broke, problem, fails, failed, gagal, tidak bisa, tidak jalan, bermasalah, tampil error, muncul error, keluar error, ada error

**Coding (contextual issue):**
- "issue" + any of: error, bug, fix, fail, crash, broken, problem, save, load, code, class, file, workspace, java, python, script, module, function
- "issue" alone → coding (safe default)

**Coding (feature):**
implement, add feature, create function, build, refactor, develop

**Docs:**
summarize, write, document, SOP, guide, report, documentation, buat dokumen, tulis, known issues report, issue list

**PPT:**
slides, deck, presentation, pitch, ppt, buat presentasi

**Spreadsheet:**
Excel, CSV, data, spreadsheet, reconcile, filter data, buat laporan

**Research (only when no bug/error keywords present):**
analyze, compare, research, evaluate, analisis, bandingkan

Note: "investigate" alone → research. "investigate" + any bug/error keyword → coding.

**Mixed:**
multiple types combined

**Fallback:**
- If no keywords match but the user describes a concrete task → infer from context
- If truly ambiguous → ask the user

### Complexity Detection

| Signal | Complexity |
|---|---|
| Single file, small change, one question, "simple", "mudah" | simple |
| Multiple files, investigation needed, medium scope, default | medium |
| Large scope, multi-step, cross-system, uncertain root cause, "complex", "rumit" | complex |

If not specified → default to `medium`.

### External Workspace Detection

If the user mentions a path pattern anywhere in the prompt:
- `C:\...` or `D:\...` or `E:\...` (Windows)
- `/home/...` or `/var/...` or `/opt/...` (Linux)
- `~/...` (home directory shorthand)

And the path is NOT the AI Flow repo itself → treat as target project workspace.

Also detect these phrasings:
- "Workspace: <path>"
- "Workspace: <path>, especially the <ClassName>"
- "project is at <path>"
- "the code is in <path>"
- "working on <path>"
- "especially the <ClassName> class in <path>"
- "<path>, especially the <ClassName>"
- "gunakan <path>" (Indonesian: "use")
- "repo di <path>" (Indonesian: "repo at")

Record in ticket as:
```text
Target workspace: <path>
```

### Suspected Area Detection

If the user mentions:
- A class name (CamelCase, e.g., `PreAccounting`, `InventoryService`)
- A file name with extension (e.g., `PreAccounting.java`, `config.xml`)
- A module or feature name (e.g., "Issue Inventory save", "login flow")
- "especially the X" or "specifically X" or "terutama X"

Record in ticket as:
```text
Suspected area: <name>
```

## Planner Actions

After classification:

1. If task is `coding` + bug/error/problem/issue → create investigation ticket
2. If task is `coding` + feature request → create implementation ticket
3. If task is `docs` → create documentation ticket
4. If task is `ppt` → create presentation ticket
5. If task is `spreadsheet` → create data ticket
6. If task is `research` → create analysis ticket
7. If task is `mixed` → split into multiple tickets or ask user
8. If task is unclear → ask the user before creating a ticket

## Ticket Output Format

For bug investigation tickets:

```text
# Ticket: AF-XXXX

Status: ready
Task type: coding
Complexity: medium
Owner: Builder
Planned workspace: workspaces/code/AF-XXXX
Target workspace: <external path or same as planned workspace>
Suspected area: <class or file>
Lane: project
Skill: core/skills/coding.md
Created from: core/scripts/aiflow.py
Created at: <timezone-aware ISO 8601>

## Goal

<one-sentence goal>

## Context

<what the user reported or requested>

## Allowed areas
- <suspected file paths>
- directly related files in the same module
- assigned workspace

## Do not touch
- unrelated files
- production config unless investigation requires

## Requirements
- reproduce the error first
- identify root cause before proposing fix
- document findings in the ticket

## Non-goals
- unrelated improvements
- scope expansion without approval

## Acceptance criteria
- root cause identified
- fix proposed or applied
- no unrelated changes

## Verification
- outputs exist in the planned workspace
- report written and stored under core/logs/builder_runs
- any explicit checks requested by the ticket were performed

## Required Builder report
- Summary
- Files changed
- Commands or checks run
- Verification done
- Issues found
- Out-of-scope observations
- Suggested follow-up tickets
- Confidence: High | Medium | Low
```

## Prompt Examples

### Example 1: Original format
```text
You are the Planner. Use C:\AI Flow.
Pada saat save transaksi Issue Inventory bagian Line, tampil error kalau preposting already exist.
Workspace: C:\Project\NMU, especially the PreAccounting Java class.
```

### Example 2: Casual format
```text
Hey, act as Planner. Use the repo at C:\AI Flow.
There's a bug when saving Issue Inventory lines — it says preposting already exist.
Project is at C:\Project\NMU. Look at PreAccounting.java.
```

### Example 3: Minimal format
```text
Planner, fix this error: preposting already exist on Issue Inventory save.
C:\Project\NMU, PreAccounting class.
```

### Example 4: Indonesian mixed
```text
You are the Planner. Gunakan C:\AI Flow.
Waktu save transaksi Issue Inventory bagian Line, muncul error preposting already exist.
Workspace: C:\Project\NMU, terutama class PreAccounting.
```

### Example 5: No role specified
```text
I'm getting a preposting error when saving Issue Inventory lines.
Project: C:\Project\NMU
Suspected: PreAccounting.java
```

All of the above should produce:
```text
Role: Planner
Task type: coding
Complexity: medium
Lane: project
Target workspace: C:\Project\NMU
Suspected area: PreAccounting Java class
Action: create investigation ticket
```

### Example 6: Builder with ticket
```text
You are the Builder. Use C:\AI Flow.
Work on AF-0001.
```

→ Builder reads `core/tickets/ready/AF-0001_*.md` and executes.

### Example 7: Builder without ticket
```text
You are the Builder. Use C:\AI Flow.
```

→ Ask: "Which ticket should I work on? Please provide a ticket ID (e.g., AF-0001)."

### Example 8: investigate + error (coding, not research)
```text
Investigate the preposting error in Issue Inventory save.
```

→ Task type: coding (bug keywords override research keyword)

### Example 9: investigate alone (research)
```text
Investigate the best approach for refactoring the inventory module.
```

→ Task type: research (no bug/error keywords present)

### Example 10: "issue" with context (coding)
```text
There's an issue with PreAccounting.java when saving.
```

→ Task type: coding (issue + save + .java file)

### Example 11: "issue" in docs context (docs)
```text
Write a known issues report for the inventory module.
```

→ Task type: docs (issue + write + report)
