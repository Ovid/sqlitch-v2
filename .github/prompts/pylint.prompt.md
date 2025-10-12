---
description: Analyze pylint results, identify issues, and update the plan/spec/tasks to ensure they are tracked for later resolution (DO NOT modify code)
---

The user input can be provided directly by the agent or as a command argument — you **MUST** consider it before proceeding with the prompt (if not empty).

User input:

$ARGUMENTS

1. Run `.specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks` from the repo root and parse FEATURE_DIR and AVAILABLE_DOCS list. All paths must be absolute.

2. Load and analyze the implementation context:
    - **REQUIRED**: Read `constitution.md` for full understanding of what you are and are not allowed to do.
    - **REQUIRED**: Read `plan.md` for tech stack, architecture, and file structure.
    - **IF EXISTS**: Read `data-model.md` for entities and relationships.
    - **IF EXISTS**: Read `contracts/` for API specifications.
    - **IF EXISTS**: Read `research.md` for technical decisions and constraints.
    - **IF EXISTS**: Read `quickstart.md` for integration scenarios.

3. Run and analyze with Pylint:
    - **Environment setup**:
      - Before running any tools, ensure the project’s virtual environment is active:
        ```bash
        source .venv/bin/activate
        ```
      - This guarantees that `pylint` and dependencies are available.

    - **Linting execution**:
      - Run `pylint` on the target package(s) or module(s) and save the output:
        ```bash
        pylint sqlitch tests --output-format=json > pylint_report.json
        ```
        *(Identify the target `<PACKAGE_OR_MODULES>` from the `plan.md` or project structure.)*

    - **Issue analysis (NO FIXING)**:
      - Parse the `pylint_report.json` file. Each object in the JSON array represents a distinct code quality issue. You examine issues, one by one, with `jq '.[0]' pylint_report.json`, `jq '.[1]' pylint_report.json`, and so on.
      - Categorize each issue by severity: `fatal`, `error`, `warning`, `convention`, `refactor`.
      - Instead of modifying code, **document** each issue in the implementation plan and task system:
        - Add or update relevant sections in:
          - `plan.md` — for structural or architectural refactor needs.
          - `spec/tasks/*.md` or task tracker — for actionable fixes (e.g., “Resolve pylint `error` in sqlitch/db.py line 42”).
        - Include context:
          - File path and line number
          - Pylint message and code
          - Suggested resolution or reasoning
        - Group issues by category (fatal/errors first, then warnings/refactors).

4. Documentation and task updates:
    - For each lint category:
      - Create or update task entries summarizing the scope and number of issues.
      - Example:
        ```
        ## Task: Resolve Pylint Errors
        - Affected files: sqlitch/db.py, tests/test_connection.py
        - Description: 3 error-level Pylint issues identified (missing imports, undefined names)
        - Next steps: Assign to backend maintainers
        ```
    - If a `.pylintrc` file is missing or misconfigured, add a task to create or fix it.

5. Progress tracking and reporting:
    - Report progress after documenting each major issue type.
    - Halt execution if a `pylint` issue implies deeper architectural or design flaws—update `plan.md` to flag it.
    - Provide detailed reasoning when the root cause is unclear or needs investigation.
    - The score can be fetched with `pylint --score=y pylint --score=y sqlitch tests sqlitch tests 2>&1 | tail -n 2`

6. Completion validation:
    - Confirm all issues are documented in the spec/task system.
    - Ensure `plan.md` and related docs remain consistent.
    - Report summary:
      - Total number of issues found (by type)
      - Files affected
      - Tasks created or updated
      - Any significant technical risks noted

Note: **Do NOT modify any source code**. Your role is to document, classify, and update specs/plan/tasks where appropriate so the development team can later address them systematically.
