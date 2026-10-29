# depdrift

Your lockfile changed by 400 lines. This tells you what actually changed, and which parts are dangerous.

```bash
git show HEAD~1:package-lock.json > /tmp/before.json
depdrift /tmp/before.json package-lock.json
```

```
# Dependency review

- added 3, removed 0, changed 1
- worst finding: **critical**

| severity | package | version | rule | detail |
|---|---|---|---|---|
| critical | expresss | 1.0.3 | typosquat | name is within edit distance of popular package 'express' |
| high | expresss | 1.0.3 | install-script | package declares an install/postinstall script that runs on npm install |
| high | shady-pkg | 0.0.1 | git-dependency | resolves to a git reference instead of a published tarball |
| medium | express | 5.0.0 | major-version-jump | 4.18.2 -> 5.0.0: major version changed, read the changelog |
| medium | mirrored-pkg | 2.1.0 | non-default-registry | resolves from 'registry.evil-mirror.dev' instead of registry.npmjs.org |
```

## Install

```bash
pipx install depdrift
```

Local only: no registry calls, no API key, no telemetry. Python 3.9+.

## Usage

```bash
depdrift before.json after.json          # markdown report
depdrift before.json after.json --json   # for CI and agents
depdrift before.json after.json --fail-on high   # exit 2 when something is high or critical
```

Typical CI use, on a dependency-update PR:

```yaml
- run: git show origin/main:package-lock.json > /tmp/before.json
- run: depdrift /tmp/before.json package-lock.json --fail-on high
```

## What it checks

| Rule | Severity | Why it matters |
|---|---|---|
| `typosquat` | critical | name is within edit distance 1-2 of a popular package; the classic supply-chain trap |
| `install-script` | high | the package runs code on install, before you ever require it |
| `git-dependency` | high | a git ref is mutable; the tarball you audited is not the one you get |
| `non-default-registry` | medium | the package resolves from a mirror that is not npmjs |
| `major-version-jump` | medium | version diff crossed a major boundary |
| `diff-size` | low | more than 40 new packages in one change |

## How it works

1. Parse both lockfiles. `lockfileVersion` 2 and 3 use the `packages` map; version 1 walks nested
   `dependencies`. Workspace links are skipped.
2. Diff by package name: added, removed, version-changed.
3. Run every rule over added packages, and over changed packages at their new version.
4. Sort by severity, render markdown or JSON, set an exit code if `--fail-on` is given.

The typosquat check uses a bundled list of ~150 popular package names, so it works offline. Edit
`depdrift/popular.py` to match the ecosystem you actually ship.

## Honest limits

- npm lockfiles only today. `pnpm-lock.yaml`, `yarn.lock`, `poetry.lock`, `Cargo.lock` are not parsed.
- It does not know CVEs. A package can pass every rule here and still be vulnerable; run your
  scanner as well.
- Typosquat distance is a heuristic. Close names are a reason to look, not proof of malice.
- "No findings" means "no known shape fired", never "safe".

## Tests

```bash
python -m pytest -q
```

Ten tests: diff accounting, each rule, clean-diff behaviour, v1 lockfile layout, and the
distance helpers.

## License

MIT. See [LICENSE](LICENSE).
