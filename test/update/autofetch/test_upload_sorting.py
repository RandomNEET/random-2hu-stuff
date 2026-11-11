import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "update" / "autofetch"))
import upload


class UploadSortingTests(unittest.TestCase):
    def test_local_and_online_natural_order_agree(self):
        rows = [
            ["Author10", "u10", "Video 1", "b10", "1"],
            ["Author2", "u2", "Video 10", "b2", "2"],
            ["author2", "u3", "video 2", "b3", "3"],
            ["Author2", "u4", "video 2", "b4", "4"],
            ["Author2", "u5", "VIDEO 02", "b5", "5"],
            ["Author2", "u6", "Video 1", "b6", ""],
        ]
        # Group identity remains case-sensitive; sorting ignores case.
        expected = ["u6", "u4", "u5", "u2", "u3", "u10"]
        local = upload.process_rows(copy.deepcopy(rows))
        self.assertEqual([r[1] for r in local if r], expected)
        cells = [[{"text": c} for c in r] for r in rows]
        online, columns = upload.reorganize_rows(cells)
        self.assertEqual([r[1]["text"] for r in online if r is not None], expected)
        self.assertEqual(columns, 5)
        self.assertEqual(sum(not r for r in local), 2)
        self.assertEqual(sum(r is None for r in online), 2)
        self.assertEqual(cells, [[{"text": c} for c in r] for r in rows])

    def test_sort_keeps_collision_notes_and_distinct_parts(self):
        rows = [
            ["a", "same-source?p=2", "Part 10", "same-bili", "1"],
            ["a", "same-source?p=1", "Part 2", "same-bili", "1"],
        ]
        result = upload.process_rows(rows)
        self.assertEqual([r[2] for r in result], ["Part 2", "Part 10"])
        self.assertTrue(all(r[6] == "不同原视频相同B站" for r in result))
        self.assertEqual(result[0][1], "same-source?p=1")

    def test_online_sort_preserves_cell_objects_and_deduplication(self):
        title = {
            "link": {"url": "https://example.test", "text": "作品 10"},
            "format": {"bold": True},
        }
        rows = [
            [{"text": "作者2"}, {"text": "u1"}, title, {"text": "b1"}, {"number": 1}],
            [
                {"text": "作者2"},
                {"text": "u2"},
                {"text": "作品 2"},
                {"text": "b2"},
                {"number": 2},
            ],
        ]
        result, _ = upload.reorganize_rows(rows + [copy.deepcopy(rows[0]), []])
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0][2]["text"], "作品 2")
        self.assertIs(result[1][2], title)

    def test_missing_authors_titles_and_columns_do_not_crash(self):
        rows = [["z"], ["", "", "Title 10"], ["", "", "Title 2"], ["a", "", ""]]
        local = upload.process_rows(copy.deepcopy(rows))
        self.assertEqual(
            [r[2] for r in local if r and not r[0]], ["Title 2", "Title 10"]
        )
        cells = [[{"text": c} for c in row] for row in rows]
        online, _ = upload.reorganize_rows(cells)
        self.assertEqual(len([r for r in online if r is not None]), 4)

    def test_chinese_episode_numbers_in_local_and_online_sorting(self):
        episodes = ["一", "七", "三", "二", "五", "四", "十", "十一", "九", "二十"]
        rows = [
            [
                "はぅ",
                f"original-{i}",
                f"【东M中】幻想日和 第{n}话：标题",
                f"bili-{i}",
                "1",
            ]
            for i, n in enumerate(episodes)
        ]
        expected = [
            f"【东M中】幻想日和 第{n}话：标题"
            for n in ["一", "二", "三", "四", "五", "七", "九", "十", "十一", "二十"]
        ]
        self.assertEqual(
            [r[2] for r in upload.process_rows(copy.deepcopy(rows))], expected
        )
        cells = [[{"text": c} for c in row] for row in rows]
        result, _ = upload.reorganize_rows(cells)
        self.assertEqual([r[2]["text"] for r in result], expected)

    def test_chinese_units_and_digit_sequences(self):
        examples = {
            "零": 0,
            "十": 10,
            "十一": 11,
            "二十": 20,
            "廿三": 23,
            "一百零二": 102,
            "两百": 200,
            "兩百零一": 201,
            "一千零二": 1002,
            "二〇二六": 2026,
            "一万零二": 10002,
            "一萬二千三百四十五": 12345,
            "一亿零三万零二": 100030002,
            "一万亿": 1000000000000,
            "１３": 13,
        }
        for text, expected in examples.items():
            with self.subTest(text=text):
                self.assertEqual(upload.number_value(text), expected)

    def test_chinese_and_arabic_numbers_share_sort_keys_and_stable_order(self):
        titles = ["第十话", "第2话", "第二话", "第０２话", "第一话"]
        self.assertEqual(
            sorted(titles, key=upload.natural_sort_key),
            ["第一话", "第2话", "第二话", "第０２话", "第十话"],
        )
        rows = [
            [author, f"u{i}", "标题", f"b{i}", "1"]
            for i, author in enumerate(["作者十", "作者二", "作者一"])
        ]
        self.assertEqual(
            [r[0] for r in upload.process_rows(rows) if r],
            ["作者一", "作者二", "作者十"],
        )


if __name__ == "__main__":
    unittest.main()
