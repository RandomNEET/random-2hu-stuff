#!/usr/bin/env python3
"""
Video Thumbnail Update Script

Get thumbnails from video links in database and update to database.

Usage:
python3 thumbnail_updater.py

Optional arguments:
--db-path: Database path (default: ../backend/random-2hu-stuff.db)
--debug: Enable debug mode
--dry-run: Check only, do not actually update
--limit: Limit the number of records to process
--update-original: Update original video thumbnails
--update-repost: Update repost video thumbnails
--force: Force update existing thumbnails
--cookies: Netscape formatted cookie file to read cookies from
--cookies-from-browser: Extract cookies from specified browser to handle restricted videos
                       Supported browsers: brave, chrome, chromium, edge, firefox, opera, safari, vivaldi, whale, qutebrowser
                       Format: BROWSER[+KEYRING][:PROFILE][::CONTAINER]
                       Supported keyrings: basictext, gnomekeyring, kwallet, kwallet5, kwallet6
"""

import argparse
import sqlite3
import os
import sys
import yt_dlp
from urllib.parse import urlparse

def create_connection(db_path):
    """Create database connection"""
    try:
        conn = sqlite3.connect(db_path)
        return conn
    except sqlite3.Error as e:
        print(f"Database connection error: {e}")
        return None

def get_video_thumbnail(url, debug=False, browser_cookies=None, cookies_file=None):
    """Get video thumbnail from URL"""
    if not url or url.strip() == '' or url == '未转载':
        return None
    
    try:
        options = {
            'quiet': not debug,
            'skip_download': True,
            'extract_flat': False,
            'no_playlist': True,  # Only get single video, don't process playlist
        }
        
        # If cookies file is specified, use it
        if cookies_file:
            options['cookiefile'] = cookies_file
        
        # If cookies enabled, extract cookies from specified browser
        elif browser_cookies:
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
            
            # If it's a playlist, get info from first video
            if 'entries' in info and info['entries']:
                info = info['entries'][0]
            
            # Get thumbnail URL
            thumbnail = info.get('thumbnail')
            
            # If can't get thumbnail, try to get highest quality from thumbnails list
            if not thumbnail and 'thumbnails' in info:
                thumbnails = info['thumbnails']
                if thumbnails:
                    # Sort by preference, choose best thumbnail
                    thumbnails.sort(key=lambda x: x.get('preference', 0), reverse=True)
                    thumbnail = thumbnails[0].get('url')
            
            # Handle Bilibili thumbnail URL: change http to https
            if thumbnail and 'hdslb.com' in thumbnail and thumbnail.startswith('http://'):
                thumbnail = thumbnail.replace('http://', 'https://')
            
            return thumbnail
            
    except Exception as e:
        if debug:
            print(f"Failed to get thumbnail {url}: {e}")
        raise e

def update_thumbnails(conn, debug=False, dry_run=False, limit=None, update_original=True, update_repost=True, force=False, browser_cookies=None, cookies_file=None):
    """Update video thumbnails"""
    cursor = conn.cursor()
    
    # Build query conditions
    conditions = []
    if update_original and not force:
        conditions.append("(original_url IS NOT NULL AND original_url != '' AND original_url != '未转载' AND (original_thumbnail IS NULL OR original_thumbnail = ''))")
    elif update_original and force:
        conditions.append("(original_url IS NOT NULL AND original_url != '' AND original_url != '未转载')")
    
    if update_repost and not force:
        conditions.append("(repost_url IS NOT NULL AND repost_url != '' AND repost_url != '未转载' AND (repost_thumbnail IS NULL OR repost_thumbnail = ''))")
    elif update_repost and force:
        conditions.append("(repost_url IS NOT NULL AND repost_url != '' AND repost_url != '未转载')")
    
    if not conditions:
        print("❌ No thumbnail type specified for update")
        return {'processed': 0, 'updated': 0, 'errors': 0}
    
    where_clause = " OR ".join(conditions)
    query = f"SELECT id, original_url, original_thumbnail, repost_url, repost_thumbnail FROM videos WHERE {where_clause}"
    
    if limit:
        query += f" LIMIT {limit}"
    
    cursor.execute(query)
    videos = cursor.fetchall()
    
    print(f"Found {len(videos)} videos to process")
    
    stats = {
        'processed': 0,
        'updated': 0,
        'errors': 0,
        'original_updated': 0,
        'repost_updated': 0
    }
    
    for video in videos:
        video_id, original_url, original_thumbnail, repost_url, repost_thumbnail = video
        stats['processed'] += 1
        
        print(f"\nProcessing video ID {video_id} ({stats['processed']}/{len(videos)})")
        
        updated_fields = []
        update_params = []
        
        # Process original video thumbnail
        if update_original and original_url and original_url != '未转载':
            should_update_original = force or not original_thumbnail
            
            if should_update_original:
                try:
                    print(f"  Getting original video thumbnail: {original_url}")
                    new_thumbnail = get_video_thumbnail(original_url, debug, browser_cookies, cookies_file)
                    
                    if new_thumbnail:
                        if not dry_run:
                            updated_fields.append("original_thumbnail = ?")
                            update_params.append(new_thumbnail)
                            stats['original_updated'] += 1
                        
                        print(f"  ✅ Original video thumbnail: {new_thumbnail}")
                    else:
                        print(f"  ⚠️  Original video thumbnail not obtained")
                        
                except Exception as e:
                    print(f"  ❌ Original video thumbnail failed: {e}")
                    stats['errors'] += 1
            else:
                print(f"  ⏭️  Original video already has thumbnail, skipping")
        
        # Process repost video thumbnail
        if update_repost and repost_url and repost_url != '未转载':
            should_update_repost = force or not repost_thumbnail
            
            if should_update_repost:
                try:
                    print(f"  Getting repost video thumbnail: {repost_url}")
                    new_thumbnail = get_video_thumbnail(repost_url, debug, browser_cookies, cookies_file)
                    
                    if new_thumbnail:
                        if not dry_run:
                            updated_fields.append("repost_thumbnail = ?")
                            update_params.append(new_thumbnail)
                            stats['repost_updated'] += 1
                        
                        print(f"  ✅ Repost video thumbnail: {new_thumbnail}")
                    else:
                        print(f"  ⚠️  Repost video thumbnail not obtained")
                        
                except Exception as e:
                    print(f"  ❌ Repost video thumbnail failed: {e}")
                    stats['errors'] += 1
            else:
                print(f"  ⏭️  Repost video already has thumbnail, skipping")
        
        # Update database
        if updated_fields and not dry_run:
            try:
                update_params.append(video_id)
                update_query = f"UPDATE videos SET {', '.join(updated_fields)} WHERE id = ?"
                cursor.execute(update_query, update_params)
                conn.commit()
                stats['updated'] += 1
                print(f"  💾 Database updated")
            except Exception as e:
                print(f"  ❌ Database update failed: {e}")
                stats['errors'] += 1
        elif updated_fields and dry_run:
            print(f"  [DRY RUN] Will update: {', '.join(updated_fields)}")
            stats['updated'] += 1
    
    return stats

def fix_existing_http_thumbnails(conn, debug=False, dry_run=False):
    """Fix existing http thumbnail links in database, change them to https"""
    cursor = conn.cursor()
    
    # Find all thumbnail records containing http://i2.hdslb.com
    cursor.execute('''
        SELECT id, original_thumbnail, repost_thumbnail 
        FROM videos 
        WHERE (original_thumbnail LIKE 'http://i%.hdslb.com%' OR 
               repost_thumbnail LIKE 'http://i%.hdslb.com%')
    ''')
    
    videos = cursor.fetchall()
    
    if not videos:
        print("No http thumbnail links found that need fixing")
        return {'processed': 0, 'updated': 0}
    
    print(f"Found {len(videos)} videos with http links that need fixing")
    
    stats = {
        'processed': 0,
        'updated': 0
    }
    
    for video in videos:
        video_id, original_thumbnail, repost_thumbnail = video
        stats['processed'] += 1
        
        updated_fields = []
        update_params = []
        
        # Check and update original video thumbnail
        if original_thumbnail and original_thumbnail.startswith('http://') and 'hdslb.com' in original_thumbnail:
            new_original_thumbnail = original_thumbnail.replace('http://', 'https://')
            updated_fields.append("original_thumbnail = ?")
            update_params.append(new_original_thumbnail)
            if debug:
                print(f"Video ID {video_id}: Original video thumbnail {original_thumbnail} -> {new_original_thumbnail}")
        
        # Check and update repost video thumbnail
        if repost_thumbnail and repost_thumbnail.startswith('http://') and 'hdslb.com' in repost_thumbnail:
            new_repost_thumbnail = repost_thumbnail.replace('http://', 'https://')
            updated_fields.append("repost_thumbnail = ?")
            update_params.append(new_repost_thumbnail)
            if debug:
                print(f"Video ID {video_id}: Repost video thumbnail {repost_thumbnail} -> {new_repost_thumbnail}")
        
        # Update database
        if updated_fields:
            if not dry_run:
                try:
                    update_params.append(video_id)
                    update_query = f"UPDATE videos SET {', '.join(updated_fields)} WHERE id = ?"
                    cursor.execute(update_query, update_params)
                    conn.commit()
                    stats['updated'] += 1
                    if debug:
                        print(f"  ✅ Video ID {video_id} updated")
                except Exception as e:
                    print(f"  ❌ Video ID {video_id} update failed: {e}")
            else:
                print(f"[DRY RUN] Video ID {video_id}: Will update {', '.join(updated_fields)}")
                stats['updated'] += 1
    
    return stats

def convert_http_to_https(conn, debug=False, dry_run=False):
    """Convert HTTP links to HTTPS for Bilibili thumbnails in database"""
    cursor = conn.cursor()
    
    # Find all records with Bilibili HTTP thumbnail links
    query = """
    SELECT id, original_thumbnail, repost_thumbnail 
    FROM videos 
    WHERE (original_thumbnail LIKE 'http://i%.hdslb.com%' OR repost_thumbnail LIKE 'http://i%.hdslb.com%')
    """
    
    cursor.execute(query)
    records = cursor.fetchall()
    
    if not records:
        print("No HTTP thumbnail links found that need conversion")
        return {'processed': 0, 'updated': 0}
    
    print(f"Found {len(records)} records need HTTP to HTTPS conversion")
    
    updated_count = 0
    
    for record in records:
        video_id, original_thumbnail, repost_thumbnail = record
        updated = False
        
        # Convert original_thumbnail
        if original_thumbnail and original_thumbnail.startswith('http://') and 'hdslb.com' in original_thumbnail:
            new_original = original_thumbnail.replace('http://', 'https://')
            if debug:
                print(f"Video {video_id}: Original video thumbnail {original_thumbnail} -> {new_original}")
            
            if not dry_run:
                cursor.execute("UPDATE videos SET original_thumbnail = ? WHERE id = ?", (new_original, video_id))
            updated = True
        
        # Convert repost_thumbnail
        if repost_thumbnail and repost_thumbnail.startswith('http://') and 'hdslb.com' in repost_thumbnail:
            new_repost = repost_thumbnail.replace('http://', 'https://')
            if debug:
                print(f"Video {video_id}: Repost video thumbnail {repost_thumbnail} -> {new_repost}")
            
            if not dry_run:
                cursor.execute("UPDATE videos SET repost_thumbnail = ? WHERE id = ?", (new_repost, video_id))
            updated = True
        
        if updated:
            updated_count += 1
    
    if not dry_run:
        conn.commit()
        print(f"✅ Successfully updated {updated_count} records' thumbnail links")
    else:
        print(f"🔍 [Preview mode] Will update {updated_count} records' thumbnail links")
    
    return {'processed': len(records), 'updated': updated_count}

def main():
    parser = argparse.ArgumentParser(description="Update video thumbnails in database")
    parser.add_argument('--db-path', default='../backend/random-2hu-stuff.db', 
                       help='Database path (default: ../backend/random-2hu-stuff.db)')
    parser.add_argument('--debug', action='store_true', 
                       help='Enable debug mode, show detailed information')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Check only, do not actually update database')
    parser.add_argument('--limit', type=int, 
                       help='Limit the number of records to process')
    parser.add_argument('--update-original', action='store_true', default=True,
                       help='Update original video thumbnails (enabled by default)')
    parser.add_argument('--no-update-original', dest='update_original', action='store_false',
                       help='Do not update original video thumbnails')
    parser.add_argument('--update-repost', action='store_true', default=True,
                       help='Update repost video thumbnails (enabled by default)')
    parser.add_argument('--no-update-repost', dest='update_repost', action='store_false',
                       help='Do not update repost video thumbnails')
    parser.add_argument('--force', action='store_true',
                       help='Force update existing thumbnails')
    parser.add_argument('--cookies-from-browser', type=str, 
                       help='Extract cookies from specified browser to handle restricted videos. '
                            'Supported browsers: brave, chrome, chromium, edge, firefox, opera, safari, vivaldi, whale. '
                            'Format: BROWSER[+KEYRING][:PROFILE][::CONTAINER]. '
                            'For keyring list on your system: python3 -c "import keyring.util.platform_; print(keyring.util.platform_.data_root())". '
                            'Note: qutebrowser is not directly supported, use --cookies with qutebrowser cookie file instead.')
    parser.add_argument('--cookies', type=str, 
                       help='Netscape formatted file to read cookies from and dump cookie jar in')
    parser.add_argument('--fix-http-links', action='store_true',
                       help='Fix existing http thumbnail links in database, change them to https')
    
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
        print(f"Starting thumbnail update")
        print(f"Database: {args.db_path}")
        
        if args.dry_run:
            print("*** DRY RUN mode - Database will not be actually modified ***")
        if args.force:
            print("*** Force mode - Will update existing thumbnails ***")
        if args.cookies_from_browser:
            print(f"*** Using {args.cookies_from_browser} browser cookies ***")
        if args.cookies:
            print(f"*** Using cookies from file: {args.cookies} ***")
        if args.limit:
            print(f"*** Limiting to {args.limit} records ***")
        
        update_types = []
        if args.update_original:
            update_types.append("Original videos")
        if args.update_repost:
            update_types.append("Repost videos")
        print(f"*** Update types: {', '.join(update_types)} ***")
        
        # If fix http links feature enabled
        if args.fix_http_links:
            print("\n🔧 Starting to fix http thumbnail links in database...")
            fix_stats = fix_existing_http_thumbnails(conn, args.debug, args.dry_run)
            print(f"\n=== 🔧 Fix http links complete ===")
            print(f"Records checked: {fix_stats['processed']}")
            print(f"Records fixed: {fix_stats['updated']}")
            print()
        
        # Update thumbnails
        stats = update_thumbnails(
            conn, 
            debug=args.debug, 
            dry_run=args.dry_run, 
            limit=args.limit,
            update_original=args.update_original,
            update_repost=args.update_repost,
            force=args.force,
            browser_cookies=args.cookies_from_browser,
            cookies_file=args.cookies
        )
        
        # Print statistics
        print(f"\n=== 📊 Processing Complete ===")
        print(f"Records processed: {stats['processed']}")
        print(f"Records updated: {stats['updated']}")
        print(f"Original video thumbnails updated: {stats['original_updated']}")
        print(f"Repost video thumbnails updated: {stats['repost_updated']}")
        print(f"Errors: {stats['errors']}")
    
    finally:
        conn.close()

if __name__ == "__main__":
    main()
