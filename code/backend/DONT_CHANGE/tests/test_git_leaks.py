"""tools/check_git_leaks: what counts as a leak, and that secrets are not printed in full."""

from __future__ import annotations

import sys
import unittest
from unittest import mock

from project_location import DONT_CHANGE

with mock.patch.object(sys, "path", [str(DONT_CHANGE / "scripts" / "tools"), *sys.path]):
    import check_git_leaks as tool

# Assembled at runtime, so that this file itself does not look like it holds a token.
AWS_KEY = "AK" + "IA" + "ABCDEFGHIJKLMNOP"
GITHUB_TOKEN = "gh" + "p_" + "a1B2" * 10


def kinds(line: str, path: str = "app.py"):
    return [finding.kind for finding in tool.line_findings(line, path, path + ":1")]


class LeakPatternTests(unittest.TestCase):
    def test_token_formats_are_found(self):
        self.assertEqual(kinds(f'key = "{AWS_KEY}"'), ["AWS access key"])
        self.assertEqual(kinds(f"token: {GITHUB_TOKEN}"), ["GitHub token"])
        self.assertEqual(kinds("-----BEGIN RSA " + "PRIVATE KEY-----"), ["Private key"])

    def test_credentials_in_code_and_urls(self):
        self.assertEqual(kinds('api_key = "q7Zp2Lm9Xw4R"'), ["Hard-coded credential"])
        self.assertEqual(kinds("https://bob:q7Zp2Lm9@host.org/x"), ["Password in URL"])

    def test_a_password_containing_a_common_word_is_found(self):
        self.assertEqual(kinds('password = "SuperSecret123"'), ["Hard-coded credential"])

    def test_placeholders_are_not_secrets(self):
        for line in (
            'password = "your-password"',
            'api_key = "{API_KEY}"',
            'secret = "xxxxxxxxxx"',
            "api_key = os.environ",
        ):
            with self.subTest(line=line):
                self.assertEqual(kinds(line), [])

    def test_personal_data_is_a_separate_level(self):
        found = tool.line_findings(r"open('C:\Users\Alice\notes.txt')  # bob@company.org", "app.py", "app.py:1")
        self.assertEqual(
            [(f.level, f.kind, f.value) for f in found],
            [
                (tool.PERSONAL, "Home folder path", "Alice"),
                (tool.PERSONAL, "Email address", "bob@company.org"),
            ],
        )

    def test_harmless_text_is_not_reported(self):
        for line in (
            r"C:\Users\Public\x",
            "a@example.com",
            "git@github.com:me/x.git",
            'python_version = "pypy@3.11"',
            "pkg @ https://host.org/a.whl",
            "a4c99c84@1eab4699.json",
        ):
            with self.subTest(line=line):
                self.assertEqual(kinds(line), [])

    def test_third_party_code_is_skipped(self):
        self.assertEqual(kinds(f'key = "{AWS_KEY}"', "x/site-packages/y.py"), [])
        self.assertEqual(tool.file_name_findings("x/site-packages/certifi/cacert.pem", "x"), [])

    def test_a_line_can_be_accepted(self):
        self.assertEqual(kinds(f'key = "{AWS_KEY}"  # leak-check: ignore'), [])

    def test_secrets_are_masked(self):
        found = tool.line_findings(f"token: {GITHUB_TOKEN}", "app.py", "app.py:1")
        self.assertEqual(found[0].value, GITHUB_TOKEN[:4] + "****")
        self.assertNotIn(GITHUB_TOKEN, repr(found))

    def test_file_names(self):
        self.assertEqual(tool.file_name_findings("config/.env", "x")[0].level, tool.SECRET)
        self.assertEqual(tool.file_name_findings("deploy/id_rsa", "x")[0].level, tool.SECRET)
        self.assertEqual(tool.file_name_findings("App.lnk", "x")[0].level, tool.PERSONAL)
        self.assertEqual(tool.file_name_findings(".env.example", "x"), [])
        self.assertEqual(tool.file_name_findings("main.py", "x"), [])


class ReportTests(unittest.TestCase):
    def test_one_row_per_value_counts_its_files(self):
        findings = [tool.Finding(tool.PERSONAL, "Home folder path", "Flo", p + ":1", p) for p in ("a", "b", "a")]
        with mock.patch.object(tool._ui, "table") as table, mock.patch.object(tool._ui, "heading"):
            tool.show("Personal", findings)
        self.assertEqual(table.call_args[0][1], [(2, "Flo", "Home folder path", "a:1")])


class HistoryTests(unittest.TestCase):
    LOG = f"""commit abc1234

diff --git a/app.py b/app.py
--- a/app.py
+++ b/app.py
@@ -0,0 +1 @@
+key = "{AWS_KEY}"
-removed = "{GITHUB_TOKEN}"
"""

    def test_only_added_lines_count_and_name_their_commit(self):
        found = tool.parse_history(self.LOG)
        self.assertEqual([f.kind for f in found], ["AWS access key"])
        self.assertEqual(found[0].where, "app.py (commit abc1234)")

    def test_a_leak_still_in_the_files_is_listed_once(self):
        history = tool.parse_history(self.LOG)
        current = tool.line_findings(f'key = "{AWS_KEY}"', "app.py", "app.py:1")
        self.assertEqual(tool.only_new_history(current, history), [])
        self.assertEqual(len(tool.only_new_history([], history + history)), 1)


if __name__ == "__main__":
    unittest.main()
