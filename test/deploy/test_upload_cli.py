"""CLI diagnostics must not require a real server or credentials."""

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class UploadCliTest(unittest.TestCase):
    def test_help_explains_database_scope_without_credentials(self):
        with tempfile.TemporaryDirectory() as directory:
            env = dict(os.environ, PROJECT_ROOT=directory)
            result = subprocess.run(
                ["bash", str(ROOT / "update/scripts/upload.sh"), "--help"],
                env=env,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("frontend, backend and database", result.stdout)
            self.assertIn("database-only", result.stdout)

    def test_missing_tool_is_reported_instead_of_silent_exit(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tools = root / "bin"
            tools.mkdir()
            (tools / "dirname").symlink_to(shutil.which("dirname"))
            env = dict(
                os.environ,
                PROJECT_ROOT=directory,
                PATH=str(tools),
                REMOTE_SERVER="test.invalid",
                SSH_KEY="/unused",
                SSH_PORT="22222",
            )
            result = subprocess.run(
                [shutil.which("bash"), str(ROOT / "update/scripts/upload.sh")],
                env=env,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Missing local dependency: ssh", result.stderr)
            self.assertIn("deploy frontend, backend and database", result.stdout)

    def run_flow(self, mode=None, fail_code=False):
        import sqlite3

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tools = root / "bin"
            tools.mkdir()
            for part in ("frontend", "backend/src", "deploy"):
                (root / part).mkdir(parents=True)
            for name in (
                "server.cjs",
                "package.json",
                "package-lock.json",
                "ecosystem.config.js",
            ):
                (root / "backend" / name).write_text("fixture")
            (root / "deploy/deploy.sh").write_text("# mock deployment")
            (root / "deploy/replace-database.sh").write_text("# mock replacement")
            with sqlite3.connect(root / "backend/random-2hu-stuff.db") as db:
                db.execute("CREATE TABLE fixture(id)")
            log = root / "calls"
            commands = {
                "ssh": """echo "ssh $*" >> "$CALLS"
case "$*" in
  *mktemp*) echo /var/www/random-2hu-stuff/backend/.database-upload.TEST1234 ;;
  *"bash -s"*) cat >/dev/null; echo database-replaced >> "$CALLS" ;;
  *"bash '/root/"*) echo code-deployed >> "$CALLS"; exit "$FAIL_CODE" ;;
esac
""",
                "rsync": 'echo "rsync $*" >> "$CALLS"\n',
                "ssh-add": "exit 0\n",
                "ssh-agent": "exit 0\n",
            }
            for name, body in commands.items():
                path = tools / name
                path.write_text("#!" + shutil.which("bash") + "\n" + body)
                path.chmod(0o755)
            env = dict(
                os.environ,
                PROJECT_ROOT=str(root),
                PATH=str(tools) + ":" + os.environ["PATH"],
                REMOTE_SERVER="test.invalid",
                SSH_KEY="/unused",
                SSH_PORT="22222",
                SSH_AUTH_SOCK="/mock-agent",
                CALLS=str(log),
                FAIL_CODE="1" if fail_code else "0",
            )
            args = ["bash", str(ROOT / "update/scripts/upload.sh")]
            if mode:
                args.append(mode)
            result = subprocess.run(args, env=env, capture_output=True, text=True)
            calls = log.read_text() if log.exists() else ""
            if not fail_code:
                self.assertEqual(result.returncode, 0, result.stderr)
            if fail_code:
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("code-deployed", calls)
                self.assertNotIn("database-replaced", calls)
                return
            self.assertEqual(result.returncode, 0, result.stderr)
            if mode in (None, "all"):
                self.assertLess(
                    calls.index("code-deployed"), calls.index("database-replaced")
                )
                self.assertIn("database.db", calls)
            elif mode == "upload-only":
                self.assertNotIn("code-deployed", calls)
                self.assertNotIn("database-replaced", calls)
                self.assertNotIn("database.db", calls)
            elif mode == "database-only":
                self.assertIn("database-replaced", calls)
                self.assertNotIn("code-deployed", calls)

    def test_default_deploys_code_then_database(self):
        self.run_flow()

    def test_all_deploys_code_then_database(self):
        self.run_flow("all")

    def test_upload_only_keeps_database_unchanged(self):
        self.run_flow("upload-only")

    def test_database_only_skips_code(self):
        self.run_flow("database-only")

    def test_failed_code_deployment_does_not_replace_database(self):
        self.run_flow("all", fail_code=True)
