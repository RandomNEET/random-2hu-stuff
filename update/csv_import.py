#!/usr/bin/env python3
"""
CSV Video Data Import Script

Import video data from CSV file to database. CSV format:
Author,Original Video Link,Repost Title,Repost Link,Translation Status,Notes,Supplementary Note

Usage:
python3 csv_import.py input.csv

Optional arguments:
--db-path: Database path (default: ../backend/random-2hu-stuff.db)
--debug: Enable debug mode
--dry-run: Check only, do not actually import
--skip-metadata: Skip metadata retrieval from links, use titles from CSV
--cookies-from-browser: Extract cookies from specified browser to handle restricted videos
                       Supported browsers: brave, chrome, chromium, edge, firefox, opera, safari, vivaldi, whale
                       Format: BROWSER[+KEYRING][:PROFILE][::CONTAINER]
                       Examples: firefox, chrome, edge+gnomekeyring, safari:Default::Facebook Container
--interactive: Interactive mode - manually choose handling method when encountering duplicate links (default mode)
--auto-merge: Auto-merge mode - intelligently handle duplicate links, skip interaction

Two modes for handling duplicate links:
1. Interactive mode (default): Ask for your choice each time duplicates are encountered
   - Skip: Keep existing record
   - Overwrite: Completely replace existing record with new record
   - Merge: Intelligently merge information
   - Add: Force add as new record (will have duplicate links)
2. Auto-merge mode (--auto-merge): Intelligently merge information, keep best data
"""

import argparse
import csv
import sqlite3
import os
import sys
import yt_dlp
from datetime import datetime
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

def create_connection(db_path):
    """Create database connection"""
    try:
        conn = sqlite3.connect(db_path)
        return conn
    except sqlite3.Error as e:
        print(f"Database connection error: {e}")
        return None

def clean_author_name(name):
    """Clean author name, remove BOM characters and extra whitespace"""
    if not name:
        return name
    
    # Remove BOM character (UTF-8 BOM: \ufeff)
    name = name.lstrip('\ufeff')
    
    # Remove leading and trailing whitespace
    name = name.strip()
    
    # Normalize whitespace (replace multiple spaces with single space)
    import re
    name = re.sub(r'\s+', ' ', name)
    
    return name
def clean_bilibili_url(url):
    """Clean Bilibili links, keep only necessary parameters"""
    if not url or 'bilibili.com' not in url:
        return url
    
    try:
        parsed = urlparse(url)
        query_params = parse_qs(parsed.query)
        
        # Only keep 'p' parameter (page number for multi-part videos)
        cleaned_params = {}
        if 'p' in query_params:
            cleaned_params['p'] = query_params['p']
        
        # Rebuild URL
        new_query = urlencode(cleaned_params, doseq=True) if cleaned_params else ''
        
        # If there are query parameters, ensure it starts with & (maintain original format consistency)
        if new_query and not new_query.startswith('&'):
            new_query = '&' + new_query
        
        cleaned_url = urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            new_query.lstrip('&'),  # Remove leading &, as urlunparse handles it automatically
            parsed.fragment
        ))
        
        return cleaned_url
        
    except Exception as e:
        print(f"Failed to clean Bilibili link {url}: {e}")
        return url

def get_video_metadata(url, debug=False, browser_cookies=None):
    """Get video metadata from URL"""
    if not url or url.strip() == '' or url == '未转载':
        return None, None, None
    
    try:
        options = {
            'quiet': not debug,
            'skip_download': True,
            'extract_flat': False,
        }
        
        # If cookies are enabled, extract cookies from specified browser
        if browser_cookies:
            # Parse browser cookies parameter
            # Format: BROWSER[+KEYRING][:PROFILE][::CONTAINER]
            if '+' in browser_cookies and ':' in browser_cookies:
                # Full format: browser+keyring:profile::container
                parts = browser_cookies.split('+', 1)
                browser = parts[0]
                keyring_profile_container = parts[1]
                
                if '::' in keyring_profile_container:
                    keyring_profile, container = keyring_profile_container.split('::', 1)
                    if ':' in keyring_profile:
                        keyring, profile = keyring_profile.split(':', 1)
                        options['cookiesfrombrowser'] = (browser, keyring, profile, container)
                    else:
                        keyring = keyring_profile
                        options['cookiesfrombrowser'] = (browser, keyring, None, container)
                else:
                    if ':' in keyring_profile_container:
                        keyring, profile = keyring_profile_container.split(':', 1)
                        options['cookiesfrombrowser'] = (browser, keyring, profile)
                    else:
                        keyring = keyring_profile_container
                        options['cookiesfrombrowser'] = (browser, keyring)
            elif '::' in browser_cookies:
                # Format: browser::container or browser:profile::container
                if browser_cookies.count(':') == 2:
                    browser_profile, container = browser_cookies.split('::', 1)
                    if ':' in browser_profile:
                        browser, profile = browser_profile.split(':', 1)
                        options['cookiesfrombrowser'] = (browser, None, profile, container)
                    else:
                        browser = browser_profile
                        options['cookiesfrombrowser'] = (browser, None, None, container)
                else:
                    browser, container = browser_cookies.split('::', 1)
                    options['cookiesfrombrowser'] = (browser, None, None, container)
            elif ':' in browser_cookies:
                # Format: browser:profile
                browser, profile = browser_cookies.split(':', 1)
                options['cookiesfrombrowser'] = (browser, None, profile)
            else:
                # Browser name only
                options['cookiesfrombrowser'] = (browser_cookies,)
        
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=False)
            
            title = info.get('title', None)
            uploader = info.get('uploader', None)
            
            # Get release date
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
                        print(f"Date formatting error: {upload_date} -> {e}")
            
                # Get author information
                author_info = {
                    'name': uploader,
                    'url': None,
                    'avatar': None
                }
            
            # Build author URL
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
            print(f"Failed to get video metadata {url}: {e}")
        # Raise exception for upper-level handling
        raise e

def get_or_create_author(conn, csv_author_name, author_info, debug=False):
    """Get or create author, return author ID"""
    cursor = conn.cursor()
    
    # Clean author name
    csv_author_name = clean_author_name(csv_author_name)
    
    # First try to find by CSV author name
    cursor.execute("SELECT id, name, url FROM authors WHERE name = ?", (csv_author_name,))
    result = cursor.fetchone()
    
    if result:
        author_id = result[0]
        if debug:
            print(f"Found existing author: {csv_author_name} (ID: {author_id})")
        
        # If more information obtained from video metadata, update author info
        if author_info and author_info.get('url') and not result[2]:
            cursor.execute("UPDATE authors SET url = ? WHERE id = ?", (author_info['url'], author_id))
            conn.commit()
            if debug:
                print(f"Updated author URL: {csv_author_name}")
        
        return author_id
    
    else:
        # If not found, try to find by author URL (if metadata available)
        if author_info and author_info.get('url'):
            cursor.execute("SELECT id FROM authors WHERE url = ?", (author_info['url'],))
            result = cursor.fetchone()
            if result:
                author_id = result[0]
                if debug:
                    print(f"Found existing author by URL, updating name: {csv_author_name} (ID: {author_id})")
                # Update author name to name from CSV
                cursor.execute("UPDATE authors SET name = ? WHERE id = ?", (csv_author_name, author_id))
                conn.commit()
                return author_id
        
        # Create new author - prioritize author name from URL, if none use name from CSV
        if author_info and author_info.get('name'):
            author_name = clean_author_name(author_info['name'])  # Also clean author name from URL
            if debug:
                print(f"Using author name from URL: {author_name}")
        else:
            author_name = csv_author_name  # If no author name from URL, use name from CSV
            if debug:
                print(f"No author name in URL, using name from CSV: {author_name}")
        
        author_url = author_info.get('url') if author_info else None
        
        cursor.execute("INSERT INTO authors (name, url) VALUES (?, ?)", 
                      (author_name, author_url))
        conn.commit()
        author_id = cursor.lastrowid
        print(f"Created new author: {author_name} (ID: {author_id})")
        return author_id

def insert_video_wrapper(conn, author_id, title, original_url, date_str, repost_name, repost_url, translation_status, comment=None, debug=False, interactive_mode=False, supplementary_note=None):
    """Video insertion wrapper function, adapted for new database structure
    
    Return values:
    'inserted': Inserted new video
    'updated': Updated existing video  
    'skipped': Skipped (exists and no update needed)
    'cancelled': User cancelled operation
    """
    cursor = conn.cursor()
    
    try:
        # Check if record with same original video link already exists
        # If original_url is empty, skip duplicate check and insert directly
        if original_url and original_url.strip():
            cursor.execute('''
                SELECT id, original_name, date, repost_name, repost_url, translation_status, comment, author FROM videos 
                WHERE original_url = ?
            ''', (original_url,))
            
            existing = cursor.fetchone()
        else:
            existing = None  # For empty URLs, skip duplicate check and insert new record directly
        
        if existing:
            existing_id, existing_title, existing_date, existing_repost_name, existing_repost_url, existing_translation_status, existing_comment, existing_author_id = existing
            
            if interactive_mode:
                # Interactive mode: Show conflict information and let user choose
                print(f"\n🔄 Found duplicate original video link:")
                print(f"   URL: {original_url}")
                print(f"\n📹 Existing record in database:")
                print(f"   Title: {existing_title}")
                print(f"   Date: {existing_date or 'Unknown'}")
                print(f"   Repost title: {existing_repost_name or 'None'}")
                print(f"   Repost link: {existing_repost_url or 'None'}")
                print(f"   Translation status: {get_translation_status_text(existing_translation_status)}")
                print(f"   Notes: {existing_comment or 'None'}")
                
                # Get existing record author information
                cursor.execute("SELECT name FROM authors WHERE id = ?", (existing_author_id,))
                existing_author = cursor.fetchone()
                existing_author_name = existing_author[0] if existing_author else 'Unknown'
                print(f"   Author: {existing_author_name}")
                
                print(f"\n🆕 New record information:")
                print(f"   Title: {title}")
                print(f"   Date: {date_str or 'Unknown'}")
                print(f"   Repost title: {repost_name or 'None'}")
                print(f"   Repost link: {repost_url or 'None'}")
                print(f"   Translation status: {get_translation_status_text(translation_status)}")
                print(f"   Notes: {comment or 'None'}")
                
                # Display supplementary note if available
                if supplementary_note:
                    print(f"   📝 Supplementary note: {supplementary_note}")
                
                # Get new record author information
                cursor.execute("SELECT name FROM authors WHERE id = ?", (author_id,))
                new_author = cursor.fetchone()
                new_author_name = new_author[0] if new_author else 'Unknown'
                print(f"   Author: {new_author_name}")
                
                print(f"\nPlease choose action:")
                print(f"  [1] Skip - Keep existing record")
                print(f"  [2] Overwrite - Completely replace existing record with new record")
                print(f"  [3] Merge - Intelligently merge information (keep best information)")
                print(f"  [4] Add - Force add as new record (will have duplicate links)")
                print(f"  [q] Exit program")
                
                while True:
                    choice = input("Please enter choice [1/2/3/4/q]: ").strip().lower()
                    if choice in ['1', '2', '3', '4', 'q']:
                        break
                    print("❌ Invalid choice, please enter again")
                
                if choice == 'q':
                    print("🛑 User chose to exit program")
                    return 'cancelled'
                elif choice == '1':
                    print("⏭️  Skipped, keeping existing record")
                    return 'skipped'
                elif choice == '2':
                    # Overwrite existing record
                    cursor.execute('''
                        UPDATE videos SET 
                        author = ?, original_name = ?, date = ?, 
                        repost_name = ?, repost_url = ?, translation_status = ?, comment = ?
                        WHERE id = ?
                    ''', (author_id, title, date_str, repost_name, repost_url, translation_status, comment, existing_id))
                    conn.commit()
                    print("✅ Overwritten existing record")
                    return 'updated'
                elif choice == '3':
                    # Intelligent merge
                    merged_title = title if title else existing_title
                    merged_date = date_str if date_str else existing_date
                    merged_repost_name = repost_name or existing_repost_name
                    merged_repost_url = repost_url or existing_repost_url
                    merged_comment = comment or existing_comment
                    # Choose better translation status (smaller value is better, but exclude 0)
                    if translation_status and existing_translation_status:
                        merged_translation_status = min(translation_status, existing_translation_status)
                    else:
                        merged_translation_status = translation_status or existing_translation_status
                    
                    cursor.execute('''
                        UPDATE videos SET 
                        original_name = ?, date = ?, 
                        repost_name = ?, repost_url = ?, translation_status = ?, comment = ?
                        WHERE id = ?
                    ''', (merged_title, merged_date, merged_repost_name, merged_repost_url, merged_translation_status, merged_comment, existing_id))
                    conn.commit()
                    print("🔀 Intelligently merged record")
                    return 'updated'
                elif choice == '4':
                    # Force add new record
                    cursor.execute('''
                        INSERT INTO videos 
                        (author, original_name, original_url, date, repost_name, repost_url, translation_status, comment)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (author_id, title, original_url, date_str, repost_name, repost_url, translation_status, comment))
                    conn.commit()
                    print("➕ Force added as new record")
                    return 'inserted'
            
            else:
                # Auto-processing mode: Intelligently merge information
                should_update = False
                update_fields = []
                params = []
                
                # If existing record has no repost info but new record does, update
                if not existing_repost_name and repost_name:
                    update_fields.append("repost_name = ?")
                    params.append(repost_name)
                    should_update = True
                    
                if not existing_repost_url and repost_url:
                    update_fields.append("repost_url = ?")  
                    params.append(repost_url)
                    should_update = True
                
                # If existing record has no date but new record does, update
                if not existing_date and date_str:
                    update_fields.append("date = ?")
                    params.append(date_str)
                    should_update = True
                
                # If existing record has no notes but new record does, update
                if not existing_comment and comment:
                    update_fields.append("comment = ?")
                    params.append(comment)
                    should_update = True
                
                # If new record has better translation status (smaller value usually means better translation), update
                if translation_status and (not existing_translation_status or (translation_status > 0 and translation_status < existing_translation_status)):
                    update_fields.append("translation_status = ?")
                    params.append(translation_status)
                    should_update = True
                
                if should_update:
                    params.append(existing_id)
                    update_query = f"UPDATE videos SET {', '.join(update_fields)} WHERE id = ?"
                    cursor.execute(update_query, params)
                    conn.commit()
                    
                    if debug:
                        print(f"🔄 Auto-updated existing video info: {title}")
                        if repost_name and not existing_repost_name:
                            print(f"  ➕ Added repost title: {repost_name}")
                        if repost_url and not existing_repost_url:
                            print(f"  ➕ Added repost link: {repost_url}")
                        if date_str and not existing_date:
                            print(f"  ➕ Added release date: {date_str}")
                        if comment and not existing_comment:
                            print(f"  ➕ Added notes: {comment}")
                        if translation_status and (not existing_translation_status or translation_status < existing_translation_status):
                            print(f"  🔄 Updated translation status: {get_translation_status_text(existing_translation_status)} -> {get_translation_status_text(translation_status)}")
                    
                    return 'updated'
                else:
                    if debug:
                        print(f"⏭️  Video already exists and info is complete, skipping: {original_url}")
                    return 'skipped'
        
        # Insert new video
        cursor.execute('''
            INSERT INTO videos 
            (author, original_name, original_url, date, repost_name, repost_url, translation_status, comment)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (author_id, title, original_url, date_str, repost_name, repost_url, translation_status, comment))
        
        conn.commit()
        
        if debug:
            print(f"➕ Inserted new video: {title or 'No title'}")
            if repost_name:
                print(f"   Repost title: {repost_name}")
            if repost_url:
                print(f"   Repost link: {repost_url}")
            if comment:
                print(f"   Notes: {comment}")
            print(f"   Translation status: {get_translation_status_text(translation_status)}")
        
        return 'inserted'
        
    except Exception as e:
        print(f"❌ Failed to insert video: {e}")
        if debug:
            print(f"   Title: {title}")
            print(f"   URL: {original_url}")
        return 'error'

def get_translation_status_text(status):
    """Get text description of translation status"""
    status_map = {
        1: 'Chinese Embedded',
        2: 'CC Subtitles', 
        3: 'Danmaku Translation',
        4: 'No Translation Needed',
        5: 'No Translation Yet',
        0: 'Not Set',
        None: 'Not Set'
    }
    return status_map.get(status, f'Unknown Status({status})')


def video_exists(conn, original_url):
    """Check if video already exists"""
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM videos WHERE original_url = ?", (original_url,))
    return cursor.fetchone() is not None

def insert_video(cursor, author_id, title, url, date, repost_name, repost_url, translation_status, comment, debug=False):
    """Insert video record to database"""
    cursor.execute('''
        INSERT INTO videos 
        (author, original_name, original_url, date, repost_name, repost_url, translation_status, comment)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (author_id, title, url, date, repost_name, repost_url, translation_status, comment))
    
    if debug:
        print(f"  Inserted video: {title} (Author ID: {author_id})")
        if repost_name and repost_name != '':
            print(f"    Repost title: {repost_name}")
        if repost_url and repost_url != '':
            print(f"    Repost link: {repost_url}")
        print(f"    Translation status: {translation_status}")
        if comment:
            print(f"    Notes: {comment}")
        print()

def parse_csv_line(line, debug=False):
    """Parse CSV line, return processed data"""
    parts = [part.strip() for part in line.split(',')]
    
    # Ensure at least 7 columns
    while len(parts) < 7:
        parts.append('')
    
    author_name = parts[0]
    original_url = parts[1]
    repost_name = parts[2] if parts[2] else None  # Repost title
    repost_url = parts[3] if parts[3] else None   # Repost link
    translation_status = parts[4]
    comment = parts[5] if parts[5] else None  # Notes (for database)
    supplementary_note = parts[6] if parts[6] else None  # Supplementary note (for display only)
    
    if debug:
        print(f"Parsing CSV line:")
        print(f"  Author: {author_name}")
        print(f"  Original video link: {original_url}")
        print(f"  Repost title: {repost_name}")
        print(f"  Repost link: {repost_url}")
        print(f"  Translation status: {translation_status}")
        print(f"  Notes: {comment}")
        if supplementary_note:
            print(f"  Supplementary note: {supplementary_note}")
    
    return author_name, original_url, repost_name, repost_url, translation_status, comment, supplementary_note

def write_error_to_csv(error_file, line_num, line_content, error_msg):
    """Write error line to error CSV file"""
    import csv as csv_module
    
    # If file doesn't exist, create and write header
    file_exists = os.path.exists(error_file)
    
    with open(error_file, 'a', encoding='utf-8', newline='') as f:
        writer = csv_module.writer(f)
        
        if not file_exists:
            writer.writerow(['Line Number', 'CSV Content', 'Error Message'])
        
        writer.writerow([line_num, line_content, error_msg])

def process_csv(input_file, conn, debug=False, dry_run=False, skip_metadata=False, browser_cookies=None, interactive_mode=False):
    """Process CSV file"""
    stats = {
        'total_rows': 0,
        'processed_rows': 0,
        'new_authors': 0,
        'new_videos': 0,
        'updated_videos': 0,
        'skipped_videos': 0,
        'errors': 0,
        'cancelled': 0
    }
    
    # Error file path
    error_file = input_file.replace('.csv', '_errors.csv')
    
    author_cache = {}  # Cache author info to avoid repeated metadata retrieval
    author_id_cache = {}  # Cache author IDs to avoid repeated database queries
    
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
                        print(f"Skipping line {line_num}: Incorrect format")
                    continue
                
                csv_author = clean_author_name(parts[0].strip())
                original_url = parts[1].strip()
                repost_name = parts[2].strip() if len(parts) > 2 and parts[2].strip() else None
                repost_url = parts[3].strip() if len(parts) > 3 and parts[3].strip() else None
                translation_status = parts[4].strip() if len(parts) > 4 else ''
                comment = parts[5].strip() if len(parts) > 5 and parts[5].strip() else None  # Notes (for database)
                supplementary_note = parts[6].strip() if len(parts) > 6 and parts[6].strip() else None  # For display only
                
                # Clean Bilibili links
                original_url = clean_bilibili_url(original_url)
                if repost_url:
                    repost_url = clean_bilibili_url(repost_url)
                
                # Skip invalid lines - only require author name, other fields can be empty
                if not csv_author:
                    if debug:
                        print(f"Skipping line {line_num}: Author name is empty")
                    continue
                
                if debug:
                    print(f"\nProcessing line {line_num}: {csv_author}")
                    if repost_name:
                        print(f"  Repost title: {repost_name}")
                    if repost_url:
                        print(f"  Repost link: {repost_url}")
                    if comment:
                        print(f"  Notes: {comment}")
                    print(f"  Original video link: {original_url}")
                
                # Get or use cached author information
                author_info = None
                error_occurred = False
                
                if csv_author not in author_cache:
                    if not skip_metadata and original_url and original_url.strip():
                        try:
                            if debug:
                                print(f"First time encountering author '{csv_author}', getting metadata: {original_url}")
                            _, _, author_info = get_video_metadata(original_url, debug, browser_cookies)
                        except Exception as e:
                            error_msg = str(e)
                            print(f"Line {line_num} failed to get metadata: {error_msg}")
                            
                            # Record error to CSV file
                            write_error_to_csv(error_file, line_num, original_line, error_msg)
                            
                            # Check if it's a geo restriction error
                            if 'geo restriction' in error_msg.lower() or 'not available from your location' in error_msg.lower():
                                print(f"  Geo restriction error, but continue processing this line")
                            
                            stats['errors'] += 1
                            # Don't set error_occurred = True, continue processing this line
                    else:
                        if debug and not original_url:
                            print(f"Author '{csv_author}' has no original video link, skipping metadata retrieval")
                    
                    # Store author info in cache, even None should be cached to avoid repeated attempts
                    author_cache[csv_author] = author_info
                else:
                    author_info = author_cache[csv_author]
                    if debug:
                        print(f"Using cached author info: {csv_author}")
                
                # Only skip when author metadata retrieval failed and there's no original video link
                # If there's repost info, process even if original video info retrieval failed
                
                # Get or create author (use cache to avoid repeated database queries)
                if not dry_run:
                    if csv_author in author_id_cache:
                        author_id = author_id_cache[csv_author]
                        if debug:
                            print(f"Using cached author ID: {csv_author} (ID: {author_id})")
                    else:
                        author_id = get_or_create_author(conn, csv_author, author_info, debug)
                        author_id_cache[csv_author] = author_id
                else:
                    author_id = 1  # Mock ID
                
                # Get video metadata
                title = None
                date_str = None
                video_error_occurred = False
                
                if skip_metadata or not original_url or not original_url.strip():
                    title = repost_name  # Use repost title as title, if none then None
                    date_str = None
                    if debug and not original_url:
                        print(f"  Original video link is empty, using repost title: {title}")
                else:
                    try:
                        title, date_str, _ = get_video_metadata(original_url, debug, browser_cookies)
                    except Exception as e:
                        error_msg = str(e)
                        print(f"Line {line_num} failed to get video metadata: {error_msg}")
                        
                        # Record error to CSV file
                        write_error_to_csv(error_file, line_num, original_line, error_msg)
                        
                        # Set to empty values
                        title = None
                        date_str = None
                        video_error_occurred = True
                
                # Process translation status
                try:
                    translation_status_int = int(translation_status) if translation_status.isdigit() else 0
                except:
                    translation_status_int = 0
                
                # Insert video
                if not dry_run:
                    result = insert_video_wrapper(conn, author_id, title, original_url, date_str, repost_name, repost_url, translation_status_int, comment, debug, interactive_mode, supplementary_note)
                    
                    if result == 'inserted':
                        stats['new_videos'] += 1
                    elif result == 'updated':
                        stats['updated_videos'] += 1
                    elif result == 'skipped':
                        stats['skipped_videos'] += 1
                    elif result == 'cancelled':
                        stats['cancelled'] += 1
                        print("🛑 Program cancelled by user")
                        return stats
                    else:  # error
                        stats['errors'] += 1
                else:
                    print(f"[DRY RUN] Will add video: {title or 'No title'}")
                    if repost_name:
                        print(f"  Repost title: {repost_name}")
                    if repost_url:
                        print(f"  Repost link: {repost_url}")
                    if comment:
                        print(f"  Notes: {comment}")
                    stats['new_videos'] += 1
                
                stats['processed_rows'] += 1
                
            except Exception as e:
                error_msg = f"Error processing line {line_num}: {e}"
                print(error_msg)
                if debug:
                    print(f"Line content: {original_line}")
                
                # Record error to CSV file
                write_error_to_csv(error_file, line_num, original_line, str(e))
                stats['errors'] += 1
    
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return stats
    
    # If there are errors, notify user
    if stats['errors'] > 0:
        print(f"\nError records saved to: {error_file}")
    
    return stats

def main():
    parser = argparse.ArgumentParser(description="Import video data from CSV file to database")
    parser.add_argument('csv_file', help='CSV file path')
    parser.add_argument('--db-path', default='../backend/random-2hu-stuff.db', help='Database path (default: ../backend/random-2hu-stuff.db)')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode for detailed information')
    parser.add_argument('--dry-run', action='store_true', help='Check only, do not actually import')
    parser.add_argument('--skip-metadata', action='store_true', help='Skip metadata retrieval from links, use titles from CSV')
    parser.add_argument('--cookies-from-browser', type=str, help='Extract cookies from specified browser to handle restricted videos. Supported browsers: brave, chrome, chromium, edge, firefox, opera, safari, vivaldi, whale. Format: BROWSER[+KEYRING][:PROFILE][::CONTAINER]')
    parser.add_argument('--interactive', action='store_true', help='Enable interactive mode: manually choose handling method when encountering duplicate links (default mode)')
    parser.add_argument('--auto-merge', action='store_true', help='Enable auto-merge mode: intelligently handle duplicate links, skip interaction')
    
    args = parser.parse_args()
    
    # Check if CSV file exists
    if not os.path.exists(args.csv_file):
        print(f"Error: CSV file does not exist: {args.csv_file}")
        sys.exit(1)
    
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
        print(f"\nStarting CSV file processing: {args.csv_file}")
        if args.dry_run:
            print("*** DRY RUN mode - Database will not be actually modified ***")
        if args.skip_metadata:
            print("*** Skip metadata mode - Use titles from CSV, do not get release dates ***")
        if args.cookies_from_browser:
            print(f"*** Using {args.cookies_from_browser} browser cookies to handle restricted videos ***")
        
        # Determine processing mode - default to interactive mode
        interactive_mode = not args.auto_merge  # If auto_merge not specified, use interactive mode
        if interactive_mode:
            print("*** 🤝 Interactive mode: Will ask for your handling method when encountering duplicate links (default mode)***")
        else:
            print("*** 🤖 Auto-merge mode: Intelligently handle duplicate links ***")
        
        # Process CSV
        stats = process_csv(args.csv_file, conn, args.debug, args.dry_run, args.skip_metadata, args.cookies_from_browser, interactive_mode)
        
        # Print statistics
        print(f"\n=== 📊 Processing Complete ===")
        print(f"Total rows: {stats['total_rows']}")
        print(f"Processed rows: {stats['processed_rows']}")
        print(f"New videos: {stats['new_videos']}")
        print(f"Updated videos: {stats['updated_videos']}")
        print(f"Skipped videos: {stats['skipped_videos']}")
        if stats['cancelled'] > 0:
            print(f"User cancelled: {stats['cancelled']}")
        print(f"Error rows: {stats['errors']}")
    
    finally:
        conn.close()

if __name__ == "__main__":
    main()
