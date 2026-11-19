import importlib.util
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3] / "update" / "autofetch"
spec = importlib.util.spec_from_file_location(
    "cookie_deploy", ROOT / "deploy-autofetch.py"
)
d = importlib.util.module_from_spec(spec)
spec.loader.exec_module(d)


class CookieDeploymentTests(unittest.TestCase):
    def test_export_and_update_preserves_other_settings(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            profile = root / "profile"
            (profile / "webengine").mkdir(parents=True)
            with sqlite3.connect(profile / "webengine/Cookies") as db:
                db.execute(
                    "CREATE TABLE cookies (host_key, path, is_secure, expires_utc, name, value)"
                )
                db.executemany(
                    "INSERT INTO cookies VALUES (?,?,?,?,?,?)",
                    [
                        (".bilibili.com", "/", 1, 0, "SESSDATA", "fake-session"),
                        (".bilibili.com", "/", 1, 0, "DedeUserID", "123"),
                        (".bilibili.com", "/", 1, 0, "bili_jct", "fake-csrf"),
                        (".youtube.com", "/", 1, 0, "SID", "fake-youtube"),
                    ],
                )
            target = root / "installed"
            (target / "config").mkdir(parents=True)
            (target / "config/.env").write_text("https_proxy=keep\n")
            rss = root / "rsshub.env"
            rss.write_text(
                "PORT=10120\nBILIBILI_COOKIE_999=keep\nBILIBILI_COOKIE_123=old\n"
            )
            with patch.object(d, "SOURCE", root):
                d.export_cookies(profile)
                self.assertIn("fake-youtube", (root / "cookies.txt").read_text())
                self.assertIn("bili_jct=fake-csrf", (root / "bcookies.txt").read_text())
                d.update_cookies(target, rss)
            self.assertEqual((target / "config/.env").read_text(), "https_proxy=keep\n")
            self.assertEqual((target / "cookies.txt").stat().st_mode & 0o777, 0o600)
            self.assertIn("PORT=10120\nBILIBILI_COOKIE_999=keep", rss.read_text())
            self.assertNotIn("=old", rss.read_text())
            self.assertIn("SESSDATA=fake-session", rss.read_text())

    def test_invalid_export_keeps_existing_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "webengine").mkdir()
            with sqlite3.connect(root / "webengine/Cookies") as db:
                db.execute(
                    "CREATE TABLE cookies (host_key, path, is_secure, expires_utc, name, value)"
                )
            (root / "cookies.txt").write_text("old")
            with patch.object(d, "SOURCE", root), self.assertRaises(ValueError):
                d.export_cookies(root)
            self.assertEqual((root / "cookies.txt").read_text(), "old")

    def test_remote_forwards_cookie_locations(self):
        import io
        import tarfile

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ["deploy-autofetch.py", "cookies.txt", "bcookies.txt"]:
                (root / name).write_text("fixture")
            with patch.object(d, "SOURCE", root), patch.object(
                d, "FILES", ["deploy-autofetch.py"]
            ), patch.object(d, "CONFIGS", []), patch.object(d, "run") as run:
                d.remote(
                    "server",
                    Path("/srv/autofetch"),
                    "auto",
                    cookies_only=True,
                    rsshub_cookie_target=Path("/home/user/.vault/rsshub"),
                )
            command = run.call_args.args[0][-1]
            self.assertIn("--cookies-only", command)
            self.assertIn("/srv/autofetch", command)
            self.assertIn("/home/user/.vault/rsshub", command)
            with tarfile.open(
                fileobj=io.BytesIO(run.call_args.kwargs["input"]), mode="r:gz"
            ) as archive:
                self.assertEqual(
                    archive.getnames(),
                    ["deploy-autofetch.py", "cookies.txt", "bcookies.txt"],
                )


if __name__ == "__main__":
    unittest.main()
