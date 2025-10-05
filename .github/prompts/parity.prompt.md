You are analyzing a Python project called **`sqlitch`**, which is a fork of **`sqitch`**, a database change management system.

Your goal is to ensure that **sqlitch** matches **sqitch** in its public-facing behavior, using **static analysis only** (no code or test execution).

---

### Objective

1. Examine the **`tests/`** directory of the `sqlitch` project.
2. Identify top-level, **public-facing commands or features** covered by the tests, such as:

   * `deploy`
   * `revert`
   * `verify`
   * `plan`
   * `config`
   * or other similar high-level user commands.
3. Ignore any tests marked as skipped (`@pytest.mark.skip`, `unittest.skip`, etc.).
4. For this initial step, do **not** perform detailed comparison or behavior analysis.

---

### Step 1: Command Discovery

List all discovered top-level commands or features, based on the organization and naming of the tests.
For each, include a short description (one line) of what functionality the tests appear to cover.

Example output:

```
Discovered Public Commands:
1. deploy — applies database change scripts and dependencies
2. revert — rolls back applied change scripts
3. verify — checks that deployed changes are valid
4. plan — manages ordered change script definitions
5. config — handles configuration settings

Please specify which commands you would like analyzed for deviations.
```

---

### Step 2: On Request — Behavioral Deviation Analysis

Once the user selects one or more commands, analyze **only those commands’ tests** to determine whether their tested behaviors in `sqlitch` differ from `sqitch`.
Perform this purely via static reasoning.

For each deviation, report in the following format:

```
Deviations Detected:

test_<name>:
  Expected (sqitch): <describe sqitch’s behavior>
  Observed (sqlitch test): <describe sqlitch’s tested behavior>
  Deviation: <concise description of difference>
```

If no deviations are found for a command, respond with:

> No behavioral deviations detected for this command.

---

### Constraints

* Do not execute any code or tests.
* Examine code and tests statically.
* Report only high-level, user-visible behavioral differences.
* Ignore internal structure, private helpers, logging, or formatting.

---

### Deliverable

Begin by listing all **top-level public commands or features** inferred from the tests, then wait for user input to specify which should be analyzed further.
Only after the user selects commands should you report deviations between `sqlitch` and `sqitch`.
