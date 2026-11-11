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

deploy_autofetch = importlib.import_module("deploy-autofetch")
import env as env_config
import processor
import requests


class EnvironmentTests(unittest.TestCase):
    def test_proxy_loading_preserves_existing_environment_and_handles_missing_file(
        self,
    ):
        with tempfile.TemporaryDirectory() as directory, patch.dict(
            os.environ, {}, clear=True
        ):
            dotenv = Path(directory) / ".env"
            env_config.load_dotenv(dotenv, quiet=True)
            dotenv.write_text(
                'http_proxy="http://proxy.test:7890"\nhttps_proxy=http://proxy.test:7890\nno_proxy=localhost,127.0.0.1\n'
            )
            os.environ["http_proxy"] = "http://inherited.test:8080"
            env_config.load_dotenv(dotenv)
            settings = requests.Session().merge_environment_settings(
                "https://example.test", {}, False, True, None
            )
            self.assertEqual(settings["proxies"]["http"], "http://inherited.test:8080")
            self.assertEqual(settings["proxies"]["https"], "http://proxy.test:7890")
            direct = requests.Session().merge_environment_settings(
                "https://localhost", {}, False, True, None
            )
            self.assertEqual(direct["proxies"], {})

    def test_processor_loads_script_relative_env_and_ytdlp_child_inherits_proxy(self):
        real_run = subprocess.run
        with tempfile.TemporaryDirectory() as directory, patch.dict(
            os.environ, {}, clear=True
        ):
            root = Path(directory)
            (root / "config").mkdir()
            (root / "output").mkdir()
            (root / "config/processor.jsonc").write_text('{"extraction_rules": [{}]}')
            (root / "config/.env").write_text("https_proxy=http://proxy.test:7890\n")

            def child(command, **kwargs):
                self.assertEqual(command[0], "yt-dlp")
                self.assertNotIn("env", kwargs)  # Inherit the parent environment.
                return real_run(
                    [
                        sys.executable,
                        "-c",
                        'import os; print(os.environ["https_proxy"])',
                    ],
                    **kwargs
                )

            def check():
                with patch.object(processor.subprocess, "run", side_effect=child):
                    self.assertEqual(
                        processor.ytdlp_get_field("https://video.test", "description"),
                        "http://proxy.test:7890",
                    )
                return True

            with patch.object(
                processor, "__file__", str(root / "processor.py")
            ), patch.object(processor, "check_ytdlp", side_effect=check):
                processor.main(["--time-range", "all"])

    def test_deployment_includes_shared_environment_module(self):
        with patch.object(deploy_autofetch, "run") as run:
            deploy_autofetch.remote("server", Path("/home/user/autofetch"), "auto")
        with tarfile.open(
            fileobj=io.BytesIO(run.call_args.kwargs["input"]), mode="r:gz"
        ) as archive:
            self.assertIn("env.py", archive.getnames())
            self.assertIn("time-range.py", archive.getnames())
            self.assertNotIn("time_range.py", archive.getnames())
            self.assertNotIn("config/.env", archive.getnames())


if __name__ == "__main__":
    unittest.main()
