import copy
import io
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "update" / "autofetch"))
import upload


def row(author, title, url="source", bili="bili"):
    return [
        {"text": author},
        {"link": {"url": url, "text": url}},
        {"text": title},
        {"link": {"url": bili, "text": bili}},
        {"number": 1},
    ]


def apply_requests(original, requests):
    rows = copy.deepcopy(original)
    writes = []
    for request in requests:
        grid = request["updateRangeRequest"]["gridData"]
        for offset, update in enumerate(grid["rows"]):
            index = grid["startRow"] + offset
            while len(rows) <= index:
                rows.append([])
            for column, cell in enumerate(update["values"], grid["startColumn"]):
                while len(rows[index]) <= column:
                    rows[index].append(None)
                writes.append(
                    (
                        index,
                        column,
                        copy.deepcopy(rows[index][column]),
                        cell["cellValue"],
                    )
                )
                value = copy.deepcopy(cell["cellValue"])
                if isinstance(value.get("link"), dict):
                    value["link"].pop("overwrite", None)
                rows[index][column] = value
    return rows, writes


class UploadUpdatesTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        patcher = patch.object(upload, "ORDER_STATE_DIR", Path(temporary.name))
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_padded_unchanged_sheet_has_no_updates(self):
        original = [
            row("a", "第2话") + [{"text": ""}] * 21,
            [{"text": ""}] * 26,
            row("b", "第十话") + [None] * 21,
        ]
        sorted_rows, _ = upload.reorganize_rows(copy.deepcopy(original))
        self.assertEqual(
            upload.build_order_batch_requests("s", sorted_rows, original), []
        )
        with patch.object(
            upload, "get_sheet_info", return_value=(3, 100)
        ), patch.object(
            upload, "_fetch_all_api_rows", return_value=original
        ), patch.object(
            upload.requests, "post"
        ) as post, patch.multiple(
            upload, ACCESS_TOKEN="test", CLIENT_ID="test", OPEN_ID="test"
        ):
            self.assertTrue(upload.order_sheet("f", "s"))
            post.assert_not_called()

    def test_natural_sort_updates_only_changed_cells_and_keeps_links(self):
        original = [
            row("a", "第十话", "source10", "b10") + [None] * 21,
            row("a", "第二话", "source2", "b2") + [{"text": ""}] * 21,
        ]
        snapshot = copy.deepcopy(original)
        sorted_rows, _ = upload.reorganize_rows(original)
        requests = upload.build_order_batch_requests("s", sorted_rows, original)
        actual, writes = apply_requests(original, requests)
        self.assertEqual(original, snapshot)
        self.assertTrue(all(old != new for _, _, old, new in writes))
        self.assertEqual({column for _, column, _, _ in writes}, {1, 2, 3})
        self.assertEqual(len(writes), 6)
        self.assertEqual(actual[0][2], {"text": "第二话"})
        self.assertEqual(actual[0][1], original[1][1])
        self.assertTrue(
            all(
                cell["cellValue"]["link"]["overwrite"]
                for request in requests
                for update in request["updateRangeRequest"]["gridData"]["rows"]
                for cell in update["values"]
                if "link" in cell["cellValue"]
            )
        )
        self.assertEqual(
            upload.build_order_batch_requests("s", sorted_rows, actual), []
        )

    def test_dedup_clears_only_old_nonempty_tail_and_preserves_notes(self):
        one = row("a", "第一话") + [{"text": "人工备注"}]
        original = [copy.deepcopy(one), copy.deepcopy(one), [None] * 26]
        sorted_rows, _ = upload.reorganize_rows(copy.deepcopy(original))
        requests = upload.build_order_batch_requests("s", sorted_rows, original)
        actual, writes = apply_requests(original, requests)
        self.assertEqual({i for i, _, _, _ in writes}, {1})
        self.assertEqual(len(writes), 6)
        self.assertEqual(actual[0][5], {"text": "人工备注"})
        self.assertTrue(upload._is_empty_api_row(actual[1]))
        self.assertEqual(
            upload.build_order_batch_requests("s", sorted_rows, actual), []
        )

    def test_numeric_zero_and_formula_rows_are_not_empty(self):
        self.assertFalse(upload._is_empty_api_row([{"number": 0}]))
        self.assertFalse(upload._is_empty_api_row([{"formula": "=1-1"}]))

    def test_partial_page_or_http_failure_never_posts(self):
        for failed_page in (Mock(status_code=503), Mock(status_code=200)):
            failed_page.raise_for_status.side_effect = (
                RuntimeError("http") if failed_page.status_code == 503 else None
            )
            failed_page.json.return_value = {"gridData": {"rows": []}}
            first = Mock()
            first.raise_for_status.return_value = None
            first.json.return_value = {"gridData": {"rows": [{"values": []}] * 500}}
            with self.subTest(status=failed_page.status_code), patch.multiple(
                upload, ACCESS_TOKEN="test", CLIENT_ID="test", OPEN_ID="test"
            ), patch.object(
                upload, "get_sheet_info", return_value=(501, 1000)
            ), patch.object(
                upload.requests, "get", side_effect=[first, failed_page]
            ), patch.object(
                upload.requests, "post"
            ) as post:
                self.assertFalse(upload.order_sheet("f", "s"))
                post.assert_not_called()

    def test_metadata_failure_stops_order_and_append(self):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"code": 1}
        with patch.multiple(
            upload, ACCESS_TOKEN="test", CLIENT_ID="test", OPEN_ID="test"
        ), patch.object(upload.requests, "get", return_value=response), patch.object(
            upload.requests, "post"
        ) as post:
            self.assertFalse(upload.order_sheet("f", "s"))
            self.assertFalse(
                upload.upload_to_tdocs([["a"]], {"file_id": "f", "sheet_id": "s"})
            )
            post.assert_not_called()

    def test_dry_run_reads_but_does_not_write(self):
        original = [row("a", "第十话"), row("a", "第二话")]
        with patch.multiple(
            upload, ACCESS_TOKEN="test", CLIENT_ID="test", OPEN_ID="test"
        ), patch.object(upload, "get_sheet_info", return_value=(2, 100)), patch.object(
            upload, "_fetch_all_api_rows", return_value=original
        ), patch.object(
            upload.requests, "post"
        ) as post:
            self.assertTrue(upload.order_sheet("f", "s", dry_run=True))
            post.assert_not_called()

    def test_partial_write_failure_stops_batches_and_next_diff_resumes(self):
        original = [[{"text": "old"}] for _ in range(204)]
        desired = [[{"text": "new"}] if i % 2 == 0 else original[i] for i in range(204)]
        requests = upload.build_order_batch_requests("s", desired, original)
        self.assertEqual(len(requests), 102)
        current, _ = apply_requests(original, requests[:100])
        remaining = upload.build_order_batch_requests("s", desired, current)
        self.assertEqual(len(remaining), 2)
        result, _ = apply_requests(current, remaining)
        self.assertEqual(result, desired)

    def test_write_response_missing_results_is_failure(self):
        original = [row("a", "第十话"), row("a", "第二话")]
        for body in ({"responses": []}, {"responses": [{"error": {"code": 1}}]}):
            response = Mock()
            response.raise_for_status.return_value = None
            response.json.return_value = body
            with patch.multiple(
                upload, ACCESS_TOKEN="test", CLIENT_ID="test", OPEN_ID="test"
            ), patch.object(
                upload, "get_sheet_info", return_value=(2, 100)
            ), patch.object(
                upload, "_fetch_all_api_rows", return_value=original
            ), patch.object(
                upload.requests, "post", return_value=response
            ):
                self.assertFalse(upload.order_sheet("f", "s"))

    def test_failure_log_identifies_request_and_redacts_credentials(self):
        original = [row("a", "第十话"), row("a", "第二话")]
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "responses": [{"error": {"code": 403, "message": "invalid secret-token"}}]
        }
        output = io.StringIO()
        with patch.multiple(
            upload, ACCESS_TOKEN="secret-token", CLIENT_ID="client", OPEN_ID="openid"
        ), patch.object(upload, "get_sheet_info", return_value=(2, 100)), patch.object(
            upload, "_fetch_all_api_rows", return_value=original
        ), patch.object(
            upload.requests, "post", return_value=response
        ), redirect_stdout(
            output
        ):
            self.assertFalse(upload.order_sheet("f", "s"))
        message = output.getvalue()
        self.assertIn("code=403", message)
        self.assertIn("子请求 1 (起始行 1, 列 3)", message)
        self.assertIn("invalid [REDACTED]", message)
        self.assertNotIn("secret-token", message)
        self.assertTrue(upload.order_plan_path("f", "s").exists())

    def test_business_and_malformed_responses_have_specific_errors(self):
        requests = upload.build_order_batch_requests("s", [[{"text": "new"}]], [[]])
        for body, expected in (
            ({"code": 1001, "message": "permission denied"}, "code=1001"),
            ({}, "缺少 responses"),
            ({"responses": []}, "预期 1，实际 0"),
            ({"responses": [None]}, "返回项应为对象"),
            ({"responses": [{}]}, "缺少 updateRangeResponse"),
        ):
            with self.subTest(body=body), self.assertRaisesRegex(
                RuntimeError, expected
            ):
                upload.validate_order_response(body, requests)

    def test_multiple_ranges_are_submitted_one_at_a_time(self):
        original = [row("b", "second"), row("a", "first")]
        expected, _ = upload.reorganize_rows(copy.deepcopy(original))
        current = copy.deepcopy(original)

        def post(url, json, **kwargs):
            self.assertEqual(len(json["requests"]), 1)
            changed, _ = apply_requests(current, json["requests"])
            current[:] = changed
            response = Mock()
            response.raise_for_status.return_value = None
            response.json.return_value = {"responses": [{"updateRangeResponse": {}}]}
            return response

        with patch.multiple(
            upload, ACCESS_TOKEN="test", CLIENT_ID="test", OPEN_ID="test"
        ), patch.object(upload, "get_sheet_info", return_value=(2, 100)), patch.object(
            upload, "_fetch_all_api_rows", side_effect=lambda *args: current
        ), patch.object(
            upload.requests, "post", side_effect=post
        ) as requests:
            self.assertTrue(upload.order_sheet("f", "s"))
            self.assertGreater(requests.call_count, 1)
        self.assertEqual(upload.build_order_batch_requests("s", expected, current), [])

    def test_partial_sort_recovers_original_target_without_losing_overwritten_row(self):
        original = [row("a", "第十话", "u10", "b10"), row("a", "第二话", "u2", "b2")]
        current = copy.deepcopy(original)
        calls = []

        def post(url, json, **kwargs):
            calls.append(json)
            # Simulate a server that only applied the first row before failing.
            requests = copy.deepcopy(json["requests"])
            if len(calls) == 1:
                for request in requests:
                    request["updateRangeRequest"]["gridData"]["rows"] = request[
                        "updateRangeRequest"
                    ]["gridData"]["rows"][:1]
                changed, _ = apply_requests(current, requests)
                current[:] = changed
                raise RuntimeError("interrupted")
            changed, _ = apply_requests(current, requests)
            current[:] = changed
            result = Mock()
            result.raise_for_status.return_value = None
            result.json.return_value = {
                "responses": [
                    {"updateRangeResponse": {"updatedCells": 3}} for _ in requests
                ]
            }
            return result

        with patch.multiple(
            upload, ACCESS_TOKEN="test", CLIENT_ID="test", OPEN_ID="test"
        ), patch.object(upload, "get_sheet_info", return_value=(2, 100)), patch.object(
            upload,
            "_fetch_all_api_rows",
            side_effect=lambda *args: copy.deepcopy(current),
        ), patch.object(
            upload.requests, "post", side_effect=post
        ):
            self.assertFalse(upload.order_sheet("f", "s"))
            self.assertTrue(upload.order_plan_path("f", "s").exists())
            self.assertTrue(upload.order_sheet("f", "s"))
            self.assertFalse(upload.order_plan_path("f", "s").exists())
        self.assertEqual([r[2]["text"] for r in current], ["第二话", "第十话"])
        self.assertEqual(current[1][1]["link"]["url"], "u10")

    def test_external_edit_during_recovery_stops_without_overwrite(self):
        import json

        original = [row("a", "第十话"), row("a", "第二话")]
        target, _ = upload.reorganize_rows(copy.deepcopy(original))
        path = upload.order_plan_path("f", "s")
        path.write_text(json.dumps({"before": original, "after": target}))
        original[0][2] = {"text": "人工修改的标题"}
        with patch.multiple(
            upload, ACCESS_TOKEN="test", CLIENT_ID="test", OPEN_ID="test"
        ), patch.object(upload, "get_sheet_info", return_value=(2, 100)), patch.object(
            upload, "_fetch_all_api_rows", return_value=original
        ), patch.object(
            upload.requests, "post"
        ) as post:
            self.assertFalse(upload.order_sheet("f", "s"))
            post.assert_not_called()
            self.assertTrue(path.exists())


if __name__ == "__main__":
    unittest.main()
