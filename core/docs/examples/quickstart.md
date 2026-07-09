# Quickstart

This is the fast path for using AI Flow.

## 1. Decide the lane

Simple task -> fast lane
Complex task -> project lane

## 2. Fast lane example

Use:

```bash
python core\scripts\aiflow.py new "Summarize this executive summary" --type docs --complexity simple
```

Then run:

```bash
python core\scripts\aiflow.py list --status ready
```

Let Builder execute directly.

## 3. Project lane example

Use:

```bash
python core\scripts\aiflow.py plan "Create pitch deck from business summary" --type ppt --complexity medium
```

Then:

```bash
python core\scripts\aiflow.py list --status ready
python core\scripts\aiflow.py move AF-0001 active
python core\scripts\aiflow.py report AF-0001
python core\scripts\aiflow.py move AF-0001 review
python core\scripts\aiflow.py review AF-0001
```

Note: `code` and `coding` are interchangeable.

## 4. Create the workspace from the ticket

```bash
python core\scripts\aiflow.py workspace AF-0001
```

## 5. Keep evidence

Every ticket should end with:

- files changed
- checks done
- report written
- review written
- state updates recorded
