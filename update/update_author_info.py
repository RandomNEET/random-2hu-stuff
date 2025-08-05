#!/usr/bin/env python3
"""
Author Information Update Script

Get author names and avatars from author URLs in database and update to database

Usage:
python3 update_author_info.py

Optional arguments:
--db-path: Database path (default: ../backend/random-2hu-stuff.db)
--debug: Enable debug mode
--force: Force update all author info (including authors with existing info)
--author-id: Only update author with specified ID
--author-name: Only update author with specified name
--update-names: Enable author name update feature
--update-avatars: Enable avatar update feature
--update-all: Update both author names and avatars (equivalent to --update-names --update-avatars)
"""

import argparse
import sqlite3
import os
import sys
import yt_dlp
import time

def create_connection(db_path):
    """Create database connection"""
    try:
        conn = sqlite3.connect(db_path)
        return conn
    except sqlite3.Error as e:
        print(f"Database connection error: {e}")
        return None

def get_author_info_from_url(author_url, debug=False):
    """Get author info (name and avatar) from author URL"""
    if not author_url:
        return None, None
    
    try:
        options = {
            'quiet': not debug,
            'skip_download': True,
            'extract_flat': True,  # Use fast mode
            'playlistend': 1,  # Only get first video is enough
        }
        
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(author_url, download=False)
            
            author_name = None
            avatar = None
            
            # YouTube channel
            if 'youtube.com' in author_url:
                # Get author name
                author_name = (info.get('uploader') or 
                              info.get('channel') or
                              info.get('title'))
                
                # Method 1: Get avatar directly from channel info
                avatar = (info.get('uploader_avatar') or
                         info.get('channel_avatar'))
                
                # Method 2: Look for avatar in thumbnails
                if not avatar:
                    thumbnails = info.get('thumbnails', [])
                    for thumb in thumbnails:
                        thumb_id = str(thumb.get('id', ''))
                        if 'avatar' in thumb_id or thumb_id == 'avatar_uncropped':
                            avatar = thumb.get('url')
                            break
                
                # Method 3: If still not found, get from first video (but don't download full info)
                if not avatar or not author_name:
                    entries = info.get('entries', [])
                    if entries:
                        # Only try to get channel info from first entry
                        first_entry = entries[0]
                        try:
                            # Use fast mode to get single video info
                            video_options = options.copy()
                            video_options['extract_flat'] = False
                            
                            with yt_dlp.YoutubeDL(video_options) as video_ydl:
                                video_info = video_ydl.extract_info(first_entry.get('url'), download=False)
                                if not author_name:
                                    author_name = (video_info.get('uploader') or
                                                  video_info.get('channel'))
                                if not avatar:
                                    avatar = (video_info.get('uploader_avatar') or
                                             video_info.get('channel_avatar'))
                        except Exception as e:
                            if debug:
                                print(f"  Failed to get info from first video: {e}")
                            # Continue trying other methods, don't give up because one video failed
            
            # NicoNico user page
            elif 'nicovideo.jp' in author_url and '/user/' in author_url:
                # Method 1: Get directly from user page info
                author_name = (info.get('uploader') or 
                              info.get('title'))
                avatar = info.get('avatar') or info.get('uploader_avatar')
                
                # Method 2: Get info from first video (if method 1 fails)
                if not avatar or not author_name:
                    entries = info.get('entries', [])
                    if entries:
                        # Get first video and get detailed info
                        first_video_url = entries[0].get('url')
                        if first_video_url:
                            try:
                                video_options = options.copy()
                                video_options['extract_flat'] = False
                                
                                with yt_dlp.YoutubeDL(video_options) as video_ydl:
                                    video_info = video_ydl.extract_info(first_video_url, download=False)
                                    if not author_name:
                                        author_name = video_info.get('uploader')
                                    if not avatar:
                                        api_data = video_info.get('_api_data', {})
                                        owner_info = api_data.get('owner', {})
                                        if owner_info:
                                            avatar = owner_info.get('iconUrl')
                            except Exception as e:
                                if debug:
                                    print(f"  Failed to get NicoNico video details: {e}")
            
            # Bilibili user page
            elif 'bilibili.com' in author_url and ('/space/' in author_url or '/u/' in author_url):
                # Get from user space info
                author_name = (info.get('uploader') or 
                              info.get('title'))
                avatar = info.get('uploader_avatar') or info.get('avatar')
            
            if debug:
                if author_name:
                    print(f"  Got author name: {author_name}")
                if avatar:
                    print(f"  Got avatar: {avatar}")
                if not author_name and not avatar:
                    print(f"  No author info found")
            
            return author_name, avatar
            
    except Exception as e:
        if debug:
            print(f"  Failed to get author info: {e}")
        return None, None

def get_authors_to_update(conn, force=False, author_id=None, author_name=None, update_names=False, update_avatars=False):
    """Get list of authors that need info update"""
    cursor = conn.cursor()
    
    if author_id:
        # Update author with specified ID
        cursor.execute("SELECT id, name, url, avatar FROM authors WHERE id = ?", (author_id,))
    elif author_name:
        # Update author with specified name
        cursor.execute("SELECT id, name, url, avatar FROM authors WHERE name = ?", (author_name,))
    elif force:
        # Force update all authors with URLs
        cursor.execute("SELECT id, name, url, avatar FROM authors WHERE url IS NOT NULL AND url != ''")
    else:
        # Build query conditions based on update options
        conditions = ["url IS NOT NULL AND url != ''"]
        
        if update_names and update_avatars:
            # Update authors without name or avatar
            conditions.append("(name IS NULL OR name = '' OR avatar IS NULL OR avatar = '')")
        elif update_names:
            # Only update authors without name
            conditions.append("(name IS NULL OR name = '')")
        elif update_avatars:
            # Only update authors without avatar
            conditions.append("(avatar IS NULL OR avatar = '')")
        else:
            # Default behavior: update authors without avatar
            conditions.append("(avatar IS NULL OR avatar = '')")
        
        query = f"SELECT id, name, url, avatar FROM authors WHERE {' AND '.join(conditions)}"
        cursor.execute(query)
    
    return cursor.fetchall()

def update_author_info(conn, author_id, author_name=None, avatar_url=None, debug=False):
    """Update author info"""
    cursor = conn.cursor()
    
    try:
        if author_name and avatar_url:
            cursor.execute("UPDATE authors SET name = ?, avatar = ? WHERE id = ?", (author_name, avatar_url, author_id))
            if debug:
                print(f"  Updated author name and avatar")
        elif author_name:
            cursor.execute("UPDATE authors SET name = ? WHERE id = ?", (author_name, author_id))
            if debug:
                print(f"  Updated author name: {author_name}")
        elif avatar_url:
            cursor.execute("UPDATE authors SET avatar = ? WHERE id = ?", (avatar_url, author_id))
            if debug:
                print(f"  Updated avatar: {avatar_url}")
        else:
            return False
        
        conn.commit()
        return True
    except Exception as e:
        if debug:
            print(f"  Database update failed: {e}")
        return False

def process_authors(conn, force=False, author_id=None, author_name=None, update_names=False, update_avatars=False, debug=False):
    """Process author info updates"""
    # If no update options specified, default to update avatars
    if not update_names and not update_avatars:
        update_avatars = True
    
    authors = get_authors_to_update(conn, force, author_id, author_name, update_names, update_avatars)
    
    if not authors:
        print("No authors found that need updating")
        return
    
    update_type = []
    if update_names:
        update_type.append("names")
    if update_avatars:
        update_type.append("avatars")
    
    print(f"Found {len(authors)} authors need {'/'.join(update_type)} update")
    
    stats = {
        'total': len(authors),
        'updated': 0,
        'failed': 0,
        'skipped': 0
    }
    
    for i, (author_id, name, url, current_avatar) in enumerate(authors, 1):
        print(f"\n[{i}/{len(authors)}] Processing author: {name or 'Unknown'} (ID: {author_id})")
        
        if not url:
            print("  Skipped: No author URL")
            stats['skipped'] += 1
            continue
        
        # Check if should skip
        skip_name = update_names and name and not force
        skip_avatar = update_avatars and current_avatar and not force
        
        if skip_name and skip_avatar:
            print(f"  Skipped: Already has complete info")
            stats['skipped'] += 1
            continue
        elif skip_name and not update_avatars:
            print(f"  Skipped: Already has author name")
            stats['skipped'] += 1
            continue
        elif skip_avatar and not update_names:
            print(f"  Skipped: Already has avatar")
            stats['skipped'] += 1
            continue
        
        print(f"  Author URL: {url}")
        
        try:
            fetched_name, fetched_avatar = get_author_info_from_url(url, debug)
            
            # Determine what info to update
            update_name = None
            update_avatar = None
            
            if update_names and fetched_name and (not name or force):
                update_name = fetched_name
            
            if update_avatars and fetched_avatar and (not current_avatar or force):
                update_avatar = fetched_avatar
            
            if update_name or update_avatar:
                if update_author_info(conn, author_id, update_name, update_avatar, debug):
                    success_msg = "  ✓ Update successful:"
                    if update_name:
                        success_msg += f" Author name: {update_name}"
                    if update_avatar:
                        success_msg += f" Avatar: {update_avatar}"
                    print(success_msg)
                    stats['updated'] += 1
                else:
                    print(f"  ✗ Database update failed")
                    stats['failed'] += 1
            else:
                print(f"  - No updatable info found")
                stats['failed'] += 1
        
        except Exception as e:
            print(f"  ✗ Processing failed: {e}")
            stats['failed'] += 1
        
        # Add delay to avoid too frequent requests
        if i < len(authors):
            time.sleep(1)
    
    # Print statistics
    print(f"\n=== Processing Complete ===")
    print(f"Total: {stats['total']} authors")
    print(f"Successfully updated: {stats['updated']}")
    print(f"Failed: {stats['failed']}")
    print(f"Skipped: {stats['skipped']}")

def main():
    parser = argparse.ArgumentParser(description="Get author info from author URLs and update to database")
    parser.add_argument('--db-path', default='../backend/random-2hu-stuff.db', help='Database path (default: ../backend/random-2hu-stuff.db)')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode, show detailed information')
    parser.add_argument('--force', action='store_true', help='Force update all author info (including authors with existing info)')
    parser.add_argument('--author-id', type=int, help='Only update author with specified ID')
    parser.add_argument('--author-name', help='Only update author with specified name')
    parser.add_argument('--update-names', action='store_true', help='Enable author name update feature')
    parser.add_argument('--update-avatars', action='store_true', help='Enable avatar update feature')
    parser.add_argument('--update-all', action='store_true', help='Update both author names and avatars (equivalent to --update-names --update-avatars)')
    
    args = parser.parse_args()
    
    # Process update options
    update_names = args.update_names or args.update_all
    update_avatars = args.update_avatars or args.update_all
    
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
        print("Starting author info update...")
        if args.force:
            print("*** Force mode - Will update all authors' info ***")
        if args.author_id:
            print(f"*** Only update author ID: {args.author_id} ***")
        if args.author_name:
            print(f"*** Only update author: {args.author_name} ***")
        
        # Show update options
        if update_names and update_avatars:
            print("*** Update author names and avatars ***")
        elif update_names:
            print("*** Only update author names ***")
        elif update_avatars:
            print("*** Only update avatars ***")
        else:
            print("*** Default mode - Only update avatars ***")
        
        # Process author info updates
        process_authors(conn, args.force, args.author_id, args.author_name, update_names, update_avatars, args.debug)
    
    finally:
        conn.close()

if __name__ == "__main__":
    main()
