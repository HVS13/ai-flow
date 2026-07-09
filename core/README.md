# Core README

`core/` is the control-plane for AI Flow.

## Purpose

This folder stores:

- role definitions
- task-type skills
- tickets
- templates
- state
- logs
- docs
- helper scripts

## Required rule

Every file in `core/` should answer one of these questions:

- What should be done?
- What happened?
- What is true now?
- What should happen next?

## Planner responsibility

- classify the request
- choose fast lane or project lane
- turn work into one clear ticket
- define acceptance criteria
- define allowed and forbidden areas
- review Builder output
- update state files

## Builder responsibility

- execute one assigned ticket only
- stay inside allowed scope
- run required checks
- return a completion report
- report risks and follow-up tickets

## Source of truth

The controlling files are:

- `WORKFLOW.md`
- `roles/PLANNER.md`
- `roles/BUILDER.md`
- `skills/*.md`
- `templates/*.md`
- `state/*.md`
- ticket files under `tickets/`
