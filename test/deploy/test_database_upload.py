"""Exercise database replacement with temporary SQLite files and fake services."""

import os
import sqlite3
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FIELDS = {
    "authors": "id yt_name yt_url yt_avatar nico_name nico_url nico_avatar twitter_name twitter_url twitter_avatar comment",
    "videos": "id author original_name original_url original_thumbnail original_duration date repost_name repost_url repost_thumbnail repost_duration translation_status comment",
}


def make_database(path, name):
    with sqlite3.connect(path) as db:
        for table, fields in FIELDS.items():
            db.execute(f'CREATE TABLE {table} ({", ".join(fields.split())})')
        db.execute("INSERT INTO authors (id, yt_name) VALUES (1, ?)", (name,))


def author_name(path):
    with sqlite3.connect(path) as db:
        return db.execute("SELECT yt_name FROM authors").fetchone()[0]


class DatabaseUploadTest(unittest.TestCase):
    def scenario(self, health_ok=True, valid=True):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tools = root / "bin"
            tools.mkdir()
            database = root / "random-2hu-stuff.db"
            candidate = root / ".database-upload.test"
            make_database(database, "old")
            if valid:
                make_database(candidate, "new")
            else:
                candidate.write_text("invalid SQLite")
            for name, body in {
                "pm2": 'echo "$*" >> "$CALLS"\nexit 0',
                "curl": "exit " + ("0" if health_ok else "1"),
                "sleep": "exit 0",
            }.items():
                tool = tools / name
                tool.write_text("#!/bin/sh\n" + body + "\n")
                tool.chmod(0o755)
            calls = root / "calls"
            env = dict(
                os.environ,
                PATH=str(tools) + ":" + os.environ["PATH"],
                DATABASE_BACKEND_DIR=str(root),
                CALLS=str(calls),
            )
            result = subprocess.run(
                ["bash", str(ROOT / "deploy/replace-database.sh"), str(candidate)],
                env=env,
                capture_output=True,
                text=True,
            )
            log = calls.read_text()
            if valid and health_ok:
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(author_name(database), "new")
                backups = list(root.glob("*.backup.*"))
                self.assertEqual(len(backups), 1)
                self.assertEqual(author_name(backups[0]), "old")
                self.assertIn("stop r2s-api", log)
                self.assertIn("restart r2s-api", log)
            else:
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(author_name(database), "old")
                if not valid:
                    self.assertNotIn("stop", log)
                else:
                    self.assertIn("restart r2s-api", log)

    def test_upload_keeps_backup_and_restarts(self):
        self.scenario()

    def test_rejects_invalid_database_before_stopping(self):
        self.scenario(valid=False)

    def test_health_failure_restores_previous_database(self):
        self.scenario(health_ok=False)
