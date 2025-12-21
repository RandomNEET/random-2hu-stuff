import csv
import os
import sqlite3
import sys


def import_csv_to_sqlite(db_path, csv_path):
    """
    从 CSV 导入数据：
    1. 只有当 CSV 第二列有内容时，才更新数据库。
    2. 如果 CSV 第二列为空，则跳过该行，保留数据库原样。
    """

    if not os.path.exists(db_path):
        print(f"错误：找不到数据库文件 '{db_path}'")
        return
    if not os.path.exists(csv_path):
        print(f"错误：找不到指定的 CSV 文件 '{csv_path}'")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    update_count = 0
    skip_count = 0
    not_found_count = 0

    try:
        with open(csv_path, "r", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            next(reader, None)  # 跳过表头

            for row_num, row in enumerate(reader, start=2):
                if len(row) < 2:
                    continue

                author_val = row[0].strip()
                comment_val = row[1].strip()  # 获取并去除两端空格

                # --- 关键逻辑：如果 CSV 的 comment 为空，直接跳过 ---
                if not comment_val:
                    skip_count += 1
                    continue

                # 执行更新
                sql_update = """
                UPDATE authors 
                SET comment = ? 
                WHERE yt_name = ? 
                   OR nico_name = ? 
                   OR twitter_name = ?
                """

                cursor.execute(
                    sql_update, (comment_val, author_val, author_val, author_val)
                )

                if cursor.rowcount > 0:
                    update_count += cursor.rowcount
                else:
                    print(f"第 {row_num} 行未找到匹配作者: [{author_val}]")
                    not_found_count += 1

        conn.commit()
        print("\n" + "=" * 30)
        print(f"处理完成！统计结果：")
        print(f"成功更新记录: {update_count} 条")
        print(f"因CSV列为空而跳过: {skip_count} 条")
        print(f"未匹配到作者: {not_found_count} 条")
        print("=" * 30)

    except Exception as e:
        print(f"程序运行中出错: {e}")
        conn.rollback()
    finally:
        conn.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("使用说明: python 脚本名.py <CSV文件路径>")
    else:
        target_csv = sys.argv[1]
        import_csv_to_sqlite("../backend/random-2hu-stuff.db", target_csv)
