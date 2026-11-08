import importlib
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "update" / "autofetch"))
import automation

deploy = importlib.import_module("deploy-autofetch")


class NotificationsAndDeploymentTests(unittest.TestCase):
    def test_env_update_preserves_missing_empty_and_quoted_empty_proxies(self):
        for incoming in ("", "https_proxy=\n", 'https_proxy=""\n', "# https_proxy=\n"):
            with self.subTest(
                incoming=incoming
            ), tempfile.TemporaryDirectory() as directory:
                source, target = Path(directory) / "source", Path(directory) / "target"
                source.write_text("TENCENT_DOCS_ACCESS_TOKEN=new\n" + incoming)
                target.write_text(
                    "TENCENT_DOCS_ACCESS_TOKEN=old\nhttps_proxy=http://server.test:7890\nno_proxy=localhost,docs.qq.com\n"
                )
                deploy.copy_dotenv(source, target)
                result = target.read_text()
                self.assertIn("TENCENT_DOCS_ACCESS_TOKEN=new", result)
                self.assertIn("https_proxy=http://server.test:7890", result)
                self.assertIn("no_proxy=localhost,docs.qq.com", result)
                self.assertEqual(target.stat().st_mode & 0o777, 0o600)

    def test_nonempty_local_proxy_overrides_server_even_with_different_case(self):
        with tempfile.TemporaryDirectory() as directory:
            source, target = Path(directory) / "source", Path(directory) / "target"
            source.write_text("HTTPS_PROXY=http://new.test:7890\n")
            target.write_text("https_proxy=http://old.test:7890\n")
            deploy.copy_dotenv(source, target)
            self.assertEqual(target.read_text(), "https_proxy=http://new.test:7890\n")

    def test_first_upload_failure_sends_one_mail_and_retry_still_runs(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(
            automation, "DATA", Path(directory)
        ), patch.object(automation, "notify") as notify:
            job = {
                "dates": ["20261107"],
                "deadline": None,
                "attempts": 1,
                "status": "running",
            }

            def execute(command, *args):
                if "--upload-week" in command:
                    raise RuntimeError("automation.py: exit 1")

            with patch.object(automation, "execute", side_effect=execute) as run:
                for attempt in (1, 2):
                    job["attempts"] = attempt
                    with self.assertRaises(RuntimeError):
                        automation.attempt("20261107-daily", job)
                self.assertEqual(
                    sum("--upload-week" in c.args[0] for c in run.call_args_list), 2
                )
            notify.assert_called_once()
            state = automation.load(Path(directory) / "jobs.json", {})
            self.assertEqual(state["20261107-daily"]["mail"], "sent")

    def test_processor_failure_does_not_trigger_early_upload_mail(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(
            automation, "DATA", Path(directory)
        ), patch.object(automation, "notify") as notify:
            job = {
                "dates": ["20261107"],
                "deadline": None,
                "attempts": 1,
                "status": "running",
            }

            def execute(command, *args):
                if command[1].endswith("processor.py"):
                    raise RuntimeError("processor.py: exit 2")

            with patch.object(automation, "execute", side_effect=execute):
                with self.assertRaises(RuntimeError):
                    automation.attempt("20261107-daily", job)
            notify.assert_not_called()


if __name__ == "__main__":
    unittest.main()
