import json
import os
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "update" / "autofetch"))
import automation as a
import fetcher
import processor
import upload


class AutomationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.data = Path(self.temp.name)
        self.patch = patch.object(a, "DATA", self.data)
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def test_dates_and_sunday_week_boundary(self):
        sat = datetime(2026, 11, 7, 23, tzinfo=a.TZ)
        sun = datetime(2026, 11, 8, 23, tzinfo=a.TZ)
        self.assertEqual([d.day for d in a.dates_for(sat.date())], [6, 7])
        self.assertEqual([d.day for d in a.dates_for(sun.date())], [8])
        self.assertNotEqual(a.week(sat.date()), a.week(sun.date()))
        state = {}
        a.discover(state, sun.replace(hour=0, minute=10))
        self.assertEqual(state["20261108-closeout"]["dates"], ["20261107"])
        self.assertEqual(state["20261107-daily"]["dates"], ["20261106", "20261107"])
        a.discover(state, sun)
        self.assertEqual(state["20261108-daily"]["dates"], ["20261108"])

    def test_retries_then_single_failure_mail(self):
        current = datetime(2026, 11, 6, 23, tzinfo=a.TZ)
        with patch.object(a, "now", return_value=current) as clock, patch.object(
            a, "attempt", side_effect=RuntimeError("fetcher.py: exit 2")
        ) as run, patch.object(a, "notify") as mail:
            a.tick()
            a.tick()
            self.assertEqual(run.call_count, 1)
            clock.return_value = current.replace(minute=20)
            a.tick()
            clock.return_value = current.replace(minute=40)
            a.tick()
            a.tick()
            self.assertEqual(run.call_count, 3)
            mail.assert_called_once()
            job = a.load(self.data / "jobs.json", {})["20261106-daily"]
            self.assertEqual(job["status"], "failed")
            self.assertEqual(job["dates"], ["20261105", "20261106"])

    def test_cutoff_does_not_start_closeout(self):
        current = datetime(2026, 11, 8, 3, tzinfo=a.TZ)
        with patch.object(a, "now", return_value=current), patch.object(
            a, "attempt"
        ) as run, patch.object(a, "notify") as mail:
            a.tick()
            self.assertFalse(
                any(call.args[0].endswith("closeout") for call in run.call_args_list)
            )
            mail.assert_called_once()
            self.assertEqual(
                a.load(self.data / "closeout.json", {})["20261108-closeout"]["status"],
                "failed",
            )

    def test_manual_resume_keeps_dates_and_clears_deadline(self):
        state = {
            "20261108-closeout": {
                "status": "failed",
                "dates": ["20261107"],
                "deadline": "2026-11-08T03:00:00+08:00",
                "attempts": 9,
                "kind": "closeout",
                "next": "2026-11-08T00:10:00+08:00",
            }
        }
        a.save(self.data / "jobs.json", state)
        with patch.object(a, "discover"), patch.object(a, "attempt") as run:
            a.tick("20261108-closeout")
            self.assertEqual(run.call_args.args[1]["dates"], ["20261107"])
            self.assertIsNone(run.call_args.args[1]["deadline"])

    def test_uncertain_upload_never_blindly_reposts(self):
        directory = self.data / "week"
        directory.mkdir()
        row = ["author", "https://source.test", "title", "https://bili.test", "1"]
        a.save(
            directory / "uploaded.json",
            {
                "pending": [row],
                "pending_payload": [row],
                "baseline": [],
                "confirmed": [],
                "order_pending": False,
            },
        )
        with patch.object(
            upload, "load_upload_config", return_value={"file_id": "f", "sheet_id": "s"}
        ), patch.object(a, "read_remote", return_value=[]), patch.object(
            upload, "upload_to_tdocs"
        ) as post:
            with self.assertRaisesRegex(RuntimeError, "upload_uncertain"):
                a.upload_week(directory)
            post.assert_not_called()

    def test_successful_readback_confirms_without_repost(self):
        directory = self.data / "week"
        (directory / "output").mkdir(parents=True)
        row = ["author", "https://source.test", "title", "https://bili.test", "1"]
        a.save(
            directory / "uploaded.json",
            {
                "pending": [row],
                "pending_payload": [row],
                "baseline": [],
                "confirmed": [],
                "order_pending": False,
            },
        )
        with patch.object(
            upload, "load_upload_config", return_value={"file_id": "f", "sheet_id": "s"}
        ), patch.object(
            a, "read_remote", return_value=[[{"text": c} for c in row]]
        ), patch.object(
            upload, "upload_to_tdocs"
        ) as post, patch.object(
            upload, "order_sheet", return_value=True
        ):
            a.upload_week(directory)
            post.assert_not_called()
            self.assertEqual(
                a.load(directory / "uploaded.json", {})["confirmed"], [row]
            )

    def test_preexisting_identical_row_cannot_confirm_new_upload(self):
        directory = self.data / "week"
        directory.mkdir()
        row = ["a", "u", "t", "b", "1"]
        a.save(
            directory / "uploaded.json",
            {
                "pending": [row],
                "pending_payload": [row],
                "baseline": [[row, 1]],
                "confirmed": [],
                "order_pending": False,
            },
        )
        with patch.object(upload, "load_upload_config", return_value={}), patch.object(
            a, "read_remote", return_value=[[{"text": c} for c in row]]
        ):
            with self.assertRaisesRegex(RuntimeError, "upload_uncertain"):
                a.upload_week(directory)

    def test_failed_remote_read_prevents_post(self):
        directory = self.data / "week"
        (directory / "output").mkdir(parents=True)
        (directory / "output" / "a-20261107.csv").write_text(
            "author,https://source.test,title,https://bili.test,1\n"
        )
        with patch.object(upload, "load_upload_config", return_value={}), patch.object(
            a, "read_remote", side_effect=RuntimeError("incomplete_sheet_read")
        ), patch.object(upload, "upload_to_tdocs") as post:
            with self.assertRaises(RuntimeError):
                a.upload_week(directory)
            post.assert_not_called()
            self.assertFalse((directory / "uploaded.json").exists())

    def test_mail_is_mocked_and_excludes_credentials(self):
        job = {
            "dates": ["20261107"],
            "attempts": 3,
            "status": "failed",
            "error": "fetcher.py: exit 2",
        }
        env = {
            "AUTOFETCH_MAIL_FROM": "sender@example.test",
            "AUTOFETCH_MAIL_TO": "recipient@example.test",
            "AUTOFETCH_MAIL_USER": "sender@example.test",
            "AUTOFETCH_MAIL_PASSWORD": "secret-do-not-leak",
        }
        with patch.dict(os.environ, env), patch.object(
            upload, "load_dotenv"
        ), patch.object(a.smtplib, "SMTP_SSL") as smtp:
            a.notify("20261107-daily", job)
            client = smtp.return_value.__enter__.return_value
            client.login.assert_called_once_with(
                env["AUTOFETCH_MAIL_USER"], env["AUTOFETCH_MAIL_PASSWORD"]
            )
            text = str(client.send_message.call_args.args[0])
            self.assertNotIn(env["AUTOFETCH_MAIL_PASSWORD"], text)
            self.assertIn("recipient@example.test", text)

    def test_partial_fetch_reports_failure_and_retries(self):
        config = {"users": ["123", "456"], "time_range": "20261107"}
        args = [
            "--time-range",
            "20261107",
            "--output-dir",
            str(self.data / "out"),
            "--state-file",
            str(self.data / "fetch.json"),
            "--report",
            str(self.data / "report.json"),
        ]
        rss = "<rss><channel><title>author</title><item><title>title</title><link>https://www.bilibili.com/video/BV1Ab411c7mD</link><pubDate>Sat, 07 Nov 2026 12:00:00 GMT</pubDate></item></channel></rss>"
        with patch.object(fetcher, "load_jsonc", return_value=config), patch.object(
            fetcher, "fetch_rss", side_effect=[rss, RuntimeError("network")]
        ):
            with self.assertRaises(SystemExit) as error:
                fetcher.main(args)
            self.assertEqual(error.exception.code, 2)
        report = a.load(self.data / "report.json", {})
        self.assertFalse(report["complete"])
        self.assertEqual(report["failures"][0]["uid"], "456")
        with patch.object(fetcher, "load_jsonc", return_value=config), patch.object(
            fetcher, "fetch_rss", return_value=rss
        ):
            fetcher.main(args)
        self.assertTrue(a.load(self.data / "report.json", {})["complete"])
        files = list((self.data / "out").glob("*.csv"))
        self.assertEqual(len(files), 1)
        self.assertEqual(len(upload.read_csv(files[0])), 1)

    def test_upload_checkpoint_precedes_post_and_order_retry_does_not_append(self):
        directory = self.data / "week"
        (directory / "output").mkdir(parents=True)
        row = ["author", "https://source.test", "title", "https://bili.test", "1"]
        (directory / "output" / "a-20261107.csv").write_text(",".join(row) + "\n")

        def post(rows, config, **kwargs):
            self.assertEqual(a.load(directory / "uploaded.json", {})["pending"], [row])
            self.assertEqual(kwargs["start_row"], 0)
            return True

        with patch.object(
            upload, "load_upload_config", return_value={"file_id": "f", "sheet_id": "s"}
        ), patch.object(a, "read_remote", return_value=[]), patch.object(
            upload, "upload_to_tdocs", side_effect=post
        ) as send, patch.object(
            upload, "order_sheet", side_effect=[False, True]
        ):
            with self.assertRaisesRegex(RuntimeError, "online_order_failed"):
                a.upload_week(directory)
            a.upload_week(directory)
            self.assertEqual(send.call_count, 1)
            self.assertFalse(a.load(directory / "uploaded.json", {})["order_pending"])

    def test_processor_preserves_original_url_when_retrying_author(self):
        output = self.data / "output"
        output.mkdir()
        path = output / "a-20261107.csv"
        path.write_text(",https://manual.test,title,https://bili.test,1\n")
        report = self.data / "process.json"
        config = {"skip_existing": True, "extraction_rules": [{}], "request_delay": 0}
        with patch.object(processor, "load_jsonc", return_value=config), patch.object(
            processor, "check_ytdlp", return_value=True
        ), patch.object(processor, "get_description") as description, patch.object(
            processor, "get_author_from_original_link", return_value="author"
        ):
            processor.main(
                [
                    "--time-range",
                    "all",
                    "--csv-dir",
                    str(output),
                    "--report",
                    str(report),
                ]
            )
            description.assert_not_called()
        self.assertIn("author,https://manual.test", path.read_text())
        self.assertTrue(a.load(report, {})["complete"])

    def test_processor_reports_unresolved_description(self):
        output = self.data / "output"
        output.mkdir()
        (output / "a-20261107.csv").write_text(",,title,https://bili.test,1\n")
        report = self.data / "process.json"
        config = {"extraction_rules": [{}], "request_delay": 0}
        with patch.object(processor, "load_jsonc", return_value=config), patch.object(
            processor, "check_ytdlp", return_value=True
        ), patch.object(processor, "get_description", return_value=None):
            with self.assertRaises(SystemExit) as error:
                processor.main(
                    [
                        "--time-range",
                        "all",
                        "--csv-dir",
                        str(output),
                        "--report",
                        str(report),
                    ]
                )
            self.assertEqual(error.exception.code, 2)
        self.assertEqual(
            a.load(report, {})["failures"][0]["video"], "https://bili.test"
        )

    def test_timeout_kills_process_group(self):
        import subprocess
        from unittest.mock import Mock

        process = Mock(pid=12345)
        process.wait.side_effect = [subprocess.TimeoutExpired("test", 1), 0]
        current = datetime(2026, 11, 8, 2, 59, tzinfo=a.TZ)
        with patch.object(a, "now", return_value=current), patch.object(
            a.subprocess, "Popen", return_value=process
        ), patch.object(a.os, "killpg") as kill:
            with self.assertRaisesRegex(RuntimeError, "deadline_or_stage_timeout"):
                a.execute(
                    ["python", "fetcher.py"], None, current.replace(hour=3, minute=0)
                )
            kill.assert_called_once_with(12345, a.signal.SIGKILL)

    def test_mail_failure_is_recorded_without_resending(self):
        current = datetime(2026, 11, 8, 3, tzinfo=a.TZ)
        with patch.object(a, "now", return_value=current), patch.object(
            a, "attempt"
        ), patch.object(a, "notify", side_effect=OSError("secret-do-not-leak")) as mail:
            a.tick()
            a.tick()
            mail.assert_called_once()
        state = a.load(self.data / "jobs.json", {})
        self.assertEqual(state["20261108-closeout"]["mail"], "failed: OSError")
        self.assertNotIn("secret-do-not-leak", json.dumps(state))

    def test_lock_excludes_another_tick(self):
        with (self.data / "lock").open("w") as held:
            a.fcntl.flock(held, a.fcntl.LOCK_EX | a.fcntl.LOCK_NB)
            with patch.object(sys, "argv", ["automation.py"]), patch.object(
                a.os, "chdir"
            ), patch.object(a, "tick") as tick, patch.dict(os.environ):
                a.main()
                tick.assert_not_called()

    def test_saturday_daily_cannot_run_past_sunday_cutoff(self):
        state = {}
        a.discover(state, datetime(2026, 11, 7, 23, tzinfo=a.TZ))
        self.assertEqual(
            state["20261107-daily"]["deadline"], "2026-11-08T03:00:00+08:00"
        )


if __name__ == "__main__":
    unittest.main()
