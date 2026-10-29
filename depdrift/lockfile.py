"""Parse npm lockfiles into a flat package map."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Package:
    """One resolved package entry from a lockfile."""

    name: str
    version: str = ""
    resolved: str = ""
    has_install_script: bool = False
    is_git: bool = False
    is_link: bool = False
    dev: bool = False


@dataclass
class Lockfile:
    """A parsed lockfile: name -> Package."""

    path: str
    packages: dict[str, Package] = field(default_factory=dict)
    lockfile_version: int = 0


def _name_from_path(path: str) -> str:
    """'node_modules/@scope/pkg' -> '@scope/pkg'; nested paths keep the last package."""
    marker = "node_modules/"
    if marker not in path:
        return path
    tail = path.split(marker)[-1]
    return tail


def _from_packages_map(data: dict) -> dict[str, Package]:
    """Handle lockfileVersion 2 and 3 layouts."""
    out: dict[str, Package] = {}
    for path, entry in data.get("packages", {}).items():
        if not path:
            continue
        if entry.get("link"):
            continue
        name = entry.get("name") or _name_from_path(path)
        if not name:
            continue
        resolved = entry.get("resolved", "") or ""
        out[name] = Package(
            name=name,
            version=entry.get("version", "") or "",
            resolved=resolved,
            has_install_script=bool(entry.get("hasInstallScript")),
            is_git=resolved.startswith(("git+", "git:", "github:")),
            dev=bool(entry.get("dev")),
        )
    return out


def _from_dependencies_map(deps: dict, out: dict[str, Package] | None = None) -> dict[str, Package]:
    """Handle lockfileVersion 1, which nests dependencies recursively."""
    out = {} if out is None else out
    for name, entry in deps.items():
        if not isinstance(entry, dict):
            continue
        resolved = entry.get("resolved", "") or ""
        out.setdefault(
            name,
            Package(
                name=name,
                version=entry.get("version", "") or "",
                resolved=resolved,
                has_install_script=bool(entry.get("requires", {}).get("install")),
                is_git=resolved.startswith(("git+", "git:", "github:")),
                dev=bool(entry.get("dev")),
            ),
        )
        nested = entry.get("dependencies")
        if isinstance(nested, dict):
            _from_dependencies_map(nested, out)
    return out


def load(path: str | Path) -> Lockfile:
    """Load an npm lockfile from disk."""
    file_path = Path(path)
    data = json.loads(file_path.read_text(encoding="utf-8"))
    version = int(data.get("lockfileVersion", 1))
    if "packages" in data:
        packages = _from_packages_map(data)
    else:
        packages = _from_dependencies_map(data.get("dependencies", {}))
    return Lockfile(path=str(file_path), packages=packages, lockfile_version=version)
