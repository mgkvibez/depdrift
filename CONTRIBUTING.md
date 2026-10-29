# Contributing

## Most useful contributions

1. **A new lockfile format** (`pnpm-lock.yaml`, `yarn.lock`, `poetry.lock`, `Cargo.lock`). Add a parser
   in `depdrift/` returning the same `Lockfile` shape.
2. **A new rule.** One function in `review.py`, a severity, a fixture pair, and a test.
3. **Registry-specific checks** for ecosystems other than npm.

## Rules

- Stay local. No network calls, no API keys, no telemetry, ever.
- Every rule needs a fixture that fires it and a fixture that does not.
- Severity means consequence, not confidence: `install-script` is high because it executes code,
  regardless of whether that particular package is malicious.
- Never claim a dependency is safe. Report which rules fired and which did not apply.

## Tests

```bash
python -m pytest -q
```
