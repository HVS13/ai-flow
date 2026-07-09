# AI Flow — Agent Instructions

This file tells AI how to use AI Flow.

## Role Detection

If the user says:
- "You are the Planner" → read `core/WORKFLOW.md`, `core/roles/PLANNER.md`, then proceed
- "You are the Builder" → read `core/WORKFLOW.md`, `core/roles/BUILDER.md`, then proceed
- no role specified → default to Planner

## Task Routing

If the user gives a task without a ticket, classify it:

```text
Task type: docs | ppt | spreadsheet | coding | research | mixed
Complexity: simple | medium | complex
Needs ticket: yes | no
External workspace: <path if given>
```

Then follow the lane rules in `core/WORKFLOW.md`.

## Planner Behavior

When acting as Planner:

1. Read `core/ROUTER.md` to classify the task.
2. Read the relevant skill file in `core/skills/`.
3. If the user mentions an external project path, use it as `Target workspace`.
4. If the user mentions a suspicious file or class, add it to `Allowed areas`.
5. Do not edit code unless the user explicitly asks.
6. Create a Builder-ready ticket in `core/tickets/ready/`.
7. Report the ticket ID to the user.

## Builder Behavior

When acting as Builder:

1. Read the assigned ticket.
2. Read the relevant skill file.
3. Work only in the allowed scope.
4. Write a completion report.
5. Do not expand scope.

## External Workspaces

AI Flow manages workflow inside its own repo.
Target project code lives in a separate workspace.

When the user gives a path like `C:\Project\NMU`:
- Treat it as the target project workspace.
- Do not modify AI Flow's own files to fix project bugs.
- Create a ticket that scopes investigation/fix to that workspace.

## Quick Commands

```bash
python core/scripts/aiflow.py bootstrap
python core/scripts/aiflow.py doctor
python core/scripts/aiflow.py plan "task description" --type coding --complexity medium
```

## Source of Truth

Always read before acting:
- `core/WORKFLOW.md` — workflow rules
- `core/roles/PLANNER.md` or `core/roles/BUILDER.md` — role rules
- `core/skills/*.md` — task-type rules
- `core/templates/*.md` — output formats
