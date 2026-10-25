"""Exercise real file deployment with fake services and package installation."""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class DeploymentTest(unittest.TestCase):
    def run_deploy(self, broken=False):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, live, tools = [root / name for name in ("source", "live", "bin")]
            for path in (
                source / "frontend/dist",
                source / "backend/src",
                live / "backend",
                tools,
            ):
                path.mkdir(parents=True)
            (source / "frontend/dist/index.html").write_text("new page")
            for name in (
                "server.cjs",
                "package.json",
                "package-lock.json",
                "ecosystem.config.js",
            ):
                (source / "backend" / name).write_text("new code")
            (source / "backend/src/app.cjs").write_text("new module")
            (source / "backend/random-2hu-stuff.db").write_text("wrong database")
            for suffix in ("", "-wal", "-shm"):
                (live / f"backend/random-2hu-stuff.db{suffix}").write_text(
                    "live data" + suffix
                )
            (live / "backend/server.cjs").write_text("old code")
            log = root / "calls"
            for name in ("node", "npm", "pm2", "nginx", "curl"):
                script = tools / name
                script.write_text(
                    '#!/bin/sh\necho "'
                    + name
                    + ' $*" >> "$CALLS"\n'
                    + ("exit 1\n" if broken and name == "npm" else "exit 0\n")
                )
                script.chmod(0o755)
            # Only replace host identity checks; all deployment logic and rsync are real.
            script = root / "deploy.sh"
            text = (ROOT / "deploy/deploy.sh").read_text()
            text = text.replace("[[ $EUID == 0 ]]", "[[ 1 == 1 ]]")
            text = text.replace("source /etc/os-release", "ID=debian")
            script.write_text(text)
            env = dict(
                os.environ,
                PATH=str(tools) + ":" + os.environ["PATH"],
                PROJECT_ROOT=str(source),
                DEPLOY_TARGET=str(live),
                BACKUP_ROOT=str(root / "backups"),
                CALLS=str(log),
            )
            result = subprocess.run(
                ["bash", str(script)], env=env, capture_output=True, text=True
            )
            for suffix in ("", "-wal", "-shm"):
                self.assertEqual(
                    (live / f"backend/random-2hu-stuff.db{suffix}").read_text(),
                    "live data" + suffix,
                )
            calls = log.read_text()
            if broken:
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual((live / "backend/server.cjs").read_text(), "old code")
                self.assertNotIn("pm2 restart", calls)
            else:
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(
                    (live / "frontend/dist/index.html").read_text(), "new page"
                )
                self.assertTrue((live / "backend/src/app.cjs").exists())
                self.assertIn("pm2 restart r2s-api", calls)
                self.assertFalse(list((root / "backups").rglob("*.db*")))
                self.assertNotIn("nginx reload", calls)

    def test_code_update_preserves_database(self):
        self.run_deploy()

    def test_build_failure_keeps_live_code(self):
        self.run_deploy(broken=True)
