"""
YouTube MMD Video Information Extraction and Database Import Script

Usage:
python3 yt_to_db.py "https://www.youtube.com/@channelname/videos"

Optional arguments:
--author-url: Author homepage URL (optional, defaults to input URL)
--author-avatar: Author avatar URL (optional)
--db-path: Database file path (default: ./mmd.db)
--limit: Limit the number of videos to process
--debug: Enable debug mode
--skip-date: Skip date extraction for fastest speed

Note: Author names will be automatically retrieved from the YouTube channel
"""

import argparse
import yt_dlp
import sqlite3
import os
import sys
from datetime import datetime

def create_connection(db_path):
    """Create database connection"""
    try:
        conn = sqlite3.connect(db_path)
        return conn
    except sqlite3.Error as e:
        print(f"Database connection error: {e}")
        return None

def get_channel_info(result):
    """Extract channel information from YouTube result"""
    # Handle playlists
    if 'playlist' in result.get('webpage_url', '').lower() or result.get('_type') == 'playlist':
        # For playlists, need to get real channel info from first video
        entries = result.get('entries', [])
        if entries:
            first_entry = entries[0]
            # Get channel info from first video
            channel_name = (first_entry.get('uploader') or 
                           first_entry.get('channel') or
                           result.get('uploader') or
                           '未知频道')
            
            channel_url = (first_entry.get('uploader_url') or 
                          first_entry.get('channel_url') or
                          result.get('uploader_url'))
            
            # Try to get avatar from multiple sources
            channel_avatar = (first_entry.get('uploader_avatar') or
                             first_entry.get('channel_avatar') or
                             result.get('uploader_avatar') or
                             result.get('channel_avatar'))
            
            # If still no avatar, try to get from result thumbnails
            if not channel_avatar:
                thumbnails = result.get('thumbnails', [])
                for thumb in thumbnails:
                    if thumb.get('id') == 'avatar_uncropped' or 'avatar' in str(thumb.get('id', '')):
                        channel_avatar = thumb.get('url')
                        break
        else:
            # If no video entries, fallback to playlist info
            channel_name = result.get('uploader') or 'Unknown Playlist'
            channel_url = result.get('uploader_url') or result.get('webpage_url')
            channel_avatar = None
    else:
        # Channel information
        channel_name = (result.get('channel') or 
                       result.get('uploader') or 
                       result.get('title', '').replace(' - Videos', '').replace(' - Shorts', ''))
        
        channel_url = (result.get('channel_url') or 
                      result.get('uploader_url') or 
                      result.get('webpage_url'))
        
        # Try to get avatar
        channel_avatar = None
        thumbnails = result.get('thumbnails', [])
        for thumb in thumbnails:
            if thumb.get('id') == 'avatar_uncropped' or 'avatar' in str(thumb.get('id', '')):
                channel_avatar = thumb.get('url')
                break
    
    return channel_name, channel_url, channel_avatar

def get_or_create_author(conn, name, url=None, avatar=None):
    """Get or create author, return author ID"""
    cursor = conn.cursor()
    
    # First try to find existing author by name
    cursor.execute("SELECT id FROM authors WHERE name = ?", (name,))
    result = cursor.fetchone()
    
    if result:
        author_id = result[0]
        print(f"Found existing author: {name} (ID: {author_id})")
        
        # If new URL or avatar provided, update author information
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
            print(f"Updated author information: {name}")
        
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

def get_video_date(entry):
    """Get video release date"""
    return (entry.get('upload_date') or 
           entry.get('release_date') or 
           entry.get('timestamp') or
           entry.get('upload_timestamp'))

def extract_date_from_url(video_id, debug=False, cookies_options=None):
    """Quickly extract release date from video ID"""
    try:
        # Use separate fast request to get date information
        options = {
            'quiet': True,
            'skip_download': True,
            'extract_flat': False,  # Get full info for individual video only
        }
        
        # Apply cookies options
        if cookies_options:
            options.update(cookies_options)
        
        url = f"https://www.youtube.com/watch?v={video_id}"
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=False)
            upload_date = get_video_date(info)
            if debug and upload_date:
                print(f"  Retrieved release date: {upload_date}")
            return upload_date
    except Exception as e:
        if debug:
            print(f"  Failed to get date: {e}")
        return None

def extract_video_info(entries, conn, author_id, stats, debug=False, skip_date=False, cookies_options=None):
    """Extract video information and insert into database"""
    for entry in entries:
        # If entry itself has entries field, process recursively
        if 'entries' in entry and isinstance(entry['entries'], list):
            extract_video_info(entry['entries'], conn, author_id, stats, debug, skip_date, cookies_options)
        else:
            title = entry.get('title')
            video_id = entry.get('id')
            
            if not title or not video_id:
                print(f"Skipping invalid entry: title={title}, id={video_id}")
                stats['skipped'] += 1
                continue
            
            # Build complete YouTube URL
            url = f"https://www.youtube.com/watch?v={video_id}"
            
            # Check if video already exists
            if video_exists(conn, url):
                print(f"Video already exists, skipping: {title}")
                stats['duplicates'] += 1
                continue
            
            # Get release date
            formatted_date = None
            if not skip_date:
                if debug:
                    print(f"Getting video date: {title}")
                upload_date = extract_date_from_url(video_id, debug, cookies_options)
                formatted_date = format_date(upload_date)
            
            # Insert video
            if insert_video(conn, author_id, title, url, formatted_date):
                stats['added'] += 1

def main():
    parser = argparse.ArgumentParser(description="Extract YouTube video information and write to database")
    parser.add_argument('url', help='Playlist or channel URL')
    parser.add_argument('--author-url', help='Author homepage URL (optional, defaults to input URL)')
    parser.add_argument('--author-avatar', help='Author avatar URL (optional)')
    parser.add_argument('--db-path', default='../backend/random-2hu-stuff.db', help='Database path (default: ../backend/random-2hu-stuff.db)')
    parser.add_argument('--limit', type=int, help='Limit the number of videos to process')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode for detailed information')
    parser.add_argument('--skip-date', action='store_true', help='Skip date extraction to speed up processing')
    parser.add_argument('--use-firefox-cookies', action='store_true', help='Use Firefox browser cookies to handle age-restricted videos (deprecated, use --cookies-from-browser)')
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
        print(f"\nStarting video information extraction: {args.url}")
        
        # yt-dlp options - use fast mode
        options = {
            'quiet': not args.debug,
            'extract_flat': True,     # Fast mode, get basic info only
            'playlistend': args.limit,
            'skip_download': True,
        }
        
        # If using Firefox cookies (backward compatibility)
        if args.use_firefox_cookies:
            options['cookiesfrombrowser'] = ('firefox',)
            print("Using Firefox browser cookies (recommend using --cookies-from-browser firefox)")
        
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
                    print(f"Debug information:")
                    print(f"  Result type: {result.get('_type')}")
                    print(f"  Title: {result.get('title')}")
                    print(f"  Webpage URL: {result.get('webpage_url')}")
                
                entries = result.get('entries', [])
                
                if not entries:
                    print("No video entries found")
                    print("Possible reasons:")
                    print("1. Playlist is empty or inaccessible")
                    print("2. URL format issue")
                    print("3. Network connection problem")
                    return
                
                # Automatically get channel information
                channel_name, channel_url, channel_avatar = get_channel_info(result)
                
                # Override auto-retrieved information with command line arguments
                author_url = args.author_url or channel_url or args.url
                author_avatar = args.author_avatar or channel_avatar
                
                print(f"Detected channel: {channel_name}")
                
                # Get or create author
                author_id = get_or_create_author(conn, channel_name, author_url, author_avatar)
                
                # Statistics
                stats = {'added': 0, 'duplicates': 0, 'skipped': 0}
                
                print(f"Found {len(entries)} video entries")
                
                if args.skip_date:
                    print("Skip date mode: Only get video titles and links, fastest speed")
                else:
                    print("Fast mode: First get video list, then get date info as needed...")
                
                # Prepare cookies options for passing to sub-functions
                cookies_options = {}
                if 'cookiesfrombrowser' in options:
                    cookies_options['cookiesfrombrowser'] = options['cookiesfrombrowser']
                if 'cookiefile' in options:
                    cookies_options['cookiefile'] = options['cookiefile']
                
                # Extract video information (in YouTube returned order)
                extract_video_info(entries, conn, author_id, stats, args.debug, args.skip_date, cookies_options if cookies_options else None)
                
            except Exception as e:
                print(f"Error extracting video information: {e}")
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
