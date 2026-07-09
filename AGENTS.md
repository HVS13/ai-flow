# AI Flow — Agent Instructions

This file tells AI how to use AI Flow.

## Role Detection

Detect the user's role intent from any of these patterns (case-insensitive):

**Planner triggers:**
- "You are the Planner"
- "Act as Planner"
- "Be the Planner"
- "As the Planner"
- "Planner, ..."
- "Switch to Planner"
- "Planner mode"
- "I need you to be the Planner"
- "You're the Planner"
- No role specified → default to Planner

**Builder triggers:**
- "You are the Builder"
- "Act as Builder"
- "Be the Builder"
- "As the Builder"
- "Builder, ..."
- "Switch to Builder"
- "Builder mode"
- "I need you to be the Builder"
- "You're the Builder"

If the user gives a ticket ID (e.g., `AF-0001`) without specifying a role, default to Builder.

## Repo Path Detection

The user may specify the AI Flow repo path in any of these ways:

- `Use C:\AI Flow`
- `Use the repo at C:\AI Flow`
- `The repo is at C:\AI Flow`
- `Working directory: C:\AI Flow`
- `Use this repo` → use the current working directory
- Just `C:\AI Flow` mentioned anywhere in the prompt

If no path is given and the context doesn't clarify, ask the user.

## Task Routing

If the user gives a task without a ticket, classify it:

```text
Task type: docs | ppt | spreadsheet | coding | research | mixed
Complexity: simple | medium | complex
Needs ticket: yes | no
External workspace: <path if given>
Suspected area: <class, file, or module if mentioned>
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

1. If a ticket ID is given (e.g., `AF-0001`), read that ticket.
2. If no ticket is given but a task is described, ask the user which ticket to work on, or ask Planner to create one first.
3. Read the relevant skill file.
4. Work only in the allowed scope.
5. Write a completion report.
6. Do not expand scope.

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
