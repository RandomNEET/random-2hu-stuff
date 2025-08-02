"""
YouTube MMD 视频信息提取并写入数据库脚本

使用方法:
python3 yt_to_db.py "https://www.youtube.com/@channelname/videos"

可选参数:
--author-url: 作者主页URL（可选，默认使用输入的URL）
--author-avatar: 作者头像URL（可选）
--db-path: 数据库路径（默认为 ./mmd.db）
--limit: 限制处理的视频数量
--debug: 启用调试模式
--skip-date: 跳过日期获取，最快速度

注意：作者名称会自动从YouTube频道获取
"""

import argparse
import yt_dlp
import sqlite3
import os
import sys
from datetime import datetime

def create_connection(db_path):
    """创建数据库连接"""
    try:
        conn = sqlite3.connect(db_path)
        return conn
    except sqlite3.Error as e:
        print(f"数据库连接错误: {e}")
        return None

def get_channel_info(result):
    """从YouTube结果中提取频道信息"""
    # 处理播放列表
    if 'playlist' in result.get('webpage_url', '').lower() or result.get('_type') == 'playlist':
        # 对于播放列表，需要从第一个视频获取真正的频道信息
        entries = result.get('entries', [])
        if entries:
            first_entry = entries[0]
            # 从第一个视频获取频道信息
            channel_name = (first_entry.get('uploader') or 
                           first_entry.get('channel') or
                           result.get('uploader') or
                           '未知频道')
            
            channel_url = (first_entry.get('uploader_url') or 
                          first_entry.get('channel_url') or
                          result.get('uploader_url'))
            
            # 尝试获取头像 - 从多个来源尝试
            channel_avatar = (first_entry.get('uploader_avatar') or
                             first_entry.get('channel_avatar') or
                             result.get('uploader_avatar') or
                             result.get('channel_avatar'))
            
            # 如果还是没有头像，尝试从result的thumbnails获取
            if not channel_avatar:
                thumbnails = result.get('thumbnails', [])
                for thumb in thumbnails:
                    if thumb.get('id') == 'avatar_uncropped' or 'avatar' in str(thumb.get('id', '')):
                        channel_avatar = thumb.get('url')
                        break
        else:
            # 如果没有视频条目，回退到播放列表信息
            channel_name = result.get('uploader') or '未知播放列表'
            channel_url = result.get('uploader_url') or result.get('webpage_url')
            channel_avatar = None
    else:
        # 频道信息
        channel_name = (result.get('channel') or 
                       result.get('uploader') or 
                       result.get('title', '').replace(' - Videos', '').replace(' - Shorts', ''))
        
        channel_url = (result.get('channel_url') or 
                      result.get('uploader_url') or 
                      result.get('webpage_url'))
        
        # 尝试获取头像
        channel_avatar = None
        thumbnails = result.get('thumbnails', [])
        for thumb in thumbnails:
            if thumb.get('id') == 'avatar_uncropped' or 'avatar' in str(thumb.get('id', '')):
                channel_avatar = thumb.get('url')
                break
    
    return channel_name, channel_url, channel_avatar

def get_or_create_author(conn, name, url=None, avatar=None):
    """获取或创建作者，返回作者ID"""
    cursor = conn.cursor()
    
    # 首先尝试通过名称查找现有作者
    cursor.execute("SELECT id FROM authors WHERE name = ?", (name,))
    result = cursor.fetchone()
    
    if result:
        author_id = result[0]
        print(f"找到现有作者: {name} (ID: {author_id})")
        
        # 如果提供了新的URL或头像，更新作者信息
        if url or avatar:
            update_fields = []
            params = []
            if url:
                update_fields.append("url = ?")
                params.append(url)
            if avatar:
                update_fields.append("avatar = ?")
                params.append(avatar)
            params.append(author_id)
            
            cursor.execute(f"UPDATE authors SET {', '.join(update_fields)} WHERE id = ?", params)
            conn.commit()
            print(f"更新作者信息: {name}")
        
        return author_id
    else:
        # 创建新作者
        cursor.execute("INSERT INTO authors (name, url, avatar) VALUES (?, ?, ?)", 
                      (name, url, avatar))
        conn.commit()
        author_id = cursor.lastrowid
        print(f"创建新作者: {name} (ID: {author_id})")
        return author_id

def video_exists(conn, original_url):
    """检查视频是否已存在"""
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM videos WHERE original_url = ?", (original_url,))
    return cursor.fetchone() is not None

def insert_video(conn, author_id, title, url, date_str):
    """插入视频信息"""
    cursor = conn.cursor()
    
    # 检查视频是否已存在
    if video_exists(conn, url):
        print(f"视频已存在，跳过: {title}")
        return False
    
    try:
        cursor.execute("""
            INSERT INTO videos (author, original_name, original_url, date) 
            VALUES (?, ?, ?, ?)
        """, (author_id, title, url, date_str))
        conn.commit()
        print(f"添加视频: {title} (发布日期: {date_str or '未知'})")
        return True
    except sqlite3.Error as e:
        print(f"插入视频失败: {e}")
        return False

def format_date(date_str):
    """格式化日期字符串"""
    if not date_str:
        return None
    
    try:
        # 如果是时间戳（整数或浮点数）
        if isinstance(date_str, (int, float)):
            return datetime.fromtimestamp(date_str).strftime('%Y-%m-%d')
        
        # 转换为字符串
        date_str = str(date_str)
        
        # yt-dlp 通常返回 YYYYMMDD 格式
        if len(date_str) == 8 and date_str.isdigit():
            return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
        
        # 如果已经是正确格式，直接返回
        elif len(date_str) == 10 and date_str.count('-') == 2:
            return date_str
        
        # 尝试ISO格式
        else:
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return dt.strftime('%Y-%m-%d')
                
    except Exception as e:
        print(f"日期格式化错误: {date_str} -> {e}")
        return str(date_str) if date_str else None

def get_video_date(entry):
    """获取视频的发布日期"""
    return (entry.get('upload_date') or 
           entry.get('release_date') or 
           entry.get('timestamp') or
           entry.get('upload_timestamp'))

def extract_date_from_url(video_id, debug=False, cookies_options=None):
    """从视频ID快速提取发布日期"""
    try:
        # 使用单独的快速请求获取日期信息
        options = {
            'quiet': True,
            'skip_download': True,
            'extract_flat': False,  # 只对单个视频获取完整信息
        }
        
        # 应用cookies选项
        if cookies_options:
            options.update(cookies_options)
        
        url = f"https://www.youtube.com/watch?v={video_id}"
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=False)
            upload_date = get_video_date(info)
            if debug and upload_date:
                print(f"  获取到发布日期: {upload_date}")
            return upload_date
    except Exception as e:
        if debug:
            print(f"  获取日期失败: {e}")
        return None

def extract_video_info(entries, conn, author_id, stats, debug=False, skip_date=False, cookies_options=None):
    """提取视频信息并插入数据库"""
    for entry in entries:
        # 如果entry本身还有entries字段，递归处理
        if 'entries' in entry and isinstance(entry['entries'], list):
            extract_video_info(entry['entries'], conn, author_id, stats, debug, skip_date, cookies_options)
        else:
            title = entry.get('title')
            video_id = entry.get('id')
            
            if not title or not video_id:
                print(f"跳过无效条目: title={title}, id={video_id}")
                stats['skipped'] += 1
                continue
            
            # 构建完整的YouTube URL
            url = f"https://www.youtube.com/watch?v={video_id}"
            
            # 检查视频是否已存在
            if video_exists(conn, url):
                print(f"视频已存在，跳过: {title}")
                stats['duplicates'] += 1
                continue
            
            # 获取发布日期
            formatted_date = None
            if not skip_date:
                if debug:
                    print(f"正在获取视频日期: {title}")
                upload_date = extract_date_from_url(video_id, debug, cookies_options)
                formatted_date = format_date(upload_date)
            
            # 插入视频
            if insert_video(conn, author_id, title, url, formatted_date):
                stats['added'] += 1

def main():
    parser = argparse.ArgumentParser(description="提取YouTube视频信息并写入数据库")
    parser.add_argument('url', help='播放列表或作者频道的 URL')
    parser.add_argument('--author-url', help='作者主页URL（可选，默认使用输入的URL）')
    parser.add_argument('--author-avatar', help='作者头像URL（可选）')
    parser.add_argument('--db-path', default='../backend/random-2hu-stuff.db', help='数据库路径（默认: ../backend/random-2hu-stuff.db）')
    parser.add_argument('--limit', type=int, help='限制处理的视频数量')
    parser.add_argument('--debug', action='store_true', help='启用调试模式，显示详细信息')
    parser.add_argument('--skip-date', action='store_true', help='跳过日期获取，加快处理速度')
    parser.add_argument('--use-firefox-cookies', action='store_true', help='使用Firefox浏览器cookies来处理年龄限制视频（已弃用，请使用--cookies-from-browser）')
    parser.add_argument('--cookies-from-browser', type=str, help='从指定浏览器提取cookies。格式：BROWSER[+KEYRING][:PROFILE][::CONTAINER]，如：firefox、chrome、edge、safari等')
    parser.add_argument('--cookies', type=str, help='指定cookies文件路径')
    
    args = parser.parse_args()
    
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
        print(f"\n开始提取视频信息: {args.url}")
        
        # yt-dlp 选项 - 使用快速模式
        options = {
            'quiet': not args.debug,
            'extract_flat': True,     # 快速模式，只获取基本信息
            'playlistend': args.limit,
            'skip_download': True,
        }
        
        # 如果使用Firefox cookies (向后兼容)
        if args.use_firefox_cookies:
            options['cookiesfrombrowser'] = ('firefox',)
            print("使用Firefox浏览器cookies (建议使用 --cookies-from-browser firefox)")
        
        # 如果指定了浏览器cookies
        if args.cookies_from_browser:
            options['cookiesfrombrowser'] = (args.cookies_from_browser,)
            print(f"使用 {args.cookies_from_browser} 浏览器cookies")
        
        # 如果指定了cookies文件
        if args.cookies:
            options['cookiefile'] = args.cookies
            print(f"使用cookies文件: {args.cookies}")
        
        with yt_dlp.YoutubeDL(options) as ydl:
            try:
                result = ydl.extract_info(args.url, download=False)
                
                if args.debug:
                    print(f"调试信息:")
                    print(f"  结果类型: {result.get('_type')}")
                    print(f"  标题: {result.get('title')}")
                    print(f"  网页URL: {result.get('webpage_url')}")
                
                entries = result.get('entries', [])
                
                if not entries:
                    print("没有找到视频条目")
                    print("可能的原因:")
                    print("1. 播放列表为空或不可访问")
                    print("2. URL 格式问题")
                    print("3. 网络连接问题")
                    return
                
                # 自动获取频道信息
                channel_name, channel_url, channel_avatar = get_channel_info(result)
                
                # 使用命令行参数覆盖自动获取的信息
                author_url = args.author_url or channel_url or args.url
                author_avatar = args.author_avatar or channel_avatar
                
                print(f"检测到频道: {channel_name}")
                
                # 获取或创建作者
                author_id = get_or_create_author(conn, channel_name, author_url, author_avatar)
                
                # 统计信息
                stats = {'added': 0, 'duplicates': 0, 'skipped': 0}
                
                print(f"找到 {len(entries)} 个视频条目")
                
                if args.skip_date:
                    print("跳过日期模式：只获取视频标题和链接，速度最快")
                else:
                    print("快速模式：先获取视频列表，再按需获取日期信息...")
                
                # 准备cookies选项，用于传递给子函数
                cookies_options = {}
                if 'cookiesfrombrowser' in options:
                    cookies_options['cookiesfrombrowser'] = options['cookiesfrombrowser']
                if 'cookiefile' in options:
                    cookies_options['cookiefile'] = options['cookiefile']
                
                # 提取视频信息（按YouTube返回的顺序）
                extract_video_info(entries, conn, author_id, stats, args.debug, args.skip_date, cookies_options if cookies_options else None)
                
            except Exception as e:
                print(f"提取视频信息时出错: {e}")
                return
        
        # 打印统计信息
        print(f"\n=== 处理完成 ===")
        print(f"作者: {channel_name} (ID: {author_id})")
        print(f"新增视频: {stats['added']}")
        print(f"重复视频: {stats['duplicates']}")
        print(f"跳过条目: {stats['skipped']}")
        print(f"总计处理: {stats['added'] + stats['duplicates'] + stats['skipped']}")
    
    finally:
        conn.close()

if __name__ == "__main__":
    main()
