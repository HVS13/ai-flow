# Coding Skill

`core/skills/coding.md`

Use this skill for bug fixes, feature work, refactoring, scripts, automation, and app builds.

## Planner mode

Planner should:

- define the problem clearly
- define allowed files or modules
- define forbidden areas
- define verification steps
- define non-goals

## Builder mode

Builder should:

- read the ticket and relevant skill
- inspect the smallest relevant code area
- implement only the assigned change
- avoid unrelated refactors
- run tests or verification steps
- write a completion report

## Recommended outputs

- code change
- config change if required
- tests if requested
- short technical notes

## Workspace

Use:

```text
workspaces/<project>/code/tasks/<task-slug>/
```

## Verification

- build or run command succeeds
- tests pass if applicable
- error handling is reasonable
- security or dependency risks are noted
- unrelated files were not changed
- behavior matches ticket requirements

## Completion report should include

- summary
- files changed
- commands run
- results
- risks
- technical debt created or removed
- suggested follow-up tickets
- confidence
