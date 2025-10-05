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
REPORT.md in the top-level directory. This file is in `.gitignore`, so do not
attempt to add it to git.

When you are finished, ask the user to review the report and ask if they would
like the specs/<branchname>/tasks.md updated. Add tasks, one-by-one, after completed tasks, but
before pending tasks. Each new task from this report should be  added after
the previous task from this report. You MUST ask the user for confirmation
prior to every task. They should be allowed to skip adding that task.
