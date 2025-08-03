"""
NicoNico视频信息提取并写入数据库脚本

使用方法:
python3 nico.py "https://www.nicovideo.jp/user/29626631"

可选参数:
--author-url: 作者主页URL（可选，默认使用输入的URL）
--author-avatar: 作者头像URL（可选）
--db-path: 数据库路径（默认为 ../backend/random-2hu-stuff.db）
--limit: 限制处理的视频数量
--debug: 启用调试模式
--skip-date: 跳过日期获取，最快速度

注意：作者名称会自动从NicoNico用户页面获取
"""

import argparse
import yt_dlp
import sqlite3
import os
import sys
import json
from datetime import datetime

def create_connection(db_path):
    """创建数据库连接"""
    try:
        conn = sqlite3.connect(db_path)
        return conn
    except sqlite3.Error as e:
        print(f"数据库连接错误: {e}")
        return None

def get_channel_info_from_first_video(first_video_url, debug=False, cookies_options=None):
    """从第一个视频获取频道信息"""
    try:
        options = {
            'quiet': not debug,
            'skip_download': True,
            'extract_flat': False,
        }
        
        if cookies_options:
            options.update(cookies_options)
        
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(first_video_url, download=False)
            
            channel_name = info.get('uploader') or '未知频道'
            channel_url = first_video_url.replace('/watch/', '/user/').split('/')[:-1]
            if len(channel_url) >= 4:
                # 构建用户页面URL
                channel_url = '/'.join(channel_url[:-1]) + '/user/' + str(info.get('uploader_id', ''))
            else:
                channel_url = None
            
            # 获取头像
            channel_avatar = None
            api_data = info.get('_api_data', {})
            owner_info = api_data.get('owner', {})
            if owner_info:
                channel_avatar = owner_info.get('iconUrl')
            
            return channel_name, channel_url, channel_avatar
    except Exception as e:
        if debug:
            print(f"获取频道信息失败: {e}")
        return "未知频道", None, None

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

def get_video_date(video_info):
    """从视频信息中获取发布日期"""
    return (video_info.get('upload_date') or 
           video_info.get('release_date') or 
           video_info.get('timestamp') or
           video_info.get('upload_timestamp'))

def extract_video_info_from_url(video_url, debug=False, cookies_options=None):
    """从视频URL提取详细信息"""
    try:
        # 构建yt-dlp选项
        options = {
            'quiet': not debug,
            'skip_download': True,
            'extract_flat': False,  # 获取完整信息
        }
        
        # 应用cookies选项
        if cookies_options:
            options.update(cookies_options)
        
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(video_url, download=False)
            
            title = info.get('title')
            uploader = info.get('uploader')
            uploader_id = info.get('uploader_id')
            upload_date = get_video_date(info)
            
            # 从owner信息获取头像（如果有的话）
            avatar = None
            api_data = info.get('_api_data', {})
            owner_info = api_data.get('owner', {})
            if owner_info:
                avatar = owner_info.get('iconUrl')
            
            if debug:
                print(f"  获取到视频信息: {title}")
                print(f"  作者: {uploader}")
                print(f"  发布日期: {upload_date}")
                print(f"  头像: {avatar}")
            
            return {
                'title': title,
                'uploader': uploader,
                'uploader_id': uploader_id,
                'upload_date': upload_date,
                'avatar': avatar
            }
    except Exception as e:
        if debug:
            print(f"  获取视频信息失败: {e}")
        return None

def process_flat_entries(entries, conn, author_id, stats, debug=False, skip_date=False, cookies_options=None):
    """处理平面播放列表条目"""
    channel_info_extracted = False
    author_avatar = None
    
    for entry in entries:
        video_url = entry.get('url') or entry.get('webpage_url')
        
        if not video_url:
            print(f"跳过无效条目: url={video_url}")
            stats['skipped'] += 1
            continue
        
        # 从URL中提取视频ID
        video_id = None
        if '/watch/' in video_url:
            video_id = video_url.split('/watch/')[-1]
        
        if debug:
            print(f"处理视频: {video_id} - {video_url}")
        
        # 检查视频是否已存在
        if video_exists(conn, video_url):
            print(f"视频已存在，跳过: {video_id}")
            stats['duplicates'] += 1
            continue
        
        # 获取详细视频信息（包括标题和日期）
        if debug:
            print(f"正在获取视频详情: {video_id}")
        
        video_info = extract_video_info_from_url(video_url, debug, cookies_options)
        
        if not video_info or not video_info.get('title'):
            print(f"无法获取视频信息，跳过: {video_id}")
            stats['skipped'] += 1
            continue
        
        title = video_info['title']
        
        # 如果还没有提取过频道头像，从第一个视频获取
        if not channel_info_extracted and video_info.get('avatar'):
            author_avatar = video_info['avatar']
            # 更新作者头像
            cursor = conn.cursor()
            cursor.execute("UPDATE authors SET avatar = ? WHERE id = ?", (author_avatar, author_id))
            conn.commit()
            print(f"更新作者头像: {author_avatar}")
            channel_info_extracted = True
        
        # 获取发布日期
        formatted_date = None
        if not skip_date and video_info.get('upload_date'):
            formatted_date = format_date(video_info['upload_date'])
        
        # 插入视频
        if insert_video(conn, author_id, title, video_url, formatted_date):
            stats['added'] += 1

def main():
    parser = argparse.ArgumentParser(description="提取NicoNico视频信息并写入数据库")
    parser.add_argument('url', help='用户页面的 URL，如: https://www.nicovideo.jp/user/29626631')
    parser.add_argument('--author-url', help='作者主页URL（可选，默认使用输入的URL）')
    parser.add_argument('--author-avatar', help='作者头像URL（可选）')
    parser.add_argument('--db-path', default='../backend/random-2hu-stuff.db', help='数据库路径（默认: ../backend/random-2hu-stuff.db）')
    parser.add_argument('--limit', type=int, help='限制处理的视频数量')
    parser.add_argument('--debug', action='store_true', help='启用调试模式，显示详细信息')
    parser.add_argument('--skip-date', action='store_true', help='跳过日期获取，加快处理速度')
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
        print(f"\n开始提取NicoNico视频信息: {args.url}")
        
        # yt-dlp 选项 - 使用快速模式获取播放列表
        options = {
            'quiet': not args.debug,
            'extract_flat': True,     # 快速模式，只获取基本信息
            'playlistend': args.limit,
            'skip_download': True,
        }
        
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
                
                if args.debug and entries:
                    print(f"  示例条目结构: {list(entries[0].keys())}")
                    print(f"  第一个条目: {entries[0]}")
                
                if not entries:
                    print("没有找到视频条目")
                    print("可能的原因:")
                    print("1. 用户页面为空或不可访问")
                    print("2. URL 格式问题")
                    print("3. 网络连接问题")
                    return
                
                # 自动获取频道信息（从第一个视频获取真实的频道信息）
                channel_name = "未知频道"
                channel_url = args.url
                channel_avatar = None
                
                # 准备cookies选项，用于传递给子函数
                cookies_options = {}
                if 'cookiesfrombrowser' in options:
                    cookies_options['cookiesfrombrowser'] = options['cookiesfrombrowser']
                if 'cookiefile' in options:
                    cookies_options['cookiefile'] = options['cookiefile']
                
                if entries:
                    first_video_url = entries[0].get('url')
                    if first_video_url:
                        channel_name, channel_url_from_video, channel_avatar = get_channel_info_from_first_video(
                            first_video_url, args.debug, cookies_options if cookies_options else None
                        )
                        if channel_url_from_video:
                            channel_url = channel_url_from_video
                
                # 使用命令行参数覆盖自动获取的信息
                author_url = args.author_url or channel_url or args.url
                author_avatar = args.author_avatar or channel_avatar
                
                print(f"检测到用户: {channel_name}")
                
                # 获取或创建作者
                author_id = get_or_create_author(conn, channel_name, author_url, author_avatar)
                
                # 统计信息
                stats = {'added': 0, 'duplicates': 0, 'skipped': 0}
                
                print(f"找到 {len(entries)} 个视频条目")
                
                if args.skip_date:
                    print("跳过日期模式：只获取视频标题和链接，速度较快")
                else:
                    print("标准模式：获取视频详细信息包括发布日期...")
                
                # 处理视频条目
                process_flat_entries(entries, conn, author_id, stats, args.debug, args.skip_date, cookies_options if cookies_options else None)
                
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
