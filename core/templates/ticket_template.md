# Ticket: AF-XXXX

Status: ready
Task type: <task-type>
Complexity: <complexity>
Owner: Builder
Project: <project-slug>
Planned workspace: workspaces/<project>/<workspace-type>/tasks/<task-slug>
Target workspace: <external-path or same as planned workspace>
Suspected area: <class, file, or module if known>
Lane: <fast|project>
Skill: core/skills/<skill-file>
Created from: core/scripts/aiflow.py
Created at: <timezone-aware ISO 8601>

## Goal

<one-sentence goal>

## Context

<what the user reported or requested>

## Allowed areas

- assigned workspace only
- source files explicitly referenced in this ticket

## Do not touch

- files outside assigned workspace unless approved
- unrelated features or refactors

## Requirements

- stay inside ticket scope
- follow relevant skill file
- record verification performed

## Non-goals

- unrelated improvements
- scope expansion without approval

## Acceptance criteria

- deliverable matches the goal
- required checks or verification completed
- builder report completed

## Verification

- outputs exist in the planned workspace
- report written and stored under core/logs/builder_runs
- any explicit checks requested by the ticket were performed

## Required Builder report

- Summary
- Files changed
- Commands or checks run
- Verification done
- Issues found
- Out-of-scope observations
- Suggested follow-up tickets
- Confidence: High | Medium | Low
