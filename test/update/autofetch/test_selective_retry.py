import csv
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


def rss(items=""):
    return "<rss><channel><title>作者</title>" + items + "</channel></rss>"


def item(bvid):
    return f"<item><title>第一话</title><link>https://www.bilibili.com/video/{bvid}</link><pubDate>Sat, 07 Nov 2026 12:00:00 GMT</pubDate></item>"


class SelectiveRetryTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def fetch_args(self):
        return [
            "--resume",
            "--report",
            str(self.root / "fetch.json"),
            "--time-range",
            "20261107",
            "--output-dir",
            str(self.root / "output"),
            "--state-file",
            str(self.root / "state.json"),
        ]

    def test_alternating_author_failures_accumulate_success(self):
        config = {"users": ["a", "b"]}
        with patch.object(fetcher, "load_jsonc", return_value=config), patch.object(
            fetcher, "fetch_rss", side_effect=[rss(), RuntimeError("network")]
        ):
            with self.assertRaises(SystemExit):
                fetcher.main(self.fetch_args())

        # Author a would now fail if requested, but only b should be retried.
        def retry(base, uid, *args, **kwargs):
            self.assertEqual(uid, "b")
            return rss()

        with patch.object(fetcher, "load_jsonc", return_value=config), patch.object(
            fetcher, "fetch_rss", side_effect=retry
        ) as request:
            fetcher.main(self.fetch_args())
            request.assert_called_once()
        report = json.loads((self.root / "fetch.json").read_text())
        self.assertTrue(report["complete"])
        self.assertEqual(report["completed_users"], 2)

    def test_failed_tag_reuses_successful_rss_and_does_not_repeat_successful_video(
        self,
    ):
        config = {"users": [{"id": "a", "tag_keywords": ["MMD"]}]}
        video1, video2 = "BV1Ab411c7mD", "BV1ssWL6yEgM"
        with patch.object(fetcher, "load_jsonc", return_value=config), patch.object(
            fetcher, "fetch_rss", return_value=rss(item(video1) + item(video2))
        ), patch.object(
            fetcher, "fetch_video_tags", side_effect=[["MMD"], RuntimeError("network")]
        ):
            with self.assertRaises(SystemExit):
                fetcher.main(self.fetch_args())
        with patch.object(fetcher, "load_jsonc", return_value=config), patch.object(
            fetcher, "fetch_rss"
        ) as request, patch.object(
            fetcher, "fetch_video_tags", return_value=["MMD"]
        ) as tags:
            fetcher.main(self.fetch_args())
            request.assert_not_called()
            self.assertEqual(tags.call_count, 1)
            self.assertIn(video2, tags.call_args.args[0])
        self.assertTrue(json.loads((self.root / "fetch.json").read_text())["complete"])
        self.assertEqual(
            sum(len(upload.read_csv(p)) for p in (self.root / "output").glob("*.csv")),
            2,
        )

    def test_legacy_failure_report_restarts_safely_once(self):
        (self.root / "fetch.json").write_text(
            json.dumps(
                {
                    "complete": False,
                    "time_range": "20261107",
                    "failures": [{"uid": "a"}],
                }
            )
        )
        with patch.object(
            fetcher, "load_jsonc", return_value={"users": ["a"]}
        ), patch.object(fetcher, "fetch_rss", return_value=rss()) as request:
            fetcher.main(self.fetch_args())
            request.assert_called_once()

    def processor_setup(self):
        (self.root / "config").mkdir()
        (self.root / "config/processor.jsonc").write_text(
            json.dumps(
                {
                    "extraction_rules": [
                        {"pattern": "(https://original.test/\\w+)", "group": 1}
                    ],
                    "request_delay": 0,
                }
            )
        )
        output = self.root / "output"
        output.mkdir()
        return output, [
            "--resume",
            "--report",
            str(self.root / "process.json"),
            "--time-range",
            "all",
            "--csv-dir",
            str(output),
        ]

    def test_processor_retries_only_failed_video_and_keeps_successful_csv(self):
        output, args = self.processor_setup()
        path = output / "作者-20261107.csv"
        with path.open("w", newline="") as stream:
            csv.writer(stream).writerows(
                [
                    ["", "", "第一话", "https://bili.test/1", "1"],
                    ["", "", "第二话", "https://bili.test/2", "1"],
                ]
            )
        with patch.object(
            processor, "__file__", str(self.root / "processor.py")
        ), patch.object(processor, "check_ytdlp", return_value=True), patch.object(
            processor, "get_author_from_original_link", return_value="原作者"
        ):
            with patch.object(
                processor,
                "get_description",
                side_effect=["https://original.test/1", None],
            ):
                with self.assertRaises(SystemExit):
                    processor.main(args)
            with patch.object(
                processor, "get_description", return_value="https://original.test/2"
            ) as request:
                processor.main(args)
                request.assert_called_once_with("https://bili.test/2", None)
        self.assertTrue(
            json.loads((self.root / "process.json").read_text())["complete"]
        )

    def test_missing_original_is_manual_until_csv_is_corrected(self):
        output, args = self.processor_setup()
        path = output / "作者-20261107.csv"
        path.write_text(",,第一话,https://bili.test/1,1\n")
        with patch.object(
            processor, "__file__", str(self.root / "processor.py")
        ), patch.object(processor, "check_ytdlp", return_value=True), patch.object(
            processor, "get_description", return_value="没有原链接"
        ) as request:
            for _ in range(2):
                with self.assertRaises(SystemExit) as result:
                    processor.main(args)
                self.assertEqual(result.exception.code, 3)
            request.assert_called_once()
            path.write_text(
                "原作者,https://original.test/1,第一话,https://bili.test/1,1\n"
            )
            processor.main(args)
            request.assert_called_once()
        self.assertTrue(
            json.loads((self.root / "process.json").read_text())["complete"]
        )

    def test_manual_only_job_stops_and_notifies_without_waiting_six_rounds(self):
        data = self.root / "state"
        current = datetime(2026, 11, 6, 23, tzinfo=a.TZ)

        def attempt(key, job):
            a.save(
                data / "jobs" / key / "process-week.json",
                {
                    "complete": False,
                    "failures": [
                        {
                            "stage": "original_link_missing",
                            "retryable": False,
                            "video": "https://bili.test/1",
                        }
                    ],
                },
            )
            raise RuntimeError("processor.py: exit 3")

        with patch.object(a, "DATA", data), patch.object(
            a, "now", return_value=current
        ), patch.object(a, "attempt", side_effect=attempt), patch.object(
            a, "notify"
        ) as notify:
            a.tick()
            job = a.load(data / "jobs.json", {})["20261106-daily"]
            self.assertEqual(job["status"], "needs_attention")
            self.assertEqual(job["attempts"], 1)
            notify.assert_called_once()

    def test_email_lists_actionable_video_failure_not_raw_json(self):
        key = "20261107-daily"
        data = self.root / "state"
        a.save(
            data / "jobs" / key / "process-week.json",
            {
                "completed_videos": 5,
                "total_videos": 6,
                "failures": [
                    {
                        "stage": "original_link_missing",
                        "retryable": False,
                        "title": "第六话",
                        "author": "作者",
                        "video": "https://bili.test/6",
                        "file": "作者-20261107.csv",
                        "row": 2,
                    }
                ],
            },
        )
        env = {
            "AUTOFETCH_MAIL_FROM": "sender@example.test",
            "AUTOFETCH_MAIL_TO": "recipient@example.test",
            "AUTOFETCH_MAIL_USER": "sender@example.test",
            "AUTOFETCH_MAIL_PASSWORD": "secret-value",
        }
        with patch.object(a, "DATA", data), patch.dict(os.environ, env), patch.object(
            upload, "load_dotenv"
        ), patch.object(a.smtplib, "SMTP_SSL") as smtp:
            a.notify(
                key, {"dates": ["20261107"], "attempts": 1, "status": "needs_attention"}
            )
            message = (
                smtp.return_value.__enter__.return_value.send_message.call_args.args[0]
            )
            body = message.get_content()
            self.assertIn("5/6", body)
            self.assertIn("第六话", body)
            self.assertIn("作者-20261107.csv 第 2 行", body)
            self.assertIn("请人工填写", body)
            self.assertNotIn("secret-value", body)
            self.assertNotIn('"failures"', body)

    def test_completed_date_is_not_refetched_when_other_date_retries(self):
        data = self.root / "state"
        job = {
            "dates": ["20261106", "20261107"],
            "deadline": None,
            "attempts": 1,
            "status": "running",
        }
        calls = []

        def execute(command, *args):
            if command[1].endswith("fetcher.py"):
                date = command[command.index("--time-range") + 1]
                calls.append(date)
                a.save(
                    Path(command[command.index("--report") + 1]),
                    {"complete": date == "20261106" or len(calls) > 2},
                )
                if len(calls) == 2:
                    raise RuntimeError("fetcher.py: exit 2")

        with patch.object(a, "DATA", data), patch.object(
            a, "execute", side_effect=execute
        ):
            with self.assertRaises(RuntimeError):
                a.attempt("job", job)
            a.attempt("job", job)
        self.assertEqual(calls, ["20261106", "20261107", "20261107"])

    def test_upload_includes_ready_rows_without_uploading_incomplete_video(self):
        directory = self.root / "week"
        (directory / "output").mkdir(parents=True)
        with (directory / "output" / "a-20261107.csv").open("w", newline="") as stream:
            csv.writer(stream).writerows(
                [
                    [
                        "作者",
                        "https://original.test/1",
                        "第一话",
                        "https://bili.test/1",
                        "1",
                    ],
                    ["", "", "第二话", "https://bili.test/2", "1"],
                ]
            )
        with patch.object(
            upload, "load_upload_config", return_value={"file_id": "f", "sheet_id": "s"}
        ), patch.object(a, "read_remote", return_value=[]), patch.object(
            upload, "upload_to_tdocs", return_value=True
        ) as send, patch.object(
            upload, "order_sheet", return_value=True
        ):
            a.upload_week(directory)
            rows = send.call_args.args[0]
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0][3], "https://bili.test/1")


if __name__ == "__main__":
    unittest.main()
