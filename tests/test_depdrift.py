"""Tests for depdrift."""

from pathlib import Path

from depdrift.lockfile import load
from depdrift.review import levenshtein, major, review, to_markdown, typosquat_target

FIXTURES = Path(__file__).parent / "fixtures"


def test_diff_counts_added_removed_changed():
    result = review(load(FIXTURES / "old-package-lock.json"), load(FIXTURES / "new-package-lock.json"))
    assert {p.name for p in result.added} == {"expresss", "shady-pkg", "mirrored-pkg"}
    assert result.removed == []
    assert [(o.name, o.version, n.version) for o, n in result.changed] == [("express", "4.18.2", "5.0.0")]


def test_typosquat_is_critical():
    result = review(load(FIXTURES / "old-package-lock.json"), load(FIXTURES / "new-package-lock.json"))
    squat = [f for f in result.findings if f.rule == "typosquat"]
    assert squat and squat[0].package == "expresss"
    assert squat[0].severity == "critical"


def test_install_script_is_high():
    result = review(load(FIXTURES / "old-package-lock.json"), load(FIXTURES / "new-package-lock.json"))
    scripts = [f for f in result.findings if f.rule == "install-script"]
    assert [f.package for f in scripts] == ["expresss"]


def test_git_dependency_flagged():
    result = review(load(FIXTURES / "old-package-lock.json"), load(FIXTURES / "new-package-lock.json"))
    git = [f for f in result.findings if f.rule == "git-dependency"]
    assert [f.package for f in git] == ["shady-pkg"]


def test_non_default_registry_flagged():
    result = review(load(FIXTURES / "old-package-lock.json"), load(FIXTURES / "new-package-lock.json"))
    mirrors = [f for f in result.findings if f.rule == "non-default-registry"]
    assert [f.package for f in mirrors] == ["mirrored-pkg"]


def test_major_version_jump_reported():
    result = review(load(FIXTURES / "old-package-lock.json"), load(FIXTURES / "new-package-lock.json"))
    jumps = [f for f in result.findings if f.rule == "major-version-jump"]
    assert jumps and jumps[0].package == "express"


def test_clean_diff_produces_no_findings():
    same = FIXTURES / "old-package-lock.json"
    result = review(load(same), load(same))
    assert result.findings == []
    assert result.worst == "none"
    assert "absence of known shapes" in to_markdown(result)


def test_levenshtein_and_major_helpers():
    assert levenshtein("express", "expresss") == 1
    assert levenshtein("kitten", "sitting") == 3
    assert major("5.0.0") == 5
    assert major("v2.1.3-beta") == 2
    assert major("latest") is None


def test_typosquat_ignores_exact_popular_names():
    assert typosquat_target("lodash") is None
    assert typosquat_target("lodas") == "lodash"
    assert typosquat_target("@scope/react") is None


def test_old_lockfile_version_1_layout():
    v1 = {"lockfileVersion": 1, "dependencies": {
        "left-pad": {"version": "1.3.0", "resolved": "https://registry.npmjs.org/left-pad/-/left-pad-1.3.0.tgz"},
        "chalk": {"version": "2.4.2", "resolved": "https://registry.npmjs.org/chalk/-/chalk-2.4.2.tgz",
                   "dependencies": {"ansi-styles": {"version": "3.2.1", "resolved": "https://registry.npmjs.org/ansi-styles/-/ansi-styles-3.2.1.tgz"}}},
    }}
    tmp = FIXTURES / "v1-lock.json"
    tmp.write_text(__import__("json").dumps(v1))
    loaded = load(tmp)
    assert set(loaded.packages) == {"left-pad", "chalk", "ansi-styles"}
    tmp.unlink()
