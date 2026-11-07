import io
import os
import subprocess
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "update" / "autofetch"))
import importlib

deploy = importlib.import_module("deploy-autofetch")


class DeployAutofetchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.target = Path(self.temp.name) / "installed"

    def test_cron_preserves_other_jobs_and_is_idempotent(self):
        old = "MAILTO=test@example.test\n0 1 * * * unrelated-command\n"
        python = self.target / ".runtime/bin/python"
        first = deploy.cron_text(old, self.target, python)
        self.assertEqual(deploy.cron_text(first, self.target, python), first)
        self.assertIn(old, first)
        self.assertEqual(first.count(deploy.MARKER), 1)
        self.assertIn("PATH=", first)
        with self.assertRaises(ValueError):
            deploy.cron_text(old, Path("/tmp/a%b"), python)

    def test_install_preserves_data_configs_and_credentials(self):
        (self.target / "config").mkdir(parents=True)
        (self.target / "config/fetcher.jsonc").write_text("existing custom rules")
        (self.target / "config/.env").write_text("existing secret")
        (self.target / "output").mkdir()
        (self.target / "output/data.csv").write_text("existing data")
        current = subprocess.CompletedProcess([], 0, "0 1 * * * unrelated\n", "")
        with patch.object(deploy.subprocess, "run", return_value=current), patch.object(
            deploy, "run"
        ) as run, patch.object(deploy, "validate"):
            deploy.install(self.target, "nix")
        self.assertEqual(
            (self.target / "config/fetcher.jsonc").read_text(), "existing custom rules"
        )
        self.assertEqual((self.target / "config/.env").read_text(), "existing secret")
        self.assertEqual((self.target / "output/data.csv").read_text(), "existing data")
        self.assertEqual((self.target / "config/.env").stat().st_mode & 0o777, 0o600)
        self.assertEqual(run.call_args_list[-1].args[0], ["crontab", "-"])
        self.assertNotIn(
            "automation.py --retry", run.call_args_list[-1].kwargs["input"]
        )

    def test_validation_failure_does_not_install_cron(self):
        current = subprocess.CompletedProcess([], 1, "", "no crontab for test")
        with patch.object(deploy.subprocess, "run", return_value=current), patch.object(
            deploy, "run"
        ) as run, patch.object(
            deploy, "validate", side_effect=RuntimeError("missing config")
        ):
            with self.assertRaises(RuntimeError):
                deploy.install(self.target, "venv")
        self.assertFalse(
            any(call.args[0] == ["crontab", "-"] for call in run.call_args_list)
        )

    def test_crontab_read_error_does_not_overwrite_existing_jobs(self):
        current = subprocess.CompletedProcess([], 1, "", "permission denied")
        with patch.object(deploy.subprocess, "run", return_value=current), patch.object(
            deploy, "run"
        ) as run:
            with self.assertRaises(RuntimeError):
                deploy.install(self.target, "nix")
            run.assert_not_called()

    def test_remote_archive_excludes_local_state_and_credentials_by_default(self):
        with patch.object(deploy, "run") as run:
            deploy.remote("voile", Path("/home/howl/autofetch"), "auto")
        args = run.call_args.args[0]
        self.assertEqual(args[:2], ["ssh", "voile"])
        with tarfile.open(
            fileobj=io.BytesIO(run.call_args.kwargs["input"]), mode="r:gz"
        ) as archive:
            names = archive.getnames()
        self.assertIn("automation.py", names)
        self.assertNotIn("cookies.txt", names)
        self.assertNotIn("config/.env", names)
        self.assertFalse(any(name.startswith("state/") for name in names))

    def test_invalid_host_is_rejected_without_ssh(self):
        with patch.object(deploy, "run") as run:
            with self.assertRaises(ValueError):
                deploy.remote("-oProxyCommand=bad", self.target, "auto")
            run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
