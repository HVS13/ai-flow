# Usage Guide

Run all commands from the repo root.

## Commands

### Show usage

```bash
python core\scripts\aiflow.py usage
```

### Create a project-lane ticket

```bash
python core\scripts\aiflow.py plan "Create pitch deck from business summary" --type ppt --complexity medium
```

### Create a fast-lane ticket

```bash
python core\scripts\aiflow.py new "Summarize this document" --type docs --complexity simple
```

### Move sample/demo data into examples

```bash
python core\scripts\aiflow.py demo
```

Notes:
- `code` and `coding` are now interchangeable.
- `report` and `review` create timestamped log files.
- ticket and log timestamps are timezone-aware ISO 8601.
- `list --status bogus` now returns a validation error.

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
