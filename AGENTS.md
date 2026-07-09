# AI Flow — Agent Instructions

This file tells AI how to use AI Flow.

## Role Detection

Detect the user's role intent from any of these patterns (case-insensitive).

**Precedence: ticket-ID shortcut wins over default Planner.**

**Ticket-ID shortcut (highest priority):**
If a ticket ID (e.g., `AF-0001`) is present but no role is specified -> default to Builder.

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
- No role specified + no ticket ID -> default to Planner

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

## Repo Path Detection

The user may specify the AI Flow repo path in any of these ways:

- `Use <path>`
- `Use the repo at <path>`
- `The repo is at <path>`
- `Working directory: <path>`
- `Use this repo` -> use the current working directory only if it contains `AGENTS.md` and `core/scripts/aiflow.py`. If not, ask the user.
- Just the path mentioned anywhere in the prompt
- Indonesian: `Gunakan <path>`, `Repo di <path>`

If no path is given and the context doesn't clarify, ask the user.

## Task Routing

If the user gives a task without a ticket, classify it. See `core/ROUTER.md` for full detection rules and precedence.

**Precedence summary:**
1. Bug/error keywords beat research keywords -> coding
2. "issue" + bug/error/save/code context -> coding. "issue" + write/report context -> docs. "issue" alone -> coding.
3. Explicit user-specified type beats inference
4. Default complexity: medium
5. Default role: Planner (unless ticket ID present)

Classification output:
```text
Task type: docs | ppt | spreadsheet | coding | research | mixed
Complexity: simple | medium | complex
Needs ticket: yes | no
External workspace: <path if given>
Suspected area: <class, file, or module if mentioned>
Project: <project slug>
```

Then follow the lane rules in `core/WORKFLOW.md`.

## Planner Behavior

When acting as Planner:

1. Read `core/ROUTER.md` to classify the task.
2. Read the relevant skill file in `core/skills/`.
   - `coding` -> `core/skills/coding.md`
   - `docs` -> `core/skills/docs.md`
   - `ppt` -> `core/skills/ppt.md`
   - `spreadsheet` -> `core/skills/spreadsheets.md`
   - `research` -> `core/skills/research.md`
   - `mixed` -> read each relevant skill
3. If the user mentions an external project path, use it as `Target workspace`.
4. If the user mentions a suspicious file or class, add it to `Allowed areas`.
5. Do not edit code unless the user explicitly asks.
6. Create a Builder-ready ticket under `workspaces/<project>/<type>/tasks/<task>/tickets/ready/`.
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

When the user gives an external path:
- Treat it as the target project workspace.
- Do not modify AI Flow's own files to fix project bugs.
- Create a ticket that scopes investigation/fix to that workspace.

## Quick Commands

```bash
python core/scripts/aiflow.py bootstrap
python core/scripts/aiflow.py doctor
python core/scripts/aiflow.py plan "task description" --type coding --complexity medium --project <project>
python core/scripts/aiflow.py plan-prompt "full user prompt" --project <project>
python core/scripts/aiflow.py new-prompt "full user prompt"
```

## Source of Truth

Always read before acting:
- `core/WORKFLOW.md` — workflow rules
- `core/ROUTER.md` — task classification and precedence
- `core/roles/PLANNER.md` or `core/roles/BUILDER.md` — role rules
- `core/skills/*.md` — task-type rules
- `core/templates/*.md` — output formats
