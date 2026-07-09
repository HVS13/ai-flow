# AI Flow Workflow

`core/` is the control-plane root.

## Directory map

```text
AI Flow root/
  core/
    roles/
    skills/
    tickets/
      inbox/
      ready/
      active/
      review/
      done/
      rejected/
    templates/
    state/
    logs/
      builder_runs/
      planner_reviews/
      incidents/
    scripts/
    docs/
  workspaces/
    docs/
    ppt/
    spreadsheets/
    code/
    research/
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
- `workspaces` are the only execution areas.
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

- docs -> `workspaces\docs`
- ppt -> `workspaces\ppt`
- spreadsheet -> `workspaces\spreadsheets`
- coding -> `workspaces\code`
- code -> accepted alias for `coding`
- research -> `workspaces\research`
- unknown -> `workspaces\research`
- mixed -> split the work or create one ticket per work type
