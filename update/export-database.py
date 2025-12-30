import csv
import sqlite3
import sys


def export_full_combined_to_csv(db_path, output_csv):
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 编写 SQL 语句，查询两张表的所有列
        # v.* 代表视频表所有字段，a.* 代表作者表所有字段
        query = """
        SELECT 
            v.id AS video_id,
            v.original_name,
            v.original_url,
            v.original_thumbnail,
            v.date,
            v.repost_name,
            v.repost_url,
            v.repost_thumbnail,
            v.translation_status,
            v.comment AS video_comment,
            a.id AS author_db_id,
            a.yt_name,
            a.yt_url,
            a.yt_avatar,
            a.nico_name,
            a.nico_url,
            a.nico_avatar,
            a.twitter_name,
            a.twitter_url,
            a.twitter_avatar,
            a.comment AS author_comment
        FROM videos v
        LEFT JOIN authors a ON v.author = a.id
        ORDER BY v.id ASC
        """

        cursor.execute(query)

        # 动态获取 SQL 查询结果的列名作为 CSV 表头
        headers = [description[0] for description in cursor.description]
        rows = cursor.fetchall()

        with open(output_csv, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            # 写入表头
            writer.writerow(headers)
            # 写入所有合并数据
            writer.writerows(rows)

        print(f"导出成功！")
        print(f"文件路径: {output_csv}")
        print(f"共导出 {len(rows)} 条记录，每条记录包含 {len(headers)} 个字段。")

    except Exception as e:
        print(f"导出失败: {e}")
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    # 可以通过参数传入输出文件名，默认为 combined_data.csv
    out_file = sys.argv[1] if len(sys.argv) > 1 else "full-data.csv"
    export_full_combined_to_csv("../backend/random-2hu-stuff.db", out_file)
