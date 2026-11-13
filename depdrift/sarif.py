"""Render a dependency review as a SARIF 2.1.0 log."""

from __future__ import annotations

import os
from pathlib import PureWindowsPath
from typing import Any
from urllib.parse import quote

from . import __version__
from .review import Finding, Review

SARIF_SCHEMA = "https://docs.oasis-open.org/sarif/sarif/v2.1.0/errata01/os/schemas/sarif-schema-2.1.0.json"
SARIF_VERSION = "2.1.0"
HELP_BASE_URI = "https://github.com/mgkvibez/depdrift/blob/main/README.md"

_RULE_DEFINITIONS: tuple[tuple[str, str], ...] = (
    ("typosquat", "New package name is within edit distance of a popular package."),
    ("install-script", "Package declares an install or postinstall script that runs on npm install."),
    ("git-dependency", "Package resolves to a git reference instead of a published tarball."),
    ("non-default-registry", "Package resolves from a host other than the official npm registry."),
    ("major-version-jump", "An existing package crosses a major version boundary."),
    ("diff-size", "A large number of new packages arrived in a single lockfile change."),
)

_RULE_INDEX: dict[str, int] = {rule_id: idx for idx, (rule_id, _) in enumerate(_RULE_DEFINITIONS)}

_LEVEL_BY_SEVERITY: dict[str, str] = {
    "critical": "error",
    "high": "error",
    "medium": "warning",
    "low": "note",
    "info": "note",
}


def _build_rules() -> list[dict[str, Any]]:
    return [
        {
            "id": rule_id,
            "shortDescription": {"text": description},
            "helpUri": f"{HELP_BASE_URI}#{rule_id}",
        }
        for rule_id, description in _RULE_DEFINITIONS
    ]


def _to_artifact_uri(path: str) -> str:
    """Encode native relative paths and fully qualified Windows/POSIX paths."""
    windows_path = PureWindowsPath(path)
    drive_is_letter = len(windows_path.drive) == 2 and windows_path.drive[1] == ":"
    if windows_path.is_absolute() and (os.name == "nt" or drive_is_letter):
        return windows_path.as_uri()
    if path.startswith("/"):
        return f"file://{quote(path, safe='/')}"
    if os.name == "nt":
        if windows_path.drive or windows_path.root:
            raise ValueError("SARIF needs a fully qualified Windows path or a relative path without a drive/root")
        return quote(windows_path.as_posix(), safe="/")
    return quote(path, safe="/")


def _format_message(finding: Finding) -> str:
    if finding.version:
        return f"{finding.package}@{finding.version}: {finding.detail}"
    return f"{finding.package}: {finding.detail}"


def to_sarif(result: Review) -> dict[str, Any]:
    """Convert a Review into a SARIF 2.1.0 dictionary."""
    artifact_uri = _to_artifact_uri(result.new_path)
    results: list[dict[str, Any]] = []
    for finding in result.findings:
        entry: dict[str, Any] = {
            "ruleId": finding.rule,
            "level": _LEVEL_BY_SEVERITY.get(finding.severity, "warning"),
            "message": {"text": _format_message(finding)},
            "locations": [
                {
                    "physicalLocation": {
                        "artifactLocation": {"uri": artifact_uri},
                    }
                }
            ],
        }
        if finding.rule in _RULE_INDEX:
            entry["ruleIndex"] = _RULE_INDEX[finding.rule]
        results.append(entry)

    return {
        "$schema": SARIF_SCHEMA,
        "version": SARIF_VERSION,
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "depdrift",
                        "version": __version__,
                        "rules": _build_rules(),
                    }
                },
                "results": results,
            }
        ],
    }
