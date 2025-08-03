#!/usr/bin/env python3
"""
作者头像更新脚本

从数据库中的作者URL获取头像并更新到数据库

使用方法:
python3 update_avatars.py

可选参数:
--db-path: 数据库路径（默认为 ../backend/random-2hu-stuff.db）
--debug: 启用调试模式
--force: 强制更新所有头像（包括已有头像的作者）
--author-id: 只更新指定ID的作者
--author-name: 只更新指定名称的作者
"""

import argparse
import sqlite3
import os
import sys
import yt_dlp
import time

def create_connection(db_path):
    """创建数据库连接"""
    try:
        conn = sqlite3.connect(db_path)
        return conn
    except sqlite3.Error as e:
        print(f"数据库连接错误: {e}")
        return None

def get_author_avatar_from_url(author_url, debug=False):
    """从作者URL获取头像"""
    if not author_url:
        return None
    
    try:
        options = {
            'quiet': not debug,
            'skip_download': True,
            'extract_flat': True,  # 使用快速模式
            'playlistend': 1,  # 只获取第一个视频就够了
        }
        
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(author_url, download=False)
            
            avatar = None
            
            # YouTube频道
            if 'youtube.com' in author_url:
                # 方法1: 从频道信息直接获取
                avatar = (info.get('uploader_avatar') or
                         info.get('channel_avatar'))
                
                # 方法2: 从thumbnails中查找头像
                if not avatar:
                    thumbnails = info.get('thumbnails', [])
                    for thumb in thumbnails:
                        thumb_id = str(thumb.get('id', ''))
                        if 'avatar' in thumb_id or thumb_id == 'avatar_uncropped':
                            avatar = thumb.get('url')
                            break
                
                # 方法3: 如果还没有找到，从第一个视频获取（但不下载完整信息）
                if not avatar:
                    entries = info.get('entries', [])
                    if entries:
                        # 只从第一个条目尝试获取频道头像信息
                        first_entry = entries[0]
                        try:
                            # 使用快速模式获取单个视频信息
                            video_options = options.copy()
                            video_options['extract_flat'] = False
                            
                            with yt_dlp.YoutubeDL(video_options) as video_ydl:
                                video_info = video_ydl.extract_info(first_entry.get('url'), download=False)
                                avatar = (video_info.get('uploader_avatar') or
                                         video_info.get('channel_avatar'))
                        except Exception as e:
                            if debug:
                                print(f"  从第一个视频获取头像失败: {e}")
                            # 继续尝试其他方法，不要因为一个视频失败就放弃
            
            # NicoNico用户页面
            elif 'nicovideo.jp' in author_url and '/user/' in author_url:
                # 方法1: 直接从用户页面信息获取
                avatar = info.get('avatar') or info.get('uploader_avatar')
                
                # 方法2: 从第一个视频获取头像信息（如果方法1失败）
                if not avatar:
                    entries = info.get('entries', [])
                    if entries:
                        # 取第一个视频并获取详细信息
                        first_video_url = entries[0].get('url')
                        if first_video_url:
                            try:
                                video_options = options.copy()
                                video_options['extract_flat'] = False
                                
                                with yt_dlp.YoutubeDL(video_options) as video_ydl:
                                    video_info = video_ydl.extract_info(first_video_url, download=False)
                                    api_data = video_info.get('_api_data', {})
                                    owner_info = api_data.get('owner', {})
                                    if owner_info:
                                        avatar = owner_info.get('iconUrl')
                            except Exception as e:
                                if debug:
                                    print(f"  获取NicoNico视频详情失败: {e}")
            
            if debug and avatar:
                print(f"  获取到头像: {avatar}")
            elif debug:
                print(f"  未找到头像")
            
            return avatar
            
    except Exception as e:
        if debug:
            print(f"  获取头像失败: {e}")
        return None

def get_authors_to_update(conn, force=False, author_id=None, author_name=None):
    """获取需要更新头像的作者列表"""
    cursor = conn.cursor()
    
    if author_id:
        # 更新指定ID的作者
        cursor.execute("SELECT id, name, url, avatar FROM authors WHERE id = ?", (author_id,))
    elif author_name:
        # 更新指定名称的作者
        cursor.execute("SELECT id, name, url, avatar FROM authors WHERE name = ?", (author_name,))
    elif force:
        # 强制更新所有有URL的作者
        cursor.execute("SELECT id, name, url, avatar FROM authors WHERE url IS NOT NULL AND url != ''")
    else:
        # 只更新没有头像但有URL的作者
        cursor.execute("SELECT id, name, url, avatar FROM authors WHERE url IS NOT NULL AND url != '' AND (avatar IS NULL OR avatar = '')")
    
    return cursor.fetchall()

def update_author_avatar(conn, author_id, avatar_url, debug=False):
    """更新作者头像"""
    cursor = conn.cursor()
    
    try:
        cursor.execute("UPDATE authors SET avatar = ? WHERE id = ?", (avatar_url, author_id))
        conn.commit()
        return True
    except Exception as e:
        if debug:
            print(f"  更新数据库失败: {e}")
        return False

def process_authors(conn, force=False, author_id=None, author_name=None, debug=False):
    """处理作者头像更新"""
    authors = get_authors_to_update(conn, force, author_id, author_name)
    
    if not authors:
        print("没有找到需要更新的作者")
        return
    
    print(f"找到 {len(authors)} 个作者需要更新头像")
    
    stats = {
        'total': len(authors),
        'updated': 0,
        'failed': 0,
        'skipped': 0
    }
    
    for i, (author_id, name, url, current_avatar) in enumerate(authors, 1):
        print(f"\n[{i}/{len(authors)}] 处理作者: {name} (ID: {author_id})")
        
        if not url:
            print("  跳过: 没有作者URL")
            stats['skipped'] += 1
            continue
        
        if current_avatar and not force:
            print(f"  跳过: 已有头像 {current_avatar}")
            stats['skipped'] += 1
            continue
        
        print(f"  作者URL: {url}")
        
        try:
            avatar = get_author_avatar_from_url(url, debug)
            
            if avatar:
                if update_author_avatar(conn, author_id, avatar, debug):
                    print(f"  ✓ 更新头像成功: {avatar}")
                    stats['updated'] += 1
                else:
                    print(f"  ✗ 更新数据库失败")
                    stats['failed'] += 1
            else:
                print(f"  - 未找到头像")
                stats['failed'] += 1
        
        except Exception as e:
            print(f"  ✗ 处理失败: {e}")
            stats['failed'] += 1
        
        # 添加延迟避免请求过于频繁
        if i < len(authors):
            time.sleep(1)
    
    # 打印统计信息
    print(f"\n=== 处理完成 ===")
    print(f"总计: {stats['total']} 个作者")
    print(f"成功更新: {stats['updated']} 个")
    print(f"失败: {stats['failed']} 个")
    print(f"跳过: {stats['skipped']} 个")

def main():
    parser = argparse.ArgumentParser(description="从作者URL获取头像并更新到数据库")
    parser.add_argument('--db-path', default='../backend/random-2hu-stuff.db', help='数据库路径（默认: ../backend/random-2hu-stuff.db）')
    parser.add_argument('--debug', action='store_true', help='启用调试模式，显示详细信息')
    parser.add_argument('--force', action='store_true', help='强制更新所有头像（包括已有头像的作者）')
    parser.add_argument('--author-id', type=int, help='只更新指定ID的作者')
    parser.add_argument('--author-name', help='只更新指定名称的作者')
    
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
        print("开始更新作者头像...")
        if args.force:
            print("*** 强制模式 - 将更新所有作者的头像 ***")
        if args.author_id:
            print(f"*** 只更新作者ID: {args.author_id} ***")
        if args.author_name:
            print(f"*** 只更新作者: {args.author_name} ***")
        
        # 处理作者头像更新
        process_authors(conn, args.force, args.author_id, args.author_name, args.debug)
    
    finally:
        conn.close()

if __name__ == "__main__":
    main()
