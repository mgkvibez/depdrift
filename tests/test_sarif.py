"""Frozen operator acceptance tests for depdrift issue #2."""
import ast
import contextlib
import copy
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from depdrift import __version__
from depdrift.cli import main
from depdrift.review import Finding, Review, review
from depdrift.lockfile import load
from depdrift.sarif import to_sarif

ROOT = Path(__file__).resolve().parents[1]
OLD = "tests/fixtures/old-package-lock.json"
NEW = "tests/fixtures/new-package-lock.json"
RULE_IDS = {"typosquat", "install-script", "git-dependency", "non-default-registry", "major-version-jump", "diff-size"}

def make_report(path="package-lock.json"):
    return Review(new_path=path, findings=[
        Finding("expresss", "critical", "typosquat", "near express", "1.0.0"),
        Finding("script-pkg", "high", "install-script", "runs an install script", "2.0.0"),
        Finding("mirror-pkg", "medium", "non-default-registry", "unusual registry", "3.0.0"),
        Finding("many packages", "low", "diff-size", "large dependency change"),
    ])

def call_cli(args):
    output, errors = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
        code = main(args)
    return code, output.getvalue(), errors.getvalue()

class SarifContract(unittest.TestCase):
    def test_log_and_tool_identity(self):
        value = to_sarif(make_report())
        self.assertEqual(value["version"], "2.1.0")
        self.assertEqual(len(value["runs"]), 1)
        driver = value["runs"][0]["tool"]["driver"]
        self.assertEqual(driver["name"], "depdrift")
        self.assertEqual(driver.get("version", driver.get("semanticVersion")), __version__)
        self.assertEqual(json.loads(json.dumps(value)), value)

    def test_complete_stable_rule_inventory(self):
        one = to_sarif(make_report())["runs"][0]["tool"]["driver"]["rules"]
        empty = to_sarif(Review(new_path="package-lock.json"))["runs"][0]["tool"]["driver"]["rules"]
        self.assertEqual(one, empty)
        self.assertEqual({rule["id"] for rule in one}, RULE_IDS)
        self.assertEqual(len(one), len(RULE_IDS))

    def test_rule_help_urls(self):
        rules = to_sarif(make_report())["runs"][0]["tool"]["driver"]["rules"]
        for rule in rules:
            self.assertEqual(rule["helpUri"], "https://github.com/mgkvibez/depdrift/blob/main/README.md#" + rule["id"])
            self.assertTrue(rule["shortDescription"]["text"])

    def test_all_four_severity_mappings(self):
        results = to_sarif(make_report())["runs"][0]["results"]
        self.assertEqual([x["level"] for x in results], ["error", "error", "warning", "note"])

    def test_one_result_per_finding_including_same_rule(self):
        report = make_report()
        report.findings.append(Finding("other-pkg", "critical", "typosquat", "another distinct finding", "4.0.0"))
        run = to_sarif(report)["runs"][0]
        self.assertEqual(len(run["results"]), len(report.findings))
        self.assertEqual(len(run["tool"]["driver"]["rules"]), 6)
        for finding, item in zip(report.findings, run["results"]):
            self.assertEqual(item["ruleId"], finding.rule)
            if "ruleIndex" in item:
                self.assertEqual(run["tool"]["driver"]["rules"][item["ruleIndex"]]["id"], finding.rule)

    def test_messages_preserve_package_version_and_detail(self):
        report = make_report()
        results = to_sarif(report)["runs"][0]["results"]
        for finding, item in zip(report.findings, results):
            text = item["message"]["text"]
            self.assertIn(finding.package, text)
            self.assertIn(finding.detail, text)
            if finding.version:
                self.assertIn(finding.version, text)

    def test_relative_uri_encodes_reserved_and_unicode(self):
        report = make_report("locks/new package#\u017e%.json")
        for result in to_sarif(report)["runs"][0]["results"]:
            physical = result["locations"][0]["physicalLocation"]
            self.assertEqual(physical["artifactLocation"]["uri"], "locks/new%20package%23%C5%BE%25.json")
            self.assertNotIn("region", physical)

    def test_absolute_posix_uri(self):
        results = to_sarif(make_report("/tmp/new lock.json"))["runs"][0]["results"]
        self.assertEqual(results[0]["locations"][0]["physicalLocation"]["artifactLocation"]["uri"], "file:///tmp/new%20lock.json")

    def test_windows_drive_uri(self):
        results = to_sarif(make_report(r"C:\repo\new lock.json"))["runs"][0]["results"]
        self.assertEqual(results[0]["locations"][0]["physicalLocation"]["artifactLocation"]["uri"], "file:///C:/repo/new%20lock.json")

    def test_empty_report_has_zero_results(self):
        value = to_sarif(Review(new_path="package-lock.json"))
        self.assertEqual(value["runs"][0]["results"], [])

    def test_deterministic_without_mutation(self):
        report = make_report()
        before = copy.deepcopy(report)
        first = to_sarif(report)
        self.assertEqual(first, to_sarif(report))
        self.assertEqual(report, before)

    def test_unicode_and_json_escaping(self):
        report = make_report()
        report.findings[0] = Finding('pkg"\n\u017e', "critical", "typosquat", 'detail "quoted"\nline', "1.0.0")
        document = to_sarif(report)
        text = document["runs"][0]["results"][0]["message"]["text"]
        self.assertIn(report.findings[0].package, text)
        self.assertIn(report.findings[0].detail, text)
        self.assertEqual(json.loads(json.dumps(document)), document)

    def test_python39_syntax(self):
        for name in ("depdrift/cli.py", "depdrift/sarif.py"):
            ast.parse((ROOT / name).read_text(), filename=name, feature_version=(3, 9))

class CliContract(unittest.TestCase):
    def test_sarif_command_outputs_only_json(self):
        code, output, errors = call_cli(["review", OLD, NEW, "--sarif"])
        self.assertEqual(code, 0)
        self.assertEqual(errors, "")
        document = json.loads(output)
        self.assertEqual(document["version"], "2.1.0")
        self.assertEqual(len(document["runs"][0]["results"]), 5)

    def test_sarif_bare_positionals(self):
        code, output, errors = call_cli([OLD, NEW, "--sarif"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output)["version"], "2.1.0")

    def test_sarif_fail_on_high_preserves_report(self):
        code, output, errors = call_cli(["review", OLD, NEW, "--sarif", "--fail-on", "high"])
        self.assertEqual(code, 2)
        self.assertEqual(len(json.loads(output)["runs"][0]["results"]), 5)

    def test_clean_sarif(self):
        code, output, errors = call_cli(["review", OLD, OLD, "--sarif", "--fail-on", "low"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output)["runs"][0]["results"], [])

    def test_json_output_is_unchanged(self):
        code, output, errors = call_cli(["review", OLD, NEW, "--json"])
        self.assertEqual(code, 0)
        result = review(load(OLD), load(NEW))
        expected = {
            "added": [f"{p.name}@{p.version}" for p in result.added],
            "removed": [f"{p.name}@{p.version}" for p in result.removed],
            "changed": [f"{o.name} {o.version}->{n.version}" for o,n in result.changed],
            "worst": result.worst,
            "findings": [f.as_dict() for f in result.findings],
        }
        self.assertEqual(output, json.dumps(expected, indent=2) + "\n")

    def test_markdown_output_is_unchanged(self):
        from depdrift.review import to_markdown
        code, output, errors = call_cli(["review", OLD, NEW])
        self.assertEqual(code, 0)
        self.assertEqual(output, to_markdown(review(load(OLD), load(NEW))) + "\n")

    def test_json_sarif_are_mutually_exclusive(self):
        with self.assertRaises(SystemExit) as caught:
            call_cli(["review", OLD, NEW, "--json", "--sarif"])
        self.assertEqual(caught.exception.code, 2)

    def test_default_lockfile_path_is_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            import os
            prior = os.getcwd()
            try:
                shutil.copy(ROOT / OLD, Path(temporary) / "before.json")
                shutil.copy(ROOT / NEW, Path(temporary) / "package-lock.json")
                os.chdir(temporary)
                code, output, errors = call_cli(["review", "before.json", "--sarif"])
            finally:
                os.chdir(prior)
        self.assertEqual(code, 0)
        for result in json.loads(output)["runs"][0]["results"]:
            self.assertEqual(result["locations"][0]["physicalLocation"]["artifactLocation"]["uri"], "package-lock.json")
