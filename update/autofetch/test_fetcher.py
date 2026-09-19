import csv
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

import fetcher
import processor
import upload
from time_range import parse_time_range


class FetcherTests(unittest.TestCase):
    def test_request_timeout_is_forwarded(self):
        class Response:
            text = "rss"

            def raise_for_status(self):
                pass

            def json(self):
                return {"code": 0, "data": []}

        class Session:
            def __init__(self):
                self.timeouts = []

            def get(self, url, **kwargs):
                self.timeouts.append(kwargs["timeout"])
                return Response()

        session = Session()
        self.assertEqual(
            fetcher.fetch_rss("https://rsshub.test", "123", session, 8), "rss"
        )
        self.assertEqual(
            fetcher.fetch_video_tags(
                "https://www.bilibili.com/video/BV1Ab411c7mD", session, 12
            ),
            [],
        )
        self.assertEqual(session.timeouts, [8, 12])

    def test_parse_time_range(self):
        self.assertEqual(parse_time_range("today"), "today")
        self.assertEqual(parse_time_range("all"), "all")
        self.assertEqual(parse_time_range("20260914"), "20260914")
        self.assertEqual(parse_time_range("7"), 7)

    def test_time_range_cli_is_shared_by_processor_and_upload(self):
        self.assertEqual(
            processor.parse_args(["--time-range", "today"]).time_range, "today"
        )
        upload_args = upload.parse_args(
            ["--dry-run", "--time-range", "today"]
        )
        self.assertTrue(upload_args.dry_run)
        self.assertEqual(upload_args.time_range, "today")

    def test_two_days_uses_calendar_dates(self):
        now = datetime(2026, 9, 14, 0, 5, tzinfo=fetcher.TZ_BEIJING)
        previous_day = datetime(2026, 9, 12, 16, 1, tzinfo=timezone.utc)
        two_days_ago = datetime(2026, 9, 11, 15, 59, tzinfo=timezone.utc)

        self.assertTrue(fetcher.is_within_range(previous_day, 2, now))
        self.assertFalse(fetcher.is_within_range(two_days_ago, 2, now))

    def test_retry_session_configuration(self):
        session = fetcher.create_retry_session(retries=3, backoff_factor=0.5)
        retry = session.get_adapter("https://").max_retries
        self.assertEqual(retry.total, 3)
        self.assertEqual(retry.connect, 3)
        self.assertEqual(retry.read, 3)
        self.assertEqual(retry.status, 3)
        self.assertEqual(retry.backoff_factor, 0.5)
        self.assertIn(503, retry.status_forcelist)
        session.close()

    def test_state_round_trip_and_csv_merge(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            state_path = root / "state" / "fetcher.json"
            state = {"version": 1, "users": {"123": {"seen_bvids": ["BV1"]}}}
            fetcher.save_state(state_path, state)
            self.assertEqual(fetcher.load_state(state_path), state)
            self.assertFalse(state_path.with_suffix(".json.tmp").exists())

            csv_path = root / "author-20260914.csv"
            old_row = [
                "author",
                "source",
                "old",
                "https://www.bilibili.com/video/BV1Ab411c7mD",
                "1",
            ]
            with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
                csv.writer(f).writerow(old_row)
            new_rows = [
                {
                    "title": "duplicate",
                    "link": "https://www.bilibili.com/video/BV1Ab411c7mD",
                    "translation_status": 1,
                },
                {
                    "title": "new",
                    "link": "https://www.bilibili.com/video/BV1Q541167Qg",
                    "translation_status": 1,
                },
            ]

            self.assertEqual(fetcher.update_csv(csv_path, new_rows), (1, 2))
            with open(csv_path, "r", newline="", encoding="utf-8-sig") as f:
                rows = list(csv.reader(f))
            self.assertEqual(rows[0], old_row)
            self.assertEqual(
                rows[1][2:4],
                ["new", "https://www.bilibili.com/video/BV1Q541167Qg"],
            )
            self.assertEqual(
                fetcher.load_existing_bvids(root),
                {"BV1Ab411c7mD", "BV1Q541167Qg"},
            )


if __name__ == "__main__":
    unittest.main()
