import csv
import sqlite3


def export_authors_to_csv(db_path, output_csv):
    try:
        # 1. 连接数据库
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 2. 编写 SQL 语句
        # 使用 COALESCE 处理优先级：yt_name > nico_name > twitter_name
        # 如果三者都为空，则 author 列会显示为 None/空
        query = """
        SELECT 
            COALESCE(yt_name, nico_name, twitter_name) AS author,
            comment
        FROM authors
        """

        cursor.execute(query)

        # 3. 获取数据
        rows = cursor.fetchall()

        # 4. 写入 CSV
        with open(output_csv, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)

            # 写入自定义表头
            writer.writerow(["作者", "备注"])

            # 写入查询结果
            writer.writerows(rows)

        print(f"导出成功！文件已保存为: {output_csv}")
        print(f"共导出 {len(rows)} 条记录。")

    except sqlite3.Error as e:
        print(f"数据库操作出错: {e}")
    except Exception as e:
        print(f"发生错误: {e}")
    finally:
        if conn:
            conn.close()


# --- 执行 ---
export_authors_to_csv("../backend/random-2hu-stuff.db", "authors-comments.csv")
