"""Run with: python -m unittest discover -s test/update -v."""

import importlib.util
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

PROJECT = Path(__file__).resolve().parents[3]
SCRIPT = PROJECT / "update" / "scripts" / "updatelog.py"
spec = importlib.util.spec_from_file_location("updatelog", SCRIPT)
updatelog = importlib.util.module_from_spec(spec)
# Do not read the real project's .env while importing test helpers.
with tempfile.TemporaryDirectory() as import_root:
    with patch.dict(os.environ, {"PROJECT_ROOT": import_root}):
        spec.loader.exec_module(updatelog)


class AnnouncementEntryTests(unittest.TestCase):
    def test_structured_entry_and_commit_link(self):
        with patch.object(updatelog, "DOLTHUB_REPO", "example/videos"):
            entry = updatelog.generate_update_entry(2, 69, 71, "commit123")
        self.assertEqual(
            entry["items"][0], [{"text": "新收录作者2位，视频69个，熟肉71个"}]
        )
        self.assertEqual(
            entry["items"][1][1],
            {
                "text": "dolthub",
                "href": "https://www.dolthub.com/repositories/example/videos/compare/main/commit123",
            },
        )
        self.assertRegex(entry["date"], r"^\d{4}\.\d{2}\.\d{2}$")

    def test_partial_increases_and_no_positive_changes(self):
        with patch.object(updatelog, "DOLTHUB_REPO", "example/videos"):
            entry = updatelog.generate_update_entry(-1, 3, 0)
        self.assertEqual(entry["items"][0], [{"text": "新收录视频3个"}])
        self.assertEqual(
            entry["items"][1][1]["href"],
            "https://www.dolthub.com/repositories/example/videos",
        )
        self.assertIsNone(updatelog.generate_update_entry(0, -1, 0))


class UpdateLogIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        script_dir = self.root / "update" / "scripts"
        script_dir.mkdir(parents=True)
        self.script = script_dir / SCRIPT.name
        shutil.copy2(SCRIPT, self.script)
        self.log = script_dir / "content.log"
        self.log.write_text("1,1,1\n", encoding="utf-8")
        self.data = self.root / "frontend" / "src" / "data" / "announcements.js"
        self.data.parent.mkdir(parents=True)
        shutil.copy2(
            PROJECT / "frontend" / "src" / "data" / "announcements.js", self.data
        )
        self.before = self.data.read_text(encoding="utf-8")
        self.db = self.root / "stats.db"
        with closing(sqlite3.connect(self.db)) as conn:
            conn.executescript(
                """
                CREATE TABLE authors (id INTEGER PRIMARY KEY);
                CREATE TABLE videos (id INTEGER PRIMARY KEY, author INTEGER, translation_status INTEGER);
                INSERT INTO authors VALUES (1), (2);
                INSERT INTO videos VALUES (1, 1, 1), (2, 2, 2), (3, 2, 5);
            """
            )
        # Return a deterministic Dolt commit; never invoke the real repository.
        bin_dir = self.root / "bin"
        bin_dir.mkdir()
        dolt = bin_dir / "dolt"
        dolt.write_text(
            "#!/bin/sh\necho 'commit123 weekly "
            + updatelog.datetime.now().strftime("%Y%m%d")
            + "'\n"
        )
        dolt.chmod(0o755)
        (self.root / "dolt").mkdir()
        self.env = {
            **os.environ,
            "PROJECT_ROOT": str(self.root),
            "DOLTHUB_REPO": "example/videos",
            "PATH": str(bin_dir) + os.pathsep + os.environ["PATH"],
        }

    def run_script(self, *args):
        return subprocess.run(
            [sys.executable, str(self.script), "--db-path", str(self.db), *args],
            cwd=self.root,
            env=self.env,
            capture_output=True,
            text=True,
            check=False,
        )

    def read_module(self, source):
        # Node imports the actual module so JavaScript syntax and string escaping are checked.
        module = self.root / "entries.mjs"
        module.write_text(source, encoding="utf-8")
        result = subprocess.run(
            [
                "node",
                "--input-type=module",
                "-e",
                "const {announcements}=await import(process.argv[1]); console.log(JSON.stringify(announcements));",
                module.as_uri(),
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        return json.loads(result.stdout)

    def test_cli_prepends_valid_data_preserves_history_and_records_stats(self):
        original = self.read_module(self.before)
        result = self.run_script()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        content = self.data.read_text(encoding="utf-8")
        updated = self.read_module(content)
        self.assertEqual(updated[1:], original)
        self.assertEqual(
            updated[0]["items"][0], [{"text": "新收录作者1位，视频2个，熟肉1个"}]
        )
        self.assertTrue(
            updated[0]["items"][1][1]["href"].endswith("/compare/main/commit123")
        )
        self.assertEqual(self.log.read_text(), "1,1,1\n2,3,2\n")
        self.assertFalse((self.root / "frontend" / "src" / "views").exists())
        # Running again without new content must not insert another entry.
        second = self.run_script()
        self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
        self.assertEqual(self.data.read_text(encoding="utf-8"), content)
        self.assertEqual(self.log.read_text(), "1,1,1\n2,3,2\n")

    def test_dry_run_does_not_change_data_or_stats(self):
        result = self.run_script("--dry-run")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('"items"', result.stdout)
        self.assertEqual(self.data.read_text(encoding="utf-8"), self.before)
        self.assertEqual(self.log.read_text(), "1,1,1\n")

    def test_missing_export_does_not_change_data_or_advance_stats(self):
        invalid = "export const unrelated = [];\n"
        self.data.write_text(invalid, encoding="utf-8")
        result = self.run_script()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("Could not find the announcements export", result.stdout)
        self.assertEqual(self.data.read_text(encoding="utf-8"), invalid)
        self.assertEqual(self.log.read_text(), "1,1,1\n")

    def test_entry_strings_are_escaped_as_valid_javascript(self):
        entry = {
            "date": "2000.01.01",
            "items": [[{"text": '引号 " 与换行\n反斜杠 \\'}]],
        }
        self.assertTrue(updatelog.update_announcement(self.data, entry))
        updated = self.read_module(self.data.read_text(encoding="utf-8"))
        self.assertEqual(updated[0], entry)


if __name__ == "__main__":
    unittest.main()
