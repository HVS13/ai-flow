# Usage Guide

Run all commands from the repo root.

## Commands

### Show usage

```bash
python core\scripts\aiflow.py usage
```

### Create a project-lane ticket

```bash
python core\scripts\aiflow.py plan "<task title>" --type <type> --complexity <complexity> --project <project>
```

### Create a fast-lane ticket

```bash
python core\scripts\aiflow.py new "<task title>" --type <type> --complexity <complexity> --project <project>
```

### Create a ticket from a raw prompt

```bash
python core\scripts\aiflow.py plan-prompt "<full user prompt>" --project <project>
python core\scripts\aiflow.py new-prompt "<full user prompt>"
```

Notes:
- `code` and `coding` are interchangeable.
- `report` and `review` create timestamped log files.
- ticket and log timestamps are timezone-aware ISO 8601.
- `list --status bogus` returns a validation error.

### List tickets

```bash
python core\scripts\aiflow.py list
python core\scripts\aiflow.py list --status ready
```

### Move a ticket

```bash
python core\scripts\aiflow.py move AF-0001 active
python core\scripts\aiflow.py move AF-0001 review
python core\scripts\aiflow.py move AF-0001 done
```

### Create a builder report from template

```bash
python core\scripts\aiflow.py report AF-0001
```

### Create a planner review from template

```bash
python core\scripts\aiflow.py review AF-0001
```

### Create a workspace folder for a ticket

```bash
python core\scripts\aiflow.py workspace AF-0001
python core\scripts\aiflow.py workspace AF-0001 --task-type ppt
```

### Route a task type

```bash
python core\scripts\aiflow.py route docs
```

### Parse a prompt (dry run)

```bash
python core\scripts\aiflow.py parse "<full user prompt>"
```

## Options

| Option | Description |
|---|---|
| `--root <path>` | Override detected AI Flow root |
| `--project <name>` | Project slug for ticket placement (default: general) |

## Ticket Storage

Tickets live under:

```text
workspaces/<project>/<workspace-type>/tasks/<task-slug>/tickets/<status>/<AF-XXXX>.md
```
