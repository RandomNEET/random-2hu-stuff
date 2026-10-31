import argparse
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "update" / "autofetch"))

import fetcher
import processor
import upload
from time_range import parse_time_range


class YesterdayTests(unittest.TestCase):
    def test_shared_cli(self):
        self.assertEqual(parse_time_range(" Yesterday "), "yesterday")
        for module in (fetcher, processor, upload):
            with self.subTest(module=module.__name__):
                self.assertEqual(
                    module.parse_args(["--time-range", "yesterday"]).time_range,
                    "yesterday",
                )
        with self.assertRaises(argparse.ArgumentTypeError):
            parse_time_range("yestoday")

    def test_fetcher_uses_exact_previous_beijing_calendar_day(self):
        for now in (
            datetime(2026, 11, 1, 0, 5, tzinfo=fetcher.TZ_BEIJING),
            datetime(2027, 1, 1, 0, 5, tzinfo=fetcher.TZ_BEIJING),
            datetime(2028, 3, 1, 23, 59, tzinfo=fetcher.TZ_BEIJING),
        ):
            start_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
            start_yesterday = start_today - timedelta(days=1)
            for value, expected in (
                (start_yesterday - timedelta(seconds=1), False),
                (start_yesterday, True),
                (start_today - timedelta(seconds=1), True),
                (start_today, False),
                (start_today + timedelta(days=1), False),
            ):
                with self.subTest(now=now, value=value):
                    self.assertEqual(
                        fetcher.is_within_range(
                            value.astimezone(timezone.utc), "yesterday", now
                        ),
                        expected,
                    )
        self.assertFalse(fetcher.is_within_range(None, "yesterday"))

    def test_processor_selects_yesterdays_csv_not_todays(self):
        for now, expected in (
            (datetime(2026, 11, 1, tzinfo=processor.TZ_BEIJING), "20261031"),
            (datetime(2027, 1, 1, tzinfo=processor.TZ_BEIJING), "20261231"),
            (datetime(2028, 3, 1, tzinfo=processor.TZ_BEIJING), "20280229"),
        ):
            with self.subTest(now=now), patch.object(
                processor, "datetime", wraps=datetime
            ) as clock:
                clock.now.return_value = now
                self.assertTrue(
                    processor.csv_matches_time_range(
                        Path(f"author-{expected}.csv"), "yesterday"
                    )
                )
                self.assertFalse(
                    processor.csv_matches_time_range(
                        Path(f"author-{now:%Y%m%d}.csv"), "yesterday"
                    )
                )
                self.assertFalse(
                    processor.csv_matches_time_range(
                        Path(f"author-{now - timedelta(days=2):%Y%m%d}.csv"),
                        "yesterday",
                    )
                )
                self.assertFalse(
                    processor.csv_matches_time_range(
                        Path("author-invalid.csv"), "yesterday"
                    )
                )
                clock.now.assert_called_with(processor.TZ_BEIJING)

    def test_upload_preserves_local_calendar_day_semantics(self):
        for now, expected in (
            (datetime(2026, 11, 1, 0, 5), "20261031"),
            (datetime(2027, 1, 1, 0, 5), "20261231"),
            (datetime(2028, 3, 1, 0, 5), "20280229"),
        ):
            with self.subTest(now=now), patch.object(upload, "datetime") as clock:
                clock.now.return_value = now
                self.assertEqual(upload.get_target_dates("yesterday"), [expected])
                clock.now.assert_called_with()


if __name__ == "__main__":
    unittest.main()
