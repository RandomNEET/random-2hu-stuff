"""Offline tests: python -m unittest discover -s update/scripts -p test_author_links.py"""

from contextlib import redirect_stdout
import html
import importlib.util
import io
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import Mock, patch

import author_links as links

spec = importlib.util.spec_from_file_location("author_updater", Path(__file__).with_name("update-author-info.py"))
updater = importlib.util.module_from_spec(spec)
spec.loader.exec_module(updater)


class LinkTests(unittest.TestCase):
    def setUp(self):
        self.output = redirect_stdout(io.StringIO())
        self.output.__enter__()

    def tearDown(self):
        self.output.__exit__(None, None, None)

    def test_normalization(self):
        cases = {
            "http://mobile.twitter.com/Some_User/?s=20#bio": ("twitter_url", "https://x.com/Some_User"),
            "https://sp.nicovideo.jp/user/0123/video?ref=foo": ("nico_url", "https://www.nicovideo.jp/user/123"),
            "https://youtube.com/@作者/videos?si=foo。": ("yt_url", "https://www.youtube.com/@作者"),
            "https://youtube.com/channel/UC" + "a" * 22: ("yt_url", "https://www.youtube.com/channel/UC" + "a" * 22),
        }
        for raw, expected in cases.items():
            self.assertEqual(links.normalize_profile_url(raw), expected)
        for raw in ["https://x.com/user/status/1", "https://x.com/home", "https://evil.x.com/user", "https://x.com.evil/user", "https://youtube.com/watch?v=a", "https://youtu.be/abc", "https://nicovideo.jp/watch/sm1", "https://youtube.com/@a%2Fb", "https://x.com:999/user"]:
            self.assertIsNone(links.normalize_profile_url(raw), raw)

    def test_wrappers(self):
        self.assertEqual(links.unwrap_url("https://youtube.com/redirect?q=https%3A%2F%2Fx.com%2Fabc%3Fs%3D20&amp;event=about"), "https://x.com/abc?s=20")
        response = Mock(status_code=302, headers={"Location": "https://x.com/abc"})
        with patch.object(links.requests, "get", return_value=response) as fetch:
            self.assertEqual(links.unwrap_url("https://t.co/short"), "https://x.com/abc")
            self.assertEqual(fetch.call_count, 1)

    def test_profile_sections(self):
        youtube = {"metadata": {"channelMetadataRenderer": {"description": "https://x.com/owner"}}, "about": {"channelExternalLinkViewModel": {"url": "https://nicovideo.jp/user/42"}}, "recommendation": {"url": "https://x.com/other"}}
        urls = links.profile_page_urls("<script>var ytInitialData = " + json.dumps(youtube) + ";</script>", "yt_url")
        self.assertEqual(set(urls), {"https://x.com/owner", "https://nicovideo.jp/user/42"})
        nico = {"props": {"pageProps": {"user": {"description": '<a href="https://youtube.com/@owner">YouTube</a>', "profile": {"twitter": "https://x.com/owner"}}}}}
        for page in ['<script id="__NEXT_DATA__">' + json.dumps(nico) + '</script>', '<div id="js-initial-userpage-data" data-initial-data="' + html.escape(json.dumps(nico), quote=True) + '"></div>']:
            self.assertEqual(set(links.profile_page_urls(page, "nico_url")), {"https://youtube.com/@owner", "https://x.com/owner"})
        with self.assertRaises(ValueError):
            links.profile_page_urls('<a href="https://x.com/navigation">link</a>', "nico_url")

    def test_twitter_response(self):
        api = Mock(return_value={"user": {"description": "https://nicovideo.jp/user/42", "website": {"url": "https://youtube.com/@owner"}}})
        self.assertEqual(set(links.fetch_profile_urls("https://x.com/owner", api)), {"https://nicovideo.jp/user/42", "https://youtube.com/@owner"})

    def test_candidates_conflicts_and_failures(self):
        existing = dict(zip(links.FIELDS, ["https://youtube.com/@owner", None, ""]))
        with patch.object(links, "fetch_profile_urls", return_value=["https://twitter.com/Owner?s=20", "https://x.com/owner", "https://nicovideo.jp/user/42", "https://nicovideo.jp/user/43"]):
            found, conflicts, failures = links.discover_links(existing, Mock())
            self.assertEqual(found, {"twitter_url": "https://x.com/Owner"})
            self.assertEqual((conflicts, failures), (1, 0))
        with patch.object(links, "fetch_profile_urls", side_effect=TimeoutError("timeout")):
            self.assertEqual(links.discover_links(existing, Mock()), ({}, 0, 1))


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "test.db"
        self.conn = sqlite3.connect(self.path)
        self.conn.execute("CREATE TABLE authors(id INTEGER PRIMARY KEY AUTOINCREMENT, yt_name TEXT, yt_url TEXT, yt_avatar TEXT, nico_name TEXT, nico_url TEXT, nico_avatar TEXT, twitter_name TEXT, twitter_url TEXT, twitter_avatar TEXT, comment TEXT)")
        self.conn.execute("INSERT INTO authors(id,yt_name,yt_url,yt_avatar,nico_url) VALUES(0,'Owner','https://youtube.com/@owner','avatar','　')")
        self.conn.commit()
        self.output = redirect_stdout(io.StringIO()); self.output.__enter__()

    def tearDown(self):
        self.output.__exit__(None, None, None)
        self.conn.close(); self.tmp.cleanup()

    def run_update(self, **kwargs):
        with patch.object(updater, "discover_links", return_value=({"nico_url": "https://www.nicovideo.jp/user/42", "twitter_url": "https://x.com/owner"}, 0, 0)), patch.object(updater, "get_author_info_from_url", return_value=("New", "new-avatar")) as metadata:
            updater.process_authors(self.conn, update_links=True, **kwargs)
            return metadata.call_count

    def test_selection_and_zero(self):
        self.assertEqual(len(updater.get_authors_to_update(self.conn, update_links=True)), 1)
        self.assertEqual(updater.get_authors_to_update(self.conn, update_avatars=True), [])
        self.assertEqual(updater.get_authors_to_update(self.conn, author_id=0)[0][0], 0)
        self.assertEqual(updater.get_authors_to_update(self.conn, author_id_after=0, update_links=True), [])

    def test_link_only_backup_and_idempotency(self):
        self.assertEqual(self.run_update(), 0)
        self.assertEqual(self.conn.execute("SELECT nico_url,twitter_url,yt_name FROM authors").fetchone(), ("https://www.nicovideo.jp/user/42", "https://x.com/owner", "Owner"))
        backup = next(Path(self.tmp.name).glob("*.backup-*"))
        with sqlite3.connect(backup) as saved:
            self.assertEqual(saved.execute("SELECT twitter_url FROM authors").fetchone(), (None,))
        self.assertEqual(self.run_update(), 0)
        self.assertEqual(len(list(Path(self.tmp.name).glob("*.backup-*"))), 1)

    def test_dry_run_combined(self):
        before = self.path.read_bytes()
        self.assertGreater(self.run_update(dry_run=True, update_names=True, update_avatars=True), 0)
        self.assertEqual(self.path.read_bytes(), before)
        self.assertFalse(list(Path(self.tmp.name).glob("*.backup-*")))

    def test_combined_and_force_protection(self):
        self.conn.execute("UPDATE authors SET twitter_url='https://x.com/existing'");self.conn.commit()
        self.run_update(force=True, update_names=True, update_avatars=True)
        self.assertEqual(self.conn.execute("SELECT twitter_url,nico_name FROM authors").fetchone(), ("https://x.com/existing", "New"))

    def test_backup_failure(self):
        with patch.object(links, "backup_database", side_effect=OSError("backup failure")):
            with self.assertRaises(OSError):
                self.run_update()
        self.assertEqual(self.conn.execute("SELECT twitter_url FROM authors").fetchone(), (None,))

    def test_concurrent_fill_protected(self):
        def discover(*args):
            self.conn.execute("UPDATE authors SET twitter_url='https://x.com/concurrent'")
            self.conn.commit()
            return {"twitter_url": "https://x.com/discovered"}, 0, 0
        with patch.object(updater, "discover_links", side_effect=discover):
            updater.process_authors(self.conn, update_links=True)
        self.assertEqual(self.conn.execute("SELECT twitter_url FROM authors").fetchone(), ("https://x.com/concurrent",))

    def test_wal_backup(self):
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("UPDATE authors SET comment='in WAL'")
        self.conn.commit()
        backup = links.backup_database(self.conn)
        with sqlite3.connect(backup) as saved:
            self.assertEqual(saved.execute("SELECT comment FROM authors").fetchone(), ("in WAL",))


if __name__ == "__main__":
    unittest.main()
