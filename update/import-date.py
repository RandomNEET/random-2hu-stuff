import csv
import os
import sqlite3
import sys
from datetime import datetime


def update_video_dates_standardized(db_path, csv_path):
    if not os.path.exists(db_path):
        print(f"错误：找不到数据库文件 {db_path}")
        return
    if not os.path.exists(csv_path):
        print(f"错误：找不到指定的 CSV 文件 {csv_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    update_count = 0
    skip_count = 0
    error_count = 0

    try:
        with open(csv_path, "r", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            next(reader, None)  # 跳过表头

            for row_num, row in enumerate(reader, start=2):
                if len(row) < 5:
                    continue

                v_id = row[0].strip()
                v_date_raw = row[4].strip()

                if not v_date_raw:
                    continue

                try:
                    # 解析并标准化日期
                    date_obj = datetime.strptime(v_date_raw, "%Y/%m/%d")
                    v_date_formatted = date_obj.strftime("%Y-%m-%d")
                except ValueError:
                    print(f"第 {row_num} 行日期格式无法解析: {v_date_raw}")
                    error_count += 1
                    continue

                sql_update = """
                UPDATE videos 
                SET date = ? 
                WHERE id = ? 
                  AND (date IS NULL OR date = '')
                """
                cursor.execute(sql_update, (v_date_formatted, v_id))

                if cursor.rowcount > 0:
                    update_count += 1
                else:
                    skip_count += 1

        conn.commit()
        print("\n" + "=" * 40)
        print(f"处理文件: {csv_path}")
        print(f"成功填充日期: {update_count} 条")
        print(f"跳过 (已有或不存在): {skip_count} 条")
        if error_count > 0:
            print(f"格式错误: {error_count} 条")
        print("=" * 40)

    except Exception as e:
        print(f"运行出错: {e}")
        conn.rollback()
    finally:
        conn.close()


# --- 执行逻辑 ---
if __name__ == "__main__":
    # 检查是否传入了参数
    if len(sys.argv) < 2:
        print("使用说明: python 脚本名.py <CSV文件路径>")
        sys.exit(1)

    # 获取命令行第一个参数作为 CSV 路径
    target_csv = sys.argv[1]

    db_file = "../backend/random-2hu-stuff.db"

    update_video_dates_standardized(db_file, target_csv)
