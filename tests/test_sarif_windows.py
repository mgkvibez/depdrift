"""Frozen review probes for Windows URI rendering."""
import types
import unittest
from unittest import mock
import depdrift.sarif as sarif
from depdrift.review import Finding, Review

def uri(path, platform):
    report = Review(new_path=path, findings=[Finding("pkg", "high", "install-script", "test", "1")])
    with mock.patch.object(sarif, "os", types.SimpleNamespace(name=platform), create=True):
        return sarif.to_sarif(report)["runs"][0]["results"][0]["locations"][0]["physicalLocation"]["artifactLocation"]["uri"]

class UriReviewCases(unittest.TestCase):
    def test_windows_relative_backslashes(self):
        self.assertEqual(uri(r"locks\package-lock.json", "nt"), "locks/package-lock.json")
    def test_windows_unc_backslashes(self):
        self.assertEqual(uri(r"\\server\share\new package#\u017e.json".replace(r"\u017e", "\u017e"), "nt"), "file://server/share/new%20package%23%C5%BE.json")
    def test_windows_unc_forward_slashes(self):
        self.assertEqual(uri("//server/share/package-lock.json", "nt"), "file://server/share/package-lock.json")
    def test_posix_literal_backslash_is_preserved(self):
        self.assertEqual(uri(r"locks\package-lock.json", "posix"), "locks%5Cpackage-lock.json")
    def test_posix_double_slash_is_not_unc(self):
        self.assertEqual(uri("//server/share/package-lock.json", "posix"), "file:////server/share/package-lock.json")
    def test_windows_drive_relative_is_rejected(self):
        with self.assertRaises(ValueError):
            uri("C:package-lock.json", "nt")
    def test_windows_root_relative_is_rejected(self):
        with self.assertRaises(ValueError):
            uri(r"\locks\package-lock.json", "nt")
