"""Offline tests for the read-only duplicate author report."""

from contextlib import redirect_stdout
import importlib.util
import io
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("duplicates", Path(__file__).with_name("find-duplicate-authors.py"))
duplicates = importlib.util.module_from_spec(spec)
spec.loader.exec_module(duplicates)


class DuplicateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "test.db"
        con = sqlite3.connect(self.path)
        con.execute("CREATE TABLE authors(id INTEGER PRIMARY KEY, yt_name TEXT, nico_name TEXT, twitter_name TEXT, yt_url TEXT, nico_url TEXT, twitter_url TEXT)")
        con.executemany("INSERT INTO authors VALUES(?,?,?,?,?,?,?)", [
            (0, "原作者未知", None, None, None, None, None),
            (1, " A  B ", None, "shared", None, None, "http://twitter.com/Owner/?s=20"),
            (2, None, "A B", "shared", None, None, "https://x.com/owner"),
            (3, None, None, None, None, "https://nicovideo.jp/user/42/video", None),
            (4, None, None, None, None, "https://www.nicovideo.jp/user/42?ref=a", None),
            (5, "", "　", None, None, None, None),
            (6, None, None, None, None, None, None),
            (7, "原作者未知", None, None, None, None, None),
            (8, None, None, "SHARED", None, None, "https://x.com/other"),
            (9, None, None, None, None, None, "https://x.com/owner/status/1"),
        ])
        con.commit(); con.close()
        self.con = sqlite3.connect(self.path.resolve().as_uri() + "?mode=ro", uri=True)

    def tearDown(self):
        self.con.close(); self.tmp.cleanup()

    def test_platform_matches_normalization_and_no_empty_matches(self):
        _, pairs, invalid = duplicates.find_duplicates(self.con)
        self.assertEqual(set(pairs), {(1, 2), (3, 4)})
        self.assertEqual(len(pairs[(1, 2)]["names"]), 2)
        self.assertEqual(len(pairs[(1, 2)]["urls"]), 1)
        self.assertEqual(invalid, [(9, "twitter_url", "https://x.com/owner/status/1")])

    def test_name_conflicts_and_no_transitive_grouping(self):
        con = sqlite3.connect(":memory:")
        self.con.backup(con)
        con.execute("UPDATE authors SET twitter_name='shared' WHERE id=8")
        con.execute("UPDATE authors SET yt_name='Unique',twitter_name=NULL WHERE id=2")
        con.commit()
        _, pairs, _ = duplicates.find_duplicates(con)
        self.assertIn((1, 8), pairs)
        self.assertTrue(pairs[(1, 8)]["conflicts"])
        self.assertNotIn((2, 8), pairs)
        con.close()

    def test_report_readonly_and_offline(self):
        before = self.path.read_bytes()
        with patch("author_links.requests.get", side_effect=AssertionError("must not use network")), redirect_stdout(io.StringIO()) as output:
            duplicates.report(self.con)
        self.assertIn("合计: 2 对", output.getvalue())
        self.assertEqual(self.path.read_bytes(), before)
        with self.assertRaises(sqlite3.OperationalError):
            self.con.execute("UPDATE authors SET yt_name='changed'")


if __name__ == "__main__":
    unittest.main()
