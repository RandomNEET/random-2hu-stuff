"""
NicoNico Video Information Extraction and Database Import Script

Usage:
python3 nico.py "https://www.nicovideo.jp/user/29626631"

Optional arguments:
--author-url: Author homepage URL (optional, defaults to input URL)
--author-avatar: Author avatar URL (optional)
--db-path: Database path (default: ../backend/random-2hu-stuff.db)
--limit: Limit the number of videos to process
--debug: Enable debug mode
--skip-date: Skip date retrieval, fastest speed

Note: Author name will be automatically extracted from NicoNico user page
"""

import argparse
import yt_dlp
import sqlite3
import os
import sys
import json
from datetime import datetime

def create_connection(db_path):
    """Create database connection"""
    try:
        conn = sqlite3.connect(db_path)
        return conn
    except sqlite3.Error as e:
        print(f"Database connection error: {e}")
        return None

def get_channel_info_from_first_video(first_video_url, debug=False, cookies_options=None):
    """Get channel information from first video"""
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
            
            channel_name = info.get('uploader') or 'Unknown Channel'
            channel_url = first_video_url.replace('/watch/', '/user/').split('/')[:-1]
            if len(channel_url) >= 4:
                # Build user page URL
                channel_url = '/'.join(channel_url[:-1]) + '/user/' + str(info.get('uploader_id', ''))
            else:
                channel_url = None
            
            # Get avatar
            channel_avatar = None
            api_data = info.get('_api_data', {})
            owner_info = api_data.get('owner', {})
            if owner_info:
                channel_avatar = owner_info.get('iconUrl')
            
            return channel_name, channel_url, channel_avatar
    except Exception as e:
        if debug:
            print(f"Failed to get channel info: {e}")
        return "Unknown Channel", None, None

def get_or_create_author(conn, name, url=None, avatar=None):
    """Get or create author, return author ID"""
    cursor = conn.cursor()
    
    # First try to find existing author by name
    cursor.execute("SELECT id FROM authors WHERE name = ?", (name,))
    result = cursor.fetchone()
    
    if result:
        author_id = result[0]
        print(f"Found existing author: {name} (ID: {author_id})")
        
        # If new URL or avatar provided, update author info
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
            print(f"Updated author info: {name}")
        
        return author_id
    else:
        # Create new author
        cursor.execute("INSERT INTO authors (name, url, avatar) VALUES (?, ?, ?)", 
                      (name, url, avatar))
        conn.commit()
        author_id = cursor.lastrowid
        print(f"Created new author: {name} (ID: {author_id})")
        return author_id

def video_exists(conn, original_url):
    """Check if video already exists"""
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM videos WHERE original_url = ?", (original_url,))
    return cursor.fetchone() is not None

def insert_video(conn, author_id, title, url, date_str):
    """Insert video information"""
    cursor = conn.cursor()
    
    # Check if video already exists
    if video_exists(conn, url):
        print(f"Video already exists, skipping: {title}")
        return False
    
    try:
        cursor.execute("""
            INSERT INTO videos (author, original_name, original_url, date) 
            VALUES (?, ?, ?, ?)
        """, (author_id, title, url, date_str))
        conn.commit()
        print(f"Added video: {title} (Release date: {date_str or 'Unknown'})")
        return True
    except sqlite3.Error as e:
        print(f"Failed to insert video: {e}")
        return False

def format_date(date_str):
    """Format date string"""
    if not date_str:
        return None
    
    try:
        # If it's a timestamp (integer or float)
        if isinstance(date_str, (int, float)):
            return datetime.fromtimestamp(date_str).strftime('%Y-%m-%d')
        
        # Convert to string
        date_str = str(date_str)
        
        # yt-dlp usually returns YYYYMMDD format
        if len(date_str) == 8 and date_str.isdigit():
            return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
        
        # If already in correct format, return directly
        elif len(date_str) == 10 and date_str.count('-') == 2:
            return date_str
        
        # Try ISO format
        else:
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return dt.strftime('%Y-%m-%d')
                
    except Exception as e:
        print(f"Date formatting error: {date_str} -> {e}")
        return str(date_str) if date_str else None

def get_video_date(video_info):
    """Get release date from video info"""
    return (video_info.get('upload_date') or 
           video_info.get('release_date') or 
           video_info.get('timestamp') or
           video_info.get('upload_timestamp'))

def extract_video_info_from_url(video_url, debug=False, cookies_options=None):
    """Extract detailed information from video URL"""
    try:
        # Build yt-dlp options
        options = {
            'quiet': not debug,
            'skip_download': True,
            'extract_flat': False,  # Get full information
        }
        
        # Apply cookies options
        if cookies_options:
            options.update(cookies_options)
        
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(video_url, download=False)
            
            title = info.get('title')
            uploader = info.get('uploader')
            uploader_id = info.get('uploader_id')
            upload_date = get_video_date(info)
            
            # Get avatar from owner info (if available)
            avatar = None
            api_data = info.get('_api_data', {})
            owner_info = api_data.get('owner', {})
            if owner_info:
                avatar = owner_info.get('iconUrl')
            
            if debug:
                print(f"  Got video info: {title}")
                print(f"  Author: {uploader}")
                print(f"  Release date: {upload_date}")
                print(f"  Avatar: {avatar}")
            
            return {
                'title': title,
                'uploader': uploader,
                'uploader_id': uploader_id,
                'upload_date': upload_date,
                'avatar': avatar
            }
    except Exception as e:
        if debug:
            print(f"  Failed to get video info: {e}")
        return None

def process_flat_entries(entries, conn, author_id, stats, debug=False, skip_date=False, cookies_options=None):
    """Process flat playlist entries"""
    channel_info_extracted = False
    author_avatar = None
    
    for entry in entries:
        video_url = entry.get('url') or entry.get('webpage_url')
        
        if not video_url:
            print(f"Skipping invalid entry: url={video_url}")
            stats['skipped'] += 1
            continue
        
        # Extract video ID from URL
        video_id = None
        if '/watch/' in video_url:
            video_id = video_url.split('/watch/')[-1]
        
        if debug:
            print(f"Processing video: {video_id} - {video_url}")
        
        # Check if video already exists
        if video_exists(conn, video_url):
            print(f"Video already exists, skipping: {video_id}")
            stats['duplicates'] += 1
            continue
        
        # Get detailed video info (including title and date)
        if debug:
            print(f"Getting video details: {video_id}")
        
        video_info = extract_video_info_from_url(video_url, debug, cookies_options)
        
        if not video_info or not video_info.get('title'):
            print(f"Unable to get video info, skipping: {video_id}")
            stats['skipped'] += 1
            continue
        
        title = video_info['title']
        
        # If channel avatar not extracted yet, get from first video
        if not channel_info_extracted and video_info.get('avatar'):
            author_avatar = video_info['avatar']
            # Update author avatar
            cursor = conn.cursor()
            cursor.execute("UPDATE authors SET avatar = ? WHERE id = ?", (author_avatar, author_id))
            conn.commit()
            print(f"Updated author avatar: {author_avatar}")
            channel_info_extracted = True
        
        # Get release date
        formatted_date = None
        if not skip_date and video_info.get('upload_date'):
            formatted_date = format_date(video_info['upload_date'])
        
        # Insert video
        if insert_video(conn, author_id, title, video_url, formatted_date):
            stats['added'] += 1

def main():
    parser = argparse.ArgumentParser(description="Extract NicoNico video information and write to database")
    parser.add_argument('url', help='User page URL, e.g.: https://www.nicovideo.jp/user/29626631')
    parser.add_argument('--author-url', help='Author homepage URL (optional, defaults to input URL)')
    parser.add_argument('--author-avatar', help='Author avatar URL (optional)')
    parser.add_argument('--db-path', default='../backend/random-2hu-stuff.db', help='Database path (default: ../backend/random-2hu-stuff.db)')
    parser.add_argument('--limit', type=int, help='Limit the number of videos to process')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode, show detailed information')
    parser.add_argument('--skip-date', action='store_true', help='Skip date retrieval, faster processing speed')
    parser.add_argument('--cookies-from-browser', type=str, help='Extract cookies from specified browser. Format: BROWSER[+KEYRING][:PROFILE][::CONTAINER], e.g.: firefox, chrome, edge, safari, etc.')
    parser.add_argument('--cookies', type=str, help='Specify cookies file path')
    
    args = parser.parse_args()
    
    # Check if database file exists
    if not os.path.exists(args.db_path):
        print(f"Error: Database file does not exist: {args.db_path}")
        sys.exit(1)
    
    # Connect to database
    conn = create_connection(args.db_path)
    if not conn:
        print("Unable to connect to database")
        sys.exit(1)
    
    try:
        print(f"\nStarting NicoNico video info extraction: {args.url}")
        
        # yt-dlp options - use fast mode to get playlist
        options = {
            'quiet': not args.debug,
            'extract_flat': True,     # Fast mode, only get basic info
            'playlistend': args.limit,
            'skip_download': True,
        }
        
        # If browser cookies specified
        if args.cookies_from_browser:
            options['cookiesfrombrowser'] = (args.cookies_from_browser,)
            print(f"Using {args.cookies_from_browser} browser cookies")
        
        # If cookies file specified
        if args.cookies:
            options['cookiefile'] = args.cookies
            print(f"Using cookies file: {args.cookies}")
        
        with yt_dlp.YoutubeDL(options) as ydl:
            try:
                result = ydl.extract_info(args.url, download=False)
                
                if args.debug:
                    print(f"Debug info:")
                    print(f"  Result type: {result.get('_type')}")
                    print(f"  Title: {result.get('title')}")
                    print(f"  Webpage URL: {result.get('webpage_url')}")
                
                entries = result.get('entries', [])
                
                if args.debug and entries:
                    print(f"  Sample entry structure: {list(entries[0].keys())}")
                    print(f"  First entry: {entries[0]}")
                
                if not entries:
                    print("No video entries found")
                    print("Possible reasons:")
                    print("1. User page is empty or inaccessible")
                    print("2. URL format issue")
                    print("3. Network connection problem")
                    return
                
                # Automatically get channel info (get real channel info from first video)
                channel_name = "Unknown Channel"
                channel_url = args.url
                channel_avatar = None
                
                # Prepare cookies options for passing to sub-functions
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
                
                # Use command line arguments to override auto-detected info
                author_url = args.author_url or channel_url or args.url
                author_avatar = args.author_avatar or channel_avatar
                
                print(f"Detected user: {channel_name}")
                
                # Get or create author
                author_id = get_or_create_author(conn, channel_name, author_url, author_avatar)
                
                # Statistics
                stats = {'added': 0, 'duplicates': 0, 'skipped': 0}
                
                print(f"Found {len(entries)} video entries")
                
                if args.skip_date:
                    print("Skip date mode: Only get video title and link, faster speed")
                else:
                    print("Standard mode: Get detailed video info including release date...")
                
                # Process video entries
                process_flat_entries(entries, conn, author_id, stats, args.debug, args.skip_date, cookies_options if cookies_options else None)
                
            except Exception as e:
                print(f"Error extracting video info: {e}")
                return
        
        # Print statistics
        print(f"\n=== Processing Complete ===")
        print(f"Author: {channel_name} (ID: {author_id})")
        print(f"New videos: {stats['added']}")
        print(f"Duplicate videos: {stats['duplicates']}")
        print(f"Skipped entries: {stats['skipped']}")
        print(f"Total processed: {stats['added'] + stats['duplicates'] + stats['skipped']}")
    
    finally:
        conn.close()

if __name__ == "__main__":
    main()
