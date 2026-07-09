# Spreadsheet Skill

`core/skills/spreadsheets.md`

Use this skill for Excel, CSV, data checks, summaries, analysis, and reporting.

## Planner mode

Planner should:

- define the question to answer
- define required inputs and outputs
- define validation rules
- define required checks
- define forbidden changes if source data must be preserved

## Builder mode

Builder should:

- inspect headers and data shape
- check missing values
- check duplicates
- check formatting issues
- run required calculations
- create summary or cleaned output
- write a completion report

## Recommended outputs

- cleaned dataset
- summary report
- issue list
- validation notes

## Workspace

Use:

```text
workspaces/<project>/spreadsheets/tasks/<task-slug>/
```

## Verification

- question is answered clearly
- assumptions are listed
- columns and formulas are documented
- sanity checks are applied
- results are traceable to source data
- source file protection rules are respected

## Completion report should include

- summary
- files created or changed
- checks performed
- key findings
- data risks
- suggested follow-up tickets
- confidence
