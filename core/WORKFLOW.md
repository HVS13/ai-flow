# AI Flow Workflow

`core/` is the control-plane root.

## Directory map

```text
AI Flow root/
  core/
    roles/
    skills/
    templates/
    state/
    logs/
      builder_runs/
      planner_reviews/
      incidents/
    scripts/
    docs/
  workspaces/
    <project-slug>/
      <workspace-type>/
        tasks/
          <task-slug>/
            tickets/
              inbox/
              ready/
              active/
              review/
              done/
              rejected/
```

## Core loop

1. User request enters the system.
2. Planner classifies task type and complexity.
3. Planner chooses fast lane or project lane.
4. If project lane, Planner creates one ticket.
5. Builder executes only that ticket.
6. Builder writes a completion report.
7. Planner reviews against acceptance criteria.
8. Human approves, rejects, or asks for fixes.
9. Planner updates state.
10. Next ticket starts.

Planner is the default Reviewer unless a separate Reviewer role is explicitly assigned.

## Ticket state machine

```text
inbox -> ready -> active -> review -> done
                              \-> rejected
```

## Work rules

- `core` is the single source of truth.
- `workspaces` are the execution areas, organized by project and task type.
- Tickets define allowed scope.
- Workspace creation should match the ticket, not the other way around.
- Logs are evidence, not decoration.
- State files are shared memory.
- Simple work can skip Planner.
- Complex work must not skip review.

## Fast lane rules

Use for:

- rewrite a document
- summarize a file
- check one spreadsheet issue
- create a small outline
- make a small code fix

```text
User -> Builder -> report -> done
```

## Project lane rules

Use for:

- app builds
- complex bug fixes
- full PPT decks
- large spreadsheet analysis
- research-heavy tasks
- multi-file documentation

```text
User -> Planner -> ticket -> Builder -> report -> Planner review -> human approval
```

## Routing rule

- docs -> `workspaces/<project>/docs/tasks/<task>/tickets/`
- ppt -> `workspaces/<project>/ppt/tasks/<task>/tickets/`
- spreadsheet -> `workspaces/<project>/spreadsheets/tasks/<task>/tickets/`
- coding -> `workspaces/<project>/code/tasks/<task>/tickets/`
- research -> `workspaces/<project>/research/tasks/<task>/tickets/`
- unknown -> `workspaces/<project>/research/tasks/<task>/tickets/`
- mixed -> split the work or create one ticket per work type
