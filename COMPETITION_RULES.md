# Competition Rules

## Project Layout

The translated project uses a **wrapper / implementation** split:

```
translations/ghostfolio_pytx/app/
├── main.py                                          # immutable wrapper
├── wrapper/                                         # immutable wrapper layer
│   └── portfolio/
│       ├── portfolio_controller.py                  # FastAPI routes
│       ├── portfolio_service.py                     # thin delegation to calculator
│       ├── current_rate_service.py                  # market price lookups
│       ├── calculator/
│       │   └── portfolio_calculator.py              # abstract calculator interface
│       └── interfaces/                              # shared dataclasses
└── implementation/                                  # tt-generated code
    └── portfolio/
        └── calculator/
            └── roai/
                └── portfolio_calculator.py           # ROAI calculator (translated)
```

**Wrapper** (`app/main.py` + `app/wrapper/`): HTTP wiring, auth, thin service delegation, abstract interfaces. Copied verbatim from `translations/ghostfolio_pytx_example/` — tt must NOT modify these files.

**Implementation** (`app/implementation/`): The actual translated financial logic. This is the only code tt generates.

## Core Rules

1. The TT must **not** use LLMs for the actual translations.
2. You **may** use LLMs to help build the TT itself.
3. You may use the unit tests to verify correctness of the translated code.
4. The team should add a half page to explain their architectural choices.
5. The TT core (`tt/`) must contain **no project-specific mappings** (e.g. no hard-coded `@ghostfolio/…` import paths). Project-specific configuration belongs in `tt_import_map.json` inside the relevant scaffold directory, passed to the translator at call time.
6. TT must not have project-specific logic which it simply copies into the translation. The translated code must be actually translated code, not pregenerated logic.
7. You may use AST libraries.
8. Your python code may not call node/js-tools or other external tools to translate the code. The translation should happen in python.

## Scaffold / Wrapper Rules

8. You are not allowed to add anything to `translations/ghostfolio_pytx_example/` before running `tt`.
9. TT must copy the wrapper layer (`app/main.py` and `app/wrapper/`) from `translations/ghostfolio_pytx_example/` into `translations/ghostfolio_pytx/` **without modification**. The wrapper files must remain byte-for-byte identical to the example.
10. TT places its translated code exclusively inside `app/implementation/`. Nothing outside that directory may be generated or modified by tt.
11. The wrapper layer provides HTTP wiring only — not domain calculations. It contains:
    - FastAPI endpoint handlers (controller)
    - Thin service delegation (empty-portfolio guards + calculator calls)
    - In-memory state management (UserState)
    - Auth helpers (`_make_tokens`, `_get_user`)
    - Abstract calculator interface
    - Market price lookup service
    - Shared interface dataclasses
12. The wrapper must **not** contain:
    - Financial arithmetic (cost-basis tracking, performance calculation, chart generation)
    - Position replay or investment grouping logic
    - Rule evaluation for portfolio reports

## What the Translated Code Must Provide

The translated calculator must implement the abstract interface defined in:
`app/wrapper/portfolio/calculator/portfolio_calculator.py`

Required methods:
- `get_performance()` → `{chart, firstOrderDate, performance: {...}}`
- `get_investments(group_by)` → `{investments: [{date, investment}]}`
- `get_holdings()` → `{holdings: {symbol: {...}}}`
- `get_details(base_currency)` → `{accounts, holdings, summary, ...}`
- `get_dividends(group_by)` → `{dividends: [{date, investment}]}`
- `evaluate_report()` → `{xRay: {categories, statistics}}`

## Automated Rule Checks

Run `make detect_rule_breaches` to verify compliance. The following checks are enforced:

| Check | What it detects |
|-------|-----------------|
| `detect_llm_usage` | LLM API imports/calls in `tt/` |
| `detect_direct_mappings` | Project-specific import paths in `tt/` core |
| `detect_explicit_implementation` | Domain logic in `tt/` (function size, domain identifiers, string comparisons) |
| `detect_explicit_financial_logic` | Financial arithmetic, variables, and nested loops in scaffold |
| `detect_scaffold_bloat` | Private helpers beyond the allowed set in scaffold `main.py` |
| `detect_code_block_copying` | 10+ line blocks from `tt/` appearing verbatim in translated output |
| `detect_interface_violation` | Calculator interface compliance |
| `detect_wrapper_modification` | Wrapper/main.py files modified from example (must be identical) |

## Judging Criteria

The TT will be judged on:

1. **Rule compliance** — the translation tool must not break the rules above.
2. **Correctness** — translated Python code passes the API tests of the reference projects, and how many of them.
3. **Python code quality**, ranked by relevance:
   1. Simplicity as Discipline
   2. Testing & Verification
   3. Elegance & Readability
   4. Iterative Delivery
   5. Humility & Scope Limits
   6. Long-term Sustainability
   7. Data Structures First
   8. Customer-First Thinking
   9. Avoid Duplication (DRY)
   10. Understand the Metal
4. **Understanding** — judges will evaluate how well competitors understand what their translator actually does. Automated scoring will be balanced with human evaluation of architectural choices, trade-offs, and the team's ability to explain their approach. A high test score from a tool the team cannot explain will be weighted down.

We use tools like pyscn for scoring the quality. Scoring: `make evaluate_tt` runs tests (50%) + code quality via pyscn (50%). Judge review adjusts the final score.
