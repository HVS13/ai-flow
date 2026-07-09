# Task Router

This file classifies user requests into AI Flow workflow actions.

## Detection Rules

### Role Detection

| User says | Role |
|---|---|
| "You are the Planner" | Planner |
| "You are the Builder" | Builder |
| No role specified | Planner (default) |

### Task Type Detection

| Keywords | Task type |
|---|---|
| bug, error, fix, crash, exception, stacktrace, "not working", "tampil error" | coding |
| summarize, write, document, SOP, guide, report | docs |
| slides, deck, presentation, pitch | ppt |
| Excel, CSV, data, spreadsheet, reconcile | spreadsheet |
| analyze, compare, research, investigate, evaluate | research |
| multiple types combined | mixed |

### Complexity Detection

| Signal | Complexity |
|---|---|
| Single file, small change, one question | simple |
| Multiple files, investigation needed, medium scope | medium |
| Large scope, multi-step, cross-system, uncertain root cause | complex |

### External Workspace Detection

If the user mentions a path like:
- `C:\Project\NMU`
- `D:\Work\MyApp`
- `/home/user/project`

Treat it as the target project workspace. Record it in the ticket as:
```text
Target workspace: <path>
```

### Suspected Area Detection

If the user mentions:
- a class name (e.g., `PreAccounting`)
- a file name (e.g., `InventoryService.java`)
- a module or feature (e.g., "Issue Inventory save")

Record it in the ticket as:
```text
Suspected area: <name>
```

## Planner Actions

After classification:

1. If task is `coding` + bug/error → create investigation ticket
2. If task is `coding` + feature → create implementation ticket
3. If task is `docs` → create documentation ticket
4. If task is `ppt` → create presentation ticket
5. If task is `spreadsheet` → create data ticket
6. If task is `research` → create analysis ticket
7. If task is `mixed` → split into multiple tickets or ask user

## Ticket Output Format

For bug investigation tickets:

```text
# Ticket: AF-XXXX

Status: ready
Task type: coding
Complexity: medium
Owner: Builder
Target workspace: <external path>
Suspected area: <class or file>
Allowed areas:
- <suspected file paths>
- directly related files
Do not touch:
- unrelated files
- production config unless investigation requires
```

## Prompt Examples

### User says:
```text
You are the Planner. Use C:\AI Flow.
Pada saat save transaksi Issue Inventory bagian Line, tampil error kalau preposting already exist.
Workspace: C:\Project\NMU, especially the PreAccounting Java class.
```

### Router infers:
```text
Role: Planner
Task type: coding
Complexity: medium
Lane: project
Target workspace: C:\Project\NMU
Suspected area: PreAccounting Java class
Action: create investigation ticket
```

### Ticket created:
```text
AF-0001_2026-07-09_investigate-issue-inventory-preposting-error.md
```
