# AI Flow

AI Flow is a Planner/Builder workflow control-plane for AI-assisted tasks.

```text
Planner decides.
Builder executes.
Files remember.
```

## Fresh Clone Setup

```bash
git clone https://github.com/HVS13/ai-flow.git
cd ai-flow
python core/scripts/aiflow.py bootstrap
python core/scripts/aiflow.py doctor
```

`bootstrap` creates any missing folders and files.
`doctor` validates the structure is complete.

## How to Use with AI

### Step 1: Tell the AI its role

```text
You are the Planner. Use <repo-path>.
```

or

```text
You are the Builder. Use <repo-path>.
```

The AI will read `AGENTS.md` and follow the workflow automatically.

### Step 2: Give it a task

```text
You are the Planner. Use C:\AI Flow.

<task description>

Workspace: <external-path>, especially the <ClassName> class.
```

The AI will:
1. Read `AGENTS.md` -> detect role as Planner
2. Read `core/ROUTER.md` -> classify task type
3. Read `core/roles/PLANNER.md` -> follow Planner rules
4. Read `core/skills/<skill>.md` -> apply skill
5. Create a scoped ticket under `workspaces/<project>/<type>/tasks/<task>/tickets/ready/`

## Two Lanes

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
python core/scripts/aiflow.py bootstrap          # setup after clone
python core/scripts/aiflow.py doctor              # validate structure
python core/scripts/aiflow.py usage               # show all commands
python core/scripts/aiflow.py plan "title" --type coding --complexity medium --project <project>
python core/scripts/aiflow.py new "title" --type docs --complexity simple --project <project>
python core/scripts/aiflow.py plan-prompt "full user prompt" --project <project>
python core/scripts/aiflow.py new-prompt "full user prompt"
python core/scripts/aiflow.py list
python core/scripts/aiflow.py list --status ready
python core/scripts/aiflow.py move AF-0001 active
python core/scripts/aiflow.py report AF-0001
python core/scripts/aiflow.py review AF-0001
python core/scripts/aiflow.py workspace AF-0001
python core/scripts/aiflow.py route code
python core/scripts/aiflow.py parse "full user prompt"
```

## Key Files

| File | Purpose |
|---|---|
| `AGENTS.md` | Root AI instruction file |
| `core/WORKFLOW.md` | Workflow rules |
| `core/ROUTER.md` | Task classification logic |
| `core/roles/PLANNER.md` | Planner role rules |
| `core/roles/BUILDER.md` | Builder role rules |
| `core/skills/*.md` | Task-type skill files |
| `core/templates/*.md` | Output templates |
| `core/state/id_sequence.json` | Ticket ID sequence |
| `core/scripts/aiflow.py` | CLI tool |

## Folder Structure

```text
AI Flow root/
  AGENTS.md
  README.md
  .gitignore
  core/
    WORKFLOW.md
    ROUTER.md
    README.md
    roles/
      PLANNER.md
      BUILDER.md
    skills/
      coding.md
      docs.md
      ppt.md
      research.md
      spreadsheets.md
    templates/
      ticket_template.md
      builder_report_template.md
      planner_review_template.md
    state/
      id_sequence.json
      projects.md
      decisions.md
      known_issues.md
      file_map.md
      next_steps.md
    docs/
      usage.md
    logs/
      builder_runs/
      planner_reviews/
      incidents/
    scripts/
      aiflow.py
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

## Ticket Storage

Tickets live under the workspace hierarchy:

```text
workspaces/<project>/<workspace-type>/tasks/<task-slug>/tickets/<status>/<AF-XXXX>.md
```

- `<project>`: project slug (default: `general`)
- `<workspace-type>`: `code`, `docs`, `ppt`, `spreadsheets`, `research`
- `<task-slug>`: derived from ticket title
- `<status>`: `ready`, `active`, `review`, `done`, `rejected`
