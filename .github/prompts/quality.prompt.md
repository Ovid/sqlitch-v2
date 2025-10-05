Please read this project's constitution, specs, plan, and tests to understand the project's architecture and requirements.
Then, conduct a comprehensive Python code review and identify issues in these categories:

Code Quality & Pythonic Style:

* Violations of PEP 8 and PEP 20 (Zen of Python)
* Non-idiomatic Python (e.g., not using list comprehensions, context managers, or generators where appropriate)
* Missing or improper use of type hints
* Inconsistent naming conventions

Design & Architecture:

* SOLID principle violations
* Tight coupling or missing abstractions
* Inappropriate use of inheritance vs composition
* Missing or misused design patterns for the problem domain
* Overengineered or underengineered solutions

Maintainability Issues:

* Code duplication (DRY violations)
* Magic numbers or strings that should be constants/enums
* Functions/methods that are too long or do too many things
* Poor separation of concerns
* Inconsistent error handling patterns
* Missing docstrings or inadequate documentation

AI-Generated Code Smells:

* Overly verbose or unnecessarily complex implementations
* Copy-paste patterns with slight variations
* Inconsistent coding style across files
* Placeholder comments or TODO markers
* Dead code or unused imports
* Defensive programming that doesn't match actual requirements

For each issue found, provide:

* File and line location
* Brief description of the problem
* Why it's problematic
* Severity (Critical/High/Medium/Low)

Organize findings by category and prioritize by impact on maintainability and correctness. Do not fix anything yet—this is a report only.

In addition to displaying a quick report summary, write the full report to
REPORT.md in the top-level directory. Also, create a short, one task per line
task list in REPORT-TASKS.md, in the following order:

1. Any tasks dependent on other tasks must come after the tasks they're dependent on
2. Easiest tasks
3. Hardest tasks

Each task should have a simple `[<label>]` indicating why it was sorted that way.

These files are in `.gitignore`, so do not attempt to add them to git. 

When you are finished, ask the user to review the report and ask if they would
like the specs/<branchname>/tasks.md updated from the task list in
REPORT-TASKS.md. The user is expected to edit that list, as appropriate. If
they agree to add the tasks, they should be added after completed tasks and
before pending tasks.
