# AI Flow

AI Flow is a Planner/Builder workflow control-plane.

```text
AI Flow root/
  core\                # central instructions, templates, tickets, logs, state
  workspaces\          # execution area by task type
```

## Workflow model

```text
Planner decides.
Builder executes.
Files remember.
```

## Folder roles

- `core`: source of truth for rules, templates, tickets, logs, state, and docs.
- `workspaces`: execution area by task type (`docs`, `ppt`, `spreadsheets`, `code`, `research`).
- `core\tickets`: the workflow queue.
- `core\state`: current project memory.
- `core\logs`: evidence of what happened.

## Two lanes

### Fast lane
Simple tasks.

```text
User request -> Builder execution -> report -> done
```

### Project lane
Complex tasks.

```text
User request -> Planner plan -> ticket -> Builder execution -> review -> approval -> next ticket
```

## Commands

Run from the repo root:

```bash
python core\scripts\aiflow.py usage
python core\scripts\aiflow.py demo
python core\scripts\aiflow.py plan "Create pitch deck from business summary" --type ppt --complexity medium
python core\scripts\aiflow.py new "Create cover slide" --type ppt --complexity simple
python core\scripts\aiflow.py list
python core\scripts\aiflow.py list --status ready
python core\scripts\aiflow.py move AF-0001 active
python core\scripts\aiflow.py report AF-0001
python core\scripts\aiflow.py review AF-0001
python core\scripts\aiflow.py workspace AF-0001
python core\scripts\aiflow.py workspace AF-0001 --task-type ppt
python core\scripts\aiflow.py route code
```

## Planner principle

Every ticket should answer:

```text
What should be done?
What must not change?
What proves it is done?
What report should Builder return?
```

## Builder principle

Do only one ticket.
Do not expand scope.
Return evidence.
