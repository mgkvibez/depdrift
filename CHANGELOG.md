# Changelog

## v0.1.0 - 2026-10-29

- `depdrift review old.lock new.lock` summarizes added, removed and changed
  packages and turns the diff into a single markdown risk report.
- Rules: `typosquat` (edit distance to a bundled popular-name list),
  `install-script`, `git-dependency`, `non-default-registry`,
  `major-version-jump`, and `diff-size`.
- Fully local: no registry calls, no API key, no network at all. The popular-name
  list ships with the package so distance checks work on an air-gapped machine.
- npm `lockfileVersion` 1, 2 and 3 parsers.
- `--json` output and `--fail-on <severity>` for CI gating.
- 10 tests.
- Install: `pipx install git+https://github.com/mgkvibez/depdrift.git`.
