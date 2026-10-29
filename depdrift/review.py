"""Compare two lockfiles and turn the diff into a risk report."""

from __future__ import annotations

from dataclasses import dataclass, field
from urllib.parse import urlparse

from .lockfile import Lockfile, Package
from .popular import POPULAR

SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
OFFICIAL_REGISTRY = "registry.npmjs.org"


@dataclass
class Finding:
    """One risk in the diff."""

    package: str
    severity: str
    rule: str
    detail: str
    version: str = ""

    def as_dict(self) -> dict[str, str]:
        return {
            "package": self.package,
            "version": self.version,
            "severity": self.severity,
            "rule": self.rule,
            "detail": self.detail,
        }


@dataclass
class Review:
    """Result of comparing two lockfiles."""

    added: list[Package] = field(default_factory=list)
    removed: list[Package] = field(default_factory=list)
    changed: list[tuple[Package, Package]] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    old_path: str = ""
    new_path: str = ""

    @property
    def worst(self) -> str:
        if not self.findings:
            return "none"
        return min(self.findings, key=lambda f: SEVERITY_ORDER[f.severity]).severity


def levenshtein(a: str, b: str) -> int:
    """Edit distance, used for typosquat detection."""
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    previous = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        current = [i]
        for j, cb in enumerate(b, start=1):
            current.append(min(
                previous[j] + 1,
                current[j - 1] + 1,
                previous[j - 1] + (ca != cb),
            ))
        previous = current
    return previous[-1]


def typosquat_target(name: str) -> str | None:
    """Return the popular package this name is suspiciously close to."""
    base = name.split("/")[-1].split("@")[0].lower()
    for popular in POPULAR:
        if base == popular:
            return None
        limit = 1 if len(popular) <= 5 else 2
        if levenshtein(base, popular) <= limit:
            return popular
    return None


def registry_host(resolved: str) -> str:
    """Host a package resolves from, or '' when not a URL."""
    if not resolved.startswith(("http://", "https://")):
        return ""
    return urlparse(resolved).hostname or ""


def evaluate(package: Package, change: str) -> list[Finding]:
    """Apply every rule to one added or changed package."""
    found: list[Finding] = []

    squat = typosquat_target(package.name)
    if squat:
        found.append(Finding(
            package=package.name, version=package.version, severity="critical",
            rule="typosquat",
            detail=f"name is within edit distance of popular package '{squat}'",
        ))

    if package.has_install_script:
        found.append(Finding(
            package=package.name, version=package.version, severity="high",
            rule="install-script",
            detail="package declares an install/postinstall script that runs on npm install",
        ))

    if package.is_git:
        found.append(Finding(
            package=package.name, version=package.version, severity="high",
            rule="git-dependency",
            detail="resolves to a git reference instead of a published tarball; no immutability guarantee",
        ))

    host = registry_host(package.resolved)
    if host and host not in {OFFICIAL_REGISTRY, "registry.yarnpkg.com"}:
        found.append(Finding(
            package=package.name, version=package.version, severity="medium",
            rule="non-default-registry",
            detail=f"resolves from '{host}' instead of {OFFICIAL_REGISTRY}",
        ))

    if change == "added" and package.dev:
        pass
    return found


def major(version: str) -> int | None:
    """Major component of a semver-ish version, if parseable."""
    core = version.lstrip("v").split("-")[0].split("+")[0]
    first = core.split(".")[0]
    return int(first) if first.isdigit() else None


def review(old: Lockfile, new: Lockfile) -> Review:
    """Full diff + rule pass."""
    result = Review(old_path=old.path, new_path=new.path)

    old_names, new_names = set(old.packages), set(new.packages)
    result.added = [new.packages[n] for n in sorted(new_names - old_names)]
    result.removed = [old.packages[n] for n in sorted(old_names - new_names)]
    result.changed = [
        (old.packages[n], new.packages[n])
        for n in sorted(old_names & new_names)
        if old.packages[n].version != new.packages[n].version
    ]

    for package in result.added:
        result.findings.extend(evaluate(package, "added"))

    for old_pkg, new_pkg in result.changed:
        result.findings.extend(evaluate(new_pkg, "changed"))
        old_major, new_major = major(old_pkg.version), major(new_pkg.version)
        if old_major is not None and new_major is not None and old_major != new_major:
            result.findings.append(Finding(
                package=new_pkg.name, version=new_pkg.version, severity="medium",
                rule="major-version-jump",
                detail=f"{old_pkg.version} -> {new_pkg.version}: major version changed, read the changelog",
            ))

    if len(result.added) > 40:
        result.findings.append(Finding(
            package=f"{len(result.added)} packages", severity="low", rule="diff-size",
            detail="large number of new packages in one change; split the dependency update",
        ))

    result.findings.sort(key=lambda f: (SEVERITY_ORDER[f.severity], f.package))
    return result


def to_markdown(result: Review) -> str:
    """Render the risk report."""
    lines = [
        "# Dependency review",
        "",
        f"- before: `{result.old_path}`",
        f"- after:  `{result.new_path}`",
        f"- added {len(result.added)}, removed {len(result.removed)}, changed {len(result.changed)}",
        f"- worst finding: **{result.worst}**",
        "",
    ]

    if result.findings:
        lines += ["## Findings", "", "| severity | package | version | rule | detail |", "|---|---|---|---|---|"]
        for f in result.findings:
            lines.append(f"| {f.severity} | {f.package} | {f.version} | {f.rule} | {f.detail} |")
        lines.append("")
    else:
        lines += ["## Findings", "", "No rule fired. That is not a clean bill of health, only the absence of known shapes.", ""]

    if result.added:
        lines += ["## Added", ""]
        lines += [f"- `{p.name}@{p.version}`" for p in result.added]
        lines.append("")
    if result.removed:
        lines += ["## Removed", ""]
        lines += [f"- `{p.name}@{p.version}`" for p in result.removed]
        lines.append("")
    if result.changed:
        lines += ["## Changed", ""]
        lines += [f"- `{old.name}` {old.version} -> {new.version}" for old, new in result.changed]
        lines.append("")
    return "\n".join(lines)
