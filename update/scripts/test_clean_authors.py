"""Tests for deployment-aware cleanup, using temporary databases only."""

from contextlib import closing, redirect_stdout
import importlib.util
import io
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("cleanup", Path(__file__).with_name("clean-authors.py"))
cleanup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cleanup)


class CleanupTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.db = self.root / "test.db"
        self.log = self.root / "content.log"
        self.log.write_text("3,4,2\n5,7,3\n\n", encoding="utf-8")
        with closing(sqlite3.connect(self.db)) as con, con:
            con.executescript("CREATE TABLE authors(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT,comment TEXT); CREATE TABLE videos(id INTEGER PRIMARY KEY,author INTEGER REFERENCES authors(id));")
            con.executemany("INSERT INTO authors VALUES(?,?,?)", [(0,"原作者未知",None),(2,None,None),(5,"old",None),(8,None,None),(10,"new",None),(12,None,None)])
            con.executemany("INSERT INTO videos VALUES(?,?)", [(1,2),(2,5),(3,8),(4,10),(5,12)])

    def tearDown(self):
        self.tmp.cleanup()

    def run_clean(self, dry_run=False, answers=None):
        with redirect_stdout(io.StringIO()) as output, patch("builtins.input", side_effect=answers or ["n"]):
            cleanup.clean(self.db, dry_run, self.log)
        return output.getvalue()

    def test_preserve_deployed_ids_and_references(self):
        output = self.run_clean()
        with closing(sqlite3.connect(self.db)) as con, con:
            self.assertEqual(list(con.execute("SELECT * FROM authors ORDER BY id")), [(0,"原作者未知",None),(2,None,None),(5,"old",None),(6,"new",None)])
            self.assertEqual(list(con.execute("SELECT author FROM videos ORDER BY id")), [(2,),(5,),(0,),(6,),(0,)])
            self.assertEqual(list(con.execute("PRAGMA foreign_key_check")), [])
            con.execute("INSERT INTO authors(name) VALUES('next')")
            self.assertEqual(con.execute("SELECT last_insert_rowid()").fetchone(), (7,))
        self.assertIn("id=8", output)
        self.assertIn("id=12", output)
        self.assertIn("实际已删除作者 ID: 8, 12", output)
        self.assertIn("已部署的全 NULL 作者，保留不动: 2", output)
        backup = next(self.root.glob("*.backup-*"))
        with closing(sqlite3.connect(backup)) as con, con:
            self.assertEqual(con.execute("SELECT COUNT(*) FROM authors").fetchone(), (6,))

    def test_preview_and_repeat(self):
        before = self.db.read_bytes()
        self.assertIn("id=8", self.run_clean(True))
        self.assertEqual(self.db.read_bytes(), before)
        self.assertFalse(list(self.root.glob("*.backup-*")))
        self.run_clean()
        self.assertIn("实际已删除作者 ID: 无", self.run_clean())

    def test_bad_log_fails_before_backup_or_write(self):
        before = self.db.read_bytes()
        for value in ("", "5,7\n", "5,7,3\nbroken\n", "-1,7,3"):
            self.log.write_text(value)
            with self.assertRaises(ValueError):
                self.run_clean()
        self.log.unlink()
        with self.assertRaises(OSError):
            self.run_clean()
        self.assertEqual(self.db.read_bytes(), before)
        self.assertFalse(list(self.root.glob("*.backup-*")))

    def test_backup_failure_and_transaction_rollback(self):
        before = self.db.read_bytes()
        with patch.object(cleanup, "backup_database", side_effect=OSError("failure")):
            with self.assertRaises(OSError):
                self.run_clean()
        self.assertEqual(self.db.read_bytes(), before)
        with closing(sqlite3.connect(self.db)) as con, con:
            con.execute("CREATE TRIGGER reject_delete BEFORE DELETE ON authors BEGIN SELECT RAISE(ABORT,'failure'); END")
        with self.assertRaises(sqlite3.IntegrityError):
            self.run_clean()
        with closing(sqlite3.connect(self.db)) as con, con:
            self.assertEqual(con.execute("SELECT COUNT(*) FROM authors").fetchone(), (6,))
            self.assertEqual(con.execute("SELECT author FROM videos WHERE id=3").fetchone(), (8,))

    def test_confirm_move_last_author_and_video_links(self):
        output = self.run_clean(answers=["yes"])
        with closing(sqlite3.connect(self.db)) as con:
            self.assertEqual(list(con.execute("SELECT * FROM authors ORDER BY id")),
                             [(0,"原作者未知",None),(2,"new",None),(5,"old",None)])
            self.assertEqual(list(con.execute("SELECT author FROM videos ORDER BY id")),
                             [(0,),(5,),(0,),(2,),(0,)])
            self.assertEqual(list(con.execute("PRAGMA foreign_key_check")), [])
        self.assertIn("实际已替换: 作者原 ID 10 → 2", output)

    def test_multiple_holes_use_last_remaining_author(self):
        with closing(sqlite3.connect(self.db)) as con, con:
            con.executemany("INSERT INTO authors VALUES(?,?,?)", [(3,None,None),(14,"last",None)])
            con.executemany("INSERT INTO videos VALUES(?,?)", [(6,14),(7,3)])
        self.run_clean(answers=["y", "y"])
        with closing(sqlite3.connect(self.db)) as con:
            self.assertEqual(list(con.execute("SELECT id,name FROM authors ORDER BY id")),
                             [(0,"原作者未知"),(2,"last"),(3,"new"),(5,"old")])
            self.assertEqual(con.execute("SELECT author FROM videos WHERE id=6").fetchone(), (2,))
            self.assertEqual(con.execute("SELECT author FROM videos WHERE id=7").fetchone(), (0,))

    def test_preview_never_prompts_or_replaces(self):
        with patch("builtins.input", side_effect=AssertionError("preview must not prompt")), redirect_stdout(io.StringIO()) as output:
            cleanup.clean(self.db, True, self.log)
        self.assertIn("末尾作者 id=10 → 已部署空作者 id=2", output.getvalue())
        self.assertFalse(list(self.root.glob("*.backup-*")))

    def test_eof_skips_and_interrupt_cancels(self):
        self.run_clean(answers=[EOFError()])
        with closing(sqlite3.connect(self.db)) as con:
            self.assertEqual(con.execute("SELECT name FROM authors WHERE id=2").fetchone(), (None,))
        before = self.db.read_bytes()
        backups = list(self.root.glob("*.backup-*"))
        with self.assertRaises(KeyboardInterrupt):
            self.run_clean(answers=[KeyboardInterrupt()])
        self.assertEqual(self.db.read_bytes(), before)
        self.assertEqual(list(self.root.glob("*.backup-*")), backups)

    def test_database_change_during_confirmation_aborts(self):
        def confirm(_):
            with closing(sqlite3.connect(self.db)) as other, other:
                other.execute("UPDATE authors SET name='changed' WHERE id=10")
            return "y"
        with patch("builtins.input", side_effect=confirm), redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(RuntimeError, "确认期间"):
                cleanup.clean(self.db, False, self.log)
        self.assertFalse(list(self.root.glob("*.backup-*")))
        with closing(sqlite3.connect(self.db)) as con:
            self.assertEqual(con.execute("SELECT name FROM authors WHERE id=2").fetchone(), (None,))

    def test_no_donor_preserves_hole_and_zero(self):
        with closing(sqlite3.connect(self.db)) as con, con:
            con.execute("DELETE FROM videos")
            con.execute("DELETE FROM authors WHERE id>=5")
            con.execute("UPDATE authors SET name=NULL WHERE id=0")
        with patch("builtins.input", side_effect=AssertionError("no donor")), redirect_stdout(io.StringIO()) as output:
            cleanup.clean(self.db, False, self.log)
        self.assertIn("没有可替换", output.getvalue())
        with closing(sqlite3.connect(self.db)) as con:
            self.assertEqual(list(con.execute("SELECT id FROM authors ORDER BY id")), [(0,),(2,)])


if __name__ == "__main__":
    unittest.main()
