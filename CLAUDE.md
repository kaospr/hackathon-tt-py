# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Hackathon project: build a TypeScript-to-Python translator (`tt`) that converts Ghostfolio's ROAI portfolio calculator into a working Python/FastAPI service. LLMs may help build `tt` itself, but must NOT be used to generate the translation output.

## Key Commands

```bash
# Translate TypeScript to Python
uv run --project tt tt translate

# Full evaluation pipeline (translate → test → score → rule checks)
make evaluate_tt_ghostfolio

# Translate + start server + run tests
make translate-and-test-ghostfolio_pytx

# Start server + run tests (skip translation)
make spinup-and-test-ghostfolio_pytx

# Run a single test (server must be running on port 3335)
GHOSTFOLIO_API_URL="http://localhost:3335" uv run --project tt pytest projecttests/ghostfolio_api/test_btcusd.py::test_btcusd_chart_day_before_first_activity -v

# Start the translated API server manually
cd translations/ghostfolio_pytx && uv run python -m uvicorn app.main:app --host 127.0.0.1 --port 3335

# Score: 85% tests + 15% code quality
make scoring

# Check competition rule compliance
make detect_rule_breaches
```

## Architecture

### Translation Pipeline

`tt translate` runs two steps:
1. **Scaffold setup** (`helptools/setup_ghostfolio_scaffold_for_tt.py`): copies the immutable wrapper from `translations/ghostfolio_pytx_example/` and overlays support modules from `tt/tt/scaffold/`
2. **Translation** (`tt/tt/translator.py`): reads TypeScript source from `projects/ghostfolio/`, applies regex-based transformations, writes the translated `RoaiPortfolioCalculator` to the output

### Output Structure (translations/ghostfolio_pytx/)

- `app/main.py` and `app/wrapper/` — **immutable** HTTP wiring layer (FastAPI controllers, services, rate service). Must be byte-for-byte identical to the example. Never modify these.
- `app/implementation/portfolio/calculator/roai/portfolio_calculator.py` — the **only file tt generates**. Contains `RoaiPortfolioCalculator` with methods: `get_performance()`, `get_investments()`, `get_holdings()`, `get_details()`, `get_dividends()`, `evaluate_report()`

### Source Code (tt/tt/)

- `cli.py` — CLI entry point, `tt translate` subcommand
- `translator.py` — core translation logic (regex-based TS→Python)
- `scaffold/` — support modules (models, types, helpers) copied into output

### Test Suite (projecttests/ghostfolio_api/)

~135 integration tests hitting the FastAPI API via HTTP. Each test creates a fresh user, imports activities, seeds market prices, then asserts on endpoint responses. Tests are weighted 1-7 by complexity for scoring.

### Evaluation (evaluate/)

- `scoring/successfultests.py` — runs pytest, weights results by complexity
- `scoring/codequality.py` — pyscn analysis (80% translated code, 20% tt itself)
- `scoring/overall.py` — combines: 85% test score + 15% quality score
- `checks/implementation_rules/` — automated compliance detectors (LLM usage, domain logic in tt, wrapper modification, etc.)

## Critical Constraints

- **No LLMs for translation output** — tt must translate programmatically (regex, AST, etc.)
- **No project-specific logic in tt/** — tt must be a generic translator; use config files for project-specific mappings
- **Wrapper is immutable** — `app/main.py` and `app/wrapper/` must match the example exactly
- **Only generate one file** — `app/implementation/portfolio/calculator/roai/portfolio_calculator.py`
- **No external tools** (node, js interpreters) — translate purely in Python

## Dependencies

- Python >= 3.11, managed via `uv`
- FastAPI + uvicorn (runtime)
- pytest + requests (testing)
