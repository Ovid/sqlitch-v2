---
description: Used when the "context slop" starts kicking in and you don't want to end the current session.
---

The user input can be provided directly by the agent or as a command argument - you **MUST** consider it before proceeding with the prompt (if not empty).

User input:

$ARGUMENTS

1. Run `.specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks` from repo root and parse FEATURE_DIR and AVAILABLE_DOCS list. All paths must be absolute.


2. Load and analyze the implementation context:
    - **REQUIRED**: Read constitution.md for full understanding of what you are and are not allowed to do.
    - **REQUIRED**: Read plan.md for tech stack, architecture, and file structure.
    - **IF EXISTS**: Read data-model.md for entities and relationships.
    - **IF EXISTS**: Read contracts/ for API specifications.
    - **IF EXISTS**: Read research.md for technical decisions and constraints.
    - **IF EXISTS**: Read quickstart.md for integration scenarios.

3. Tell the user you have refreshed your understanding.
