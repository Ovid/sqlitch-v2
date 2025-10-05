Here’s a clean, handoff-ready prompt you can give to an AI agent to run the behavioral validation you described:

---

### 🧠 Prompt for AI Agent

You are validating **functional parity** between two Python projects:

* **sqlitch** – the new implementation (a fork written in Python).
* **sqitch** – the original reference implementation.

Your goal is to confirm that all **non-skipped tests** in `sqlitch/tests/` produce behavior consistent with what `sqitch` implements, at a high level of functionality.

---

### 🔍 Task Definition

1. **Run all tests** in the `tests/` directory of `sqlitch`, ignoring any that are skipped (`@pytest.mark.skip`, `unittest.skip`, etc.).

   * Record which tests are executed, their names, and their results.
   * Ignore performance metrics and low-level implementation details (private methods, helper utilities, etc.).

2. **For each test that passes**, identify what high-level functionality it validates.

   * Summarize the user-visible or API-level behavior being confirmed.
   * Example: “Deploying a change script with dependencies updates the registry table correctly.”

3. **Compare** this functional behavior with the corresponding behavior in the `sqitch` reference implementation (in the `sqitch/` directory).

   * Determine whether `sqlitch` replicates `sqitch`’s intended semantics.
   * Highlight any discrepancies (e.g., missing feature, altered argument handling, different exit code, missing validation).

4. **Ignore internal details**, such as:

   * Private helper functions (`_method_name`).
   * Logging verbosity or formatting differences.
   * Minor output wording variations that do not affect semantics.
   * Performance differences unless they imply functional deviation.

5. **Produce a summary report** that includes:

   * ✅ A list of all **tested behaviors** verified to match `sqitch`.
   * ⚠️ A list of **behaviors that diverge** from `sqitch`, including short notes on what differs.
   * 🚫 A list of **skipped or unimplemented** tests (optional).

6. Where possible, suggest **minimal corrective actions** to align `sqlitch`’s behavior with `sqitch`, but do not implement those actions. Allow the user to decide.

---

### 🧩 Deliverables

* A **summary table** or structured report (e.g., Markdown or JSON) with the following columns:

  | Test Name | Purpose / Behavior | Match with Sqitch | Notes / Differences |
  | --------- | ------------------ | ----------------- | ------------------- |

* A **brief natural-language summary** (2–3 paragraphs) explaining overall compatibility:

  * How close `sqlitch` is to being a drop-in replacement.
  * Which subsystems show divergence (e.g., deploy, rework, verify, plan).

---

### ⚙️ Environment Assumptions

* Python 3.11+
* `pytest` or compatible runner is available.
* `sqlitch/` and `sqitch/` directories exist in the project root.
* Both systems expose similar CLI or module-level entry points for comparison.
* External resources (e.g., databases) can be mocked or stubbed.
