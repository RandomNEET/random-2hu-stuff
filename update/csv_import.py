#!/usr/bin/env python3
"""
CSV视频数据导入脚本

从CSV文件导入视频数据到数据库。CSV格式：
作者,原视频链接,转载标题,转载链接,翻译状态,备注

使用方法:
python3 csv_import.py input.csv

可选参数:
--db-path: 数据库路径（默认为 ../backend/random-2hu-stuff.db）
--debug: 启用调试模式
--dry-run: 只检查不实际导入
--skip-metadata: 跳过从链接获取元数据，使用CSV中的标题
"""

import argparse
import csv
import sqlite3
import os
import sys
import yt_dlp
from datetime import datetime
from urllib.parse import urlparse

def create_connection(db_path):
    """创建数据库连接"""
    try:
        conn = sqlite3.connect(db_path)
        return conn
    except sqlite3.Error as e:
        print(f"数据库连接错误: {e}")
        return None

def get_video_metadata(url, debug=False, use_cookies=False):
    """从URL获取视频元数据"""
    if not url or url.strip() == '' or url == '未转载':
        return None, None, None
    
    try:
        options = {
            'quiet': not debug,
            'skip_download': True,
            'extract_flat': False,
        }
        
        # 如果启用cookies，使用Firefox浏览器cookies
        if use_cookies:
            options['cookiesfrombrowser'] = ('firefox',)
        
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=False)
            
            title = info.get('title', '未知标题')
            uploader = info.get('uploader', '未知作者')
            
            # 获取发布日期
            upload_date = (info.get('upload_date') or 
                          info.get('release_date') or 
                          info.get('timestamp') or
                          info.get('upload_timestamp'))
            
            formatted_date = None
            if upload_date:
                try:
                    if isinstance(upload_date, (int, float)):
                        formatted_date = datetime.fromtimestamp(upload_date).strftime('%Y-%m-%d')
                    else:
                        date_str = str(upload_date)
                        if len(date_str) == 8 and date_str.isdigit():
                            formatted_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
                        else:
                            formatted_date = date_str
                except Exception as e:
                    if debug:
                        print(f"日期格式化错误: {upload_date} -> {e}")
            
            # 获取作者信息
            author_info = {
                'name': uploader,
                'url': None,
                'avatar': None
            }
            
            # 构建作者URL
            if 'youtube.com' in url or 'youtu.be' in url:
                uploader_url = info.get('uploader_url') or info.get('channel_url')
                if uploader_url:
                    author_info['url'] = uploader_url
            
            elif 'nicovideo.jp' in url:
                uploader_id = info.get('uploader_id')
                if uploader_id:
                    author_info['url'] = f"https://www.nicovideo.jp/user/{uploader_id}"
            
            return title, formatted_date, author_info
            
    except Exception as e:
        if debug:
            print(f"获取视频元数据失败 {url}: {e}")
        # 抛出异常以便上层处理
        raise e

def get_or_create_author(conn, csv_author_name, author_info, debug=False):
    """获取或创建作者，返回作者ID"""
    cursor = conn.cursor()
    
    # 首先尝试通过CSV中的作者名查找
    cursor.execute("SELECT id, name, url FROM authors WHERE name = ?", (csv_author_name,))
    result = cursor.fetchone()
    
    if result:
        author_id = result[0]
        if debug:
            print(f"找到现有作者: {csv_author_name} (ID: {author_id})")
        
        # 如果从视频元数据获取到了更多信息，更新作者信息
        if author_info and author_info.get('url') and not result[2]:
            cursor.execute("UPDATE authors SET url = ? WHERE id = ?", (author_info['url'], author_id))
            conn.commit()
            if debug:
                print(f"更新作者URL: {csv_author_name}")
        
        return author_id
    
    else:
        # 如果没有找到，尝试通过作者URL查找（如果有元数据的话）
        if author_info and author_info.get('url'):
            cursor.execute("SELECT id FROM authors WHERE url = ?", (author_info['url'],))
            result = cursor.fetchone()
            if result:
                author_id = result[0]
                if debug:
                    print(f"通过URL找到现有作者，更新名称: {csv_author_name} (ID: {author_id})")
                # 更新作者名称为CSV中的名称
                cursor.execute("UPDATE authors SET name = ? WHERE id = ?", (csv_author_name, author_id))
                conn.commit()
                return author_id
        
        # 创建新作者
        author_name = csv_author_name
        author_url = author_info.get('url') if author_info else None
        
        cursor.execute("INSERT INTO authors (name, url) VALUES (?, ?)", 
                      (author_name, author_url))
        conn.commit()
        author_id = cursor.lastrowid
        print(f"创建新作者: {author_name} (ID: {author_id})")
        return author_id

def insert_video_wrapper(conn, author_id, title, original_url, date_str, repost_name, repost_url, translation_status, debug=False):
    """插入视频的包装函数，适配新的数据库结构"""
    cursor = conn.cursor()
    
    try:
        # 检查是否已存在
        cursor.execute('''
            SELECT id FROM videos 
            WHERE original_url = ?
        ''', (original_url,))
        
        existing = cursor.fetchone()
        if existing:
            if debug:
                print(f"视频已存在: {original_url}")
            return False
        
        # 插入新视频
        cursor.execute('''
            INSERT INTO videos 
            (author, original_name, original_url, date, repost_name, repost_url, translation_status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (author_id, title, original_url, date_str, repost_name, repost_url, translation_status))
        
        conn.commit()
        
        if debug:
            print(f"插入视频成功: {title}")
            if repost_name:
                print(f"  转载标题: {repost_name}")
            if repost_url:
                print(f"  转载链接: {repost_url}")
        
        return True
        
    except Exception as e:
        print(f"插入视频失败: {e}")
        if debug:
            print(f"  标题: {title}")
            print(f"  URL: {original_url}")
        return False


def video_exists(conn, original_url):
    """检查视频是否已存在"""
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM videos WHERE original_url = ?", (original_url,))
    return cursor.fetchone() is not None

def insert_video(cursor, author_id, title, url, date, repost_name, repost_url, translation_status, notes, debug=False):
    """插入视频记录到数据库"""
    cursor.execute('''
        INSERT INTO videos 
        (author, original_name, original_url, date, repost_name, repost_url, translation_status)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (author_id, title, url, date, repost_name, repost_url, translation_status))
    
    if debug:
        print(f"  插入视频: {title} (作者ID: {author_id})")
        if repost_name and repost_name != '':
            print(f"    转载标题: {repost_name}")
        if repost_url and repost_url != '':
            print(f"    转载链接: {repost_url}")
        print(f"    翻译状态: {translation_status}")
        if notes:
            print(f"    备注: {notes}")
        print()

def parse_csv_line(line, debug=False):
    """解析CSV行，返回处理后的数据"""
    parts = [part.strip() for part in line.split(',')]
    
    # 确保至少有6列
    while len(parts) < 6:
        parts.append('')
    
    author_name = parts[0]
    original_url = parts[1]
    repost_name = parts[2] if parts[2] else None  # 转载标题
    repost_url = parts[3] if parts[3] else None   # 转载链接
    translation_status = parts[4]
    notes = parts[5]
    
    if debug:
        print(f"解析CSV行:")
        print(f"  作者: {author_name}")
        print(f"  原视频链接: {original_url}")
        print(f"  转载标题: {repost_name}")
        print(f"  转载链接: {repost_url}")
        print(f"  翻译状态: {translation_status}")
        print(f"  备注: {notes}")
    
    return author_name, original_url, repost_name, repost_url, translation_status, notes

def write_error_to_csv(error_file, line_num, line_content, error_msg):
    """将错误行写入错误CSV文件"""
    import csv as csv_module
    
    # 如果文件不存在，创建并写入表头
    file_exists = os.path.exists(error_file)
    
    with open(error_file, 'a', encoding='utf-8', newline='') as f:
        writer = csv_module.writer(f)
        
        if not file_exists:
            writer.writerow(['行号', 'CSV内容', '错误信息'])
        
        writer.writerow([line_num, line_content, error_msg])

def process_csv(input_file, conn, debug=False, dry_run=False, skip_metadata=False, use_cookies=False):
    """处理CSV文件"""
    stats = {
        'total_rows': 0,
        'processed_rows': 0,
        'new_authors': 0,
        'new_videos': 0,
        'skipped_videos': 0,
        'errors': 0
    }
    
    # 错误文件路径
    error_file = input_file.replace('.csv', '_errors.csv')
    
    author_cache = {}  # 缓存作者信息，避免重复获取元数据
    author_id_cache = {}  # 缓存作者ID，避免重复数据库查询
    
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        for line_num, line in enumerate(lines, 1):
            original_line = line.strip()
            if not original_line:
                continue
            
            stats['total_rows'] += 1
            
            # 解析CSV行
            try:
                parts = original_line.split(',')
                if len(parts) < 2:
                    if debug:
                        print(f"跳过第{line_num}行: 格式不正确")
                    continue
                
                csv_author = parts[0].strip()
                original_url = parts[1].strip()
                repost_name = parts[2].strip() if len(parts) > 2 and parts[2].strip() else None
                repost_url = parts[3].strip() if len(parts) > 3 and parts[3].strip() else None
                translation_status = parts[4].strip() if len(parts) > 4 else ''
                
                # 跳过无效行
                if not csv_author or not original_url or original_url == '未转载':
                    if debug:
                        print(f"跳过第{line_num}行: 作者='{csv_author}', URL='{original_url}'")
                    continue
                
                if debug:
                    print(f"\n处理第{line_num}行: {csv_author}")
                    if repost_name:
                        print(f"  转载标题: {repost_name}")
                    if repost_url:
                        print(f"  转载链接: {repost_url}")
                    print(f"  原视频链接: {original_url}")
                
                # 获取或使用缓存的作者信息
                author_info = None
                error_occurred = False
                
                if csv_author not in author_cache:
                    if not skip_metadata:
                        try:
                            if debug:
                                print(f"首次遇到作者 '{csv_author}'，获取元数据: {original_url}")
                            _, _, author_info = get_video_metadata(original_url, debug, use_cookies)
                        except Exception as e:
                            error_msg = str(e)
                            print(f"第{line_num}行获取元数据失败: {error_msg}")
                            
                            # 记录错误到CSV文件
                            write_error_to_csv(error_file, line_num, original_line, error_msg)
                            
                            # 检查是否是地理限制错误
                            if 'geo restriction' in error_msg.lower() or 'not available from your location' in error_msg.lower():
                                print(f"  地理限制错误，跳过该行")
                            
                            stats['errors'] += 1
                            error_occurred = True
                    
                    # 将作者信息存入缓存，即使是None也要缓存，避免重复尝试
                    author_cache[csv_author] = author_info
                else:
                    author_info = author_cache[csv_author]
                    if debug:
                        print(f"使用缓存的作者信息: {csv_author}")
                
                # 如果获取元数据时出错，跳过这一行
                if error_occurred:
                    continue
                
                # 获取或创建作者（使用缓存避免重复数据库查询）
                if not dry_run:
                    if csv_author in author_id_cache:
                        author_id = author_id_cache[csv_author]
                        if debug:
                            print(f"使用缓存的作者ID: {csv_author} (ID: {author_id})")
                    else:
                        author_id = get_or_create_author(conn, csv_author, author_info, debug)
                        author_id_cache[csv_author] = author_id
                else:
                    author_id = 1  # 模拟ID
                
                # 获取视频元数据
                title = None
                date_str = None
                video_error_occurred = False
                
                if skip_metadata:
                    title = repost_name or "未知标题"  # 使用转载标题作为标题
                    date_str = None
                else:
                    try:
                        title, date_str, _ = get_video_metadata(original_url, debug, use_cookies)
                        if not title:
                            title = repost_name or "未知标题"
                    except Exception as e:
                        error_msg = str(e)
                        print(f"第{line_num}行获取视频元数据失败: {error_msg}")
                        
                        # 记录错误到CSV文件
                        write_error_to_csv(error_file, line_num, original_line, error_msg)
                        
                        # 使用转载标题作为备用
                        title = repost_name or "未知标题"
                        date_str = None
                        video_error_occurred = True
                
                # 处理翻译状态
                try:
                    translation_status_int = int(translation_status) if translation_status.isdigit() else 0
                except:
                    translation_status_int = 0
                
                # 插入视频
                if not dry_run:
                    if insert_video_wrapper(conn, author_id, title, original_url, date_str, repost_name, repost_url, translation_status_int, debug):
                        stats['new_videos'] += 1
                    else:
                        stats['skipped_videos'] += 1
                else:
                    print(f"[DRY RUN] 将添加视频: {title}")
                    if repost_name:
                        print(f"  转载标题: {repost_name}")
                    if repost_url:
                        print(f"  转载链接: {repost_url}")
                    stats['new_videos'] += 1
                
                stats['processed_rows'] += 1
                
            except Exception as e:
                error_msg = f"处理第{line_num}行时出错: {e}"
                print(error_msg)
                if debug:
                    print(f"行内容: {original_line}")
                
                # 记录错误到CSV文件
                write_error_to_csv(error_file, line_num, original_line, str(e))
                stats['errors'] += 1
    
    except Exception as e:
        print(f"读取CSV文件时出错: {e}")
        return stats
    
    # 如果有错误，提示用户
    if stats['errors'] > 0:
        print(f"\n错误记录已保存到: {error_file}")
    
    return stats

def main():
    parser = argparse.ArgumentParser(description="从CSV文件导入视频数据到数据库")
    parser.add_argument('csv_file', help='CSV文件路径')
    parser.add_argument('--db-path', default='../backend/random-2hu-stuff.db', help='数据库路径（默认: ../backend/random-2hu-stuff.db）')
    parser.add_argument('--debug', action='store_true', help='启用调试模式，显示详细信息')
    parser.add_argument('--dry-run', action='store_true', help='只检查不实际导入')
    parser.add_argument('--skip-metadata', action='store_true', help='跳过从链接获取元数据，使用CSV中的标题')
    parser.add_argument('--cookies-from-browser', action='store_true', help='使用Firefox浏览器cookies处理受限制的视频')
    
    args = parser.parse_args()
    
    # 检查CSV文件是否存在
    if not os.path.exists(args.csv_file):
        print(f"错误: CSV文件不存在: {args.csv_file}")
        sys.exit(1)
    
    # 检查数据库文件是否存在
    if not os.path.exists(args.db_path):
        print(f"错误: 数据库文件不存在: {args.db_path}")
        sys.exit(1)
    
    # 连接数据库
    conn = create_connection(args.db_path)
    if not conn:
        print("无法连接到数据库")
        sys.exit(1)
    
    try:
        print(f"\n开始处理CSV文件: {args.csv_file}")
        if args.dry_run:
            print("*** DRY RUN 模式 - 不会实际修改数据库 ***")
        if args.skip_metadata:
            print("*** 跳过元数据模式 - 使用CSV中的标题，不获取发布日期 ***")
        if args.cookies_from_browser:
            print("*** 使用Firefox浏览器cookies处理受限制的视频 ***")
        
        # 处理CSV
        stats = process_csv(args.csv_file, conn, args.debug, args.dry_run, args.skip_metadata, args.cookies_from_browser)
        
        # 打印统计信息
        print(f"\n=== 处理完成 ===")
        print(f"总行数: {stats['total_rows']}")
        print(f"处理行数: {stats['processed_rows']}")
        print(f"新增视频: {stats['new_videos']}")
        print(f"跳过视频: {stats['skipped_videos']}")
        print(f"错误行数: {stats['errors']}")
    
    finally:
        conn.close()

if __name__ == "__main__":
    main()
