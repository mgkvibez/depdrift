"""CLI error boundaries for SARIF path validation; no native Windows claim."""
import contextlib
import io
import json
import types
import unittest
from unittest import mock

import depdrift.cli as cli
import depdrift.sarif as sarif
from depdrift.review import Review

ERROR = "SARIF needs a fully qualified Windows path or a relative path without a drive/root"


class CliPathErrors(unittest.TestCase):
    def invoke(self, path, output="--sarif"):
        stdout, stderr = io.StringIO(), io.StringIO()
        report = Review(old_path="old.json", new_path=path)
        with mock.patch.object(cli, "load", return_value=object()), \
             mock.patch.object(cli, "review", return_value=report), \
             mock.patch.object(sarif, "os", types.SimpleNamespace(name="nt")), \
             contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            try:
                code = cli.main(["old.json", path, output])
            except SystemExit as exc:
                code = exc.code
        return code, stdout.getvalue(), stderr.getvalue()

    def assert_path_error(self, path):
        code, stdout, stderr = self.invoke(path)
        self.assertEqual(code, 2)
        self.assertEqual(stdout, "")
        self.assertIn("depdrift: error:", stderr)
        self.assertIn(ERROR, stderr)
        self.assertNotIn("Traceback", stderr)

    def test_drive_relative_sarif_path_is_cli_error(self):
        self.assert_path_error("C:package-lock.json")

    def test_root_relative_sarif_path_is_cli_error(self):
        self.assert_path_error(r"\locks\package-lock.json")

    def test_fully_qualified_windows_sarif_path_remains_valid(self):
        code, stdout, stderr = self.invoke(r"C:\locks\package-lock.json")
        self.assertEqual(code, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(json.loads(stdout)["version"], "2.1.0")

    def test_windows_relative_sarif_path_remains_valid(self):
        code, stdout, stderr = self.invoke(r"locks\package-lock.json")
        self.assertEqual(code, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(json.loads(stdout)["version"], "2.1.0")

    def test_json_does_not_apply_sarif_path_validation(self):
        code, stdout, stderr = self.invoke("C:package-lock.json", "--json")
        self.assertEqual(code, 0)
        self.assertEqual(stderr, "")
        self.assertIsInstance(json.loads(stdout), dict)

    def test_unrelated_review_value_error_is_not_swallowed(self):
        with mock.patch.object(cli, "load", return_value=object()), \
             mock.patch.object(cli, "review", side_effect=ValueError("review failed")):
            with self.assertRaisesRegex(ValueError, "review failed"):
                cli.main(["old.json", "new.json", "--sarif"])
