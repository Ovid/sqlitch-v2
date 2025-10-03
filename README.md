# SQLitch (Python Parity Fork)

> **Alpha software. Expect breaking changes.**
>
> This repository hosts the in-progress Python rewrite of Sqitch. The interfaces,
> registry schema bindings, and CLI surface are still under active development.
> Nothing here should be used in production environments yet.

## What is SQLitch?

SQLitch aims to deliver drop-in compatibility with the original Sqitch
Perl tooling while adopting a modern Python 3.11 stack. The end goal is to match
Sqitch command behavior, plan semantics, and registry schemas so existing teams
can migrate gradually without rewriting their workflows.

Key characteristics:

- Python 3.11 runtime with Click-based CLI scaffolding (under construction).
- Registry, plan, and configuration layers ported from Sqitch specs.
- Extensive parity test suites comparing SQLitch output to upstream Sqitch
  fixtures (many still skipped until the corresponding features land).
- Docker-based regression harness for MySQL and PostgreSQL parity once engines
  are implemented.

## Project Status

- ✅ Core domain models: plan parsing, configuration loader/resolver, registry state.
- ✅ Registry migrations mirror Sqitch SQL for SQLite, MySQL, and PostgreSQL.
- 🚧 Engine adapters, CLI commands, and Docker orchestration are **not** ready.
- 🚧 Most integration tests remain skipped by design until their tasks are complete.

Follow the task tracker in `specs/001-we-re-going/tasks.md` for day-to-day
progress across milestones.

## Getting Started

> 💡 Until command handlers and engines are wired up, SQLitch is primarily a
> domain-library and research sandbox. Expect many CLI commands to be stubs.

### Prerequisites

- Python 3.11
- (Optional) Docker, for future cross-engine parity tests

### Local Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

### Running the Test Suite

Tests enforce ≥90% coverage and fail when skip guards are violated.

```bash
source .venv/bin/activate
python -m pytest
```

### Code Quality Gates

This project mirrors Sqitch’s zero-warning philosophy. Lint and type gates live
in `tox.ini`, and additional enforcement scripts are in `scripts/`.

```bash
source .venv/bin/activate
python -m tox
```

> Note: Some tox environments currently skip work-in-progress parity tests,
> as documented in the spec. Remove skips only when the corresponding feature
> is under active development.

## Repository Layout

- `sqlitch/` – Python package containing domain models and (future) engine/CLI code.
- `tests/` – pytest suites, including parity fixtures and tooling checks.
- `specs/` – design documents, contracts, and milestone tracker.
- `sqitch/` – vendored upstream Sqitch code used for parity validation.
- `scripts/` – developer tooling, CI helpers, and Docker harness.

## Contributing

We welcome issue reports and design feedback, but feature contributions are
limited while the MVP spec is still evolving. If you’d like to help, start by
reviewing:

- `CONTRIBUTING.md`
- `specs/001-we-re-going/quickstart.md`
- `specs/001-we-re-going/data-model.md`

## License

SQLitch is a community-maintained fork inspired by the original
[Sqitch](https://github.com/sqitchers/sqitch) project. Consistent with the
upstream, the code in this repository is released under the MIT License:

> The MIT License (MIT)
>
> Copyright (c) 2012-2025 David E. Wheeler, 2012-2021 iovation Inc.
>
> Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
>
> The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
>
> THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

New contributions to SQLitch are also provided under the MIT License.
