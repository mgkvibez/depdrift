# Contributing

## Adding a rule

Rules live in `depdrift/review.py`. A rule gets a severity, a stable `id`, a message that names the
package, and a fix that says what to do.

Every rule needs a fixture pair in `tests/fixtures/` (before and after lockfile) and a test that
asserts both the finding **and** its severity. A rule that fires on a clean diff is a false alarm, and
false alarms get tools uninstalled.

## Running the tests

```bash
python -m pytest -q
```

CI runs the suite on Python 3.9 and 3.12.

## Rules of the road

- **Local-first.** No registry calls, no API keys, no telemetry, ever.
- **Explain the risk, not the mechanism.** "installs code on npm install" beats "hasInstallScript=true".
- **No CVE lookup in core.** Feeds are noisy and rate-limited; keep that out of the deterministic path.
- Severity must be defensible in one sentence. If you cannot say why it is high, it is not high.

## Pull requests

One rule per PR, fixtures included, `pytest` green.
