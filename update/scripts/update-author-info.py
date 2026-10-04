#!/usr/bin/env python3
"""
Author Information Update Script

Get author names and avatars from author URLs in database and update to database

Database Structure:
- Authors table now has separate fields for different platforms:
  * yt_name, yt_url, yt_avatar (YouTube)
  * nico_name, nico_url, nico_avatar (NicoNico)
  * twitter_name, twitter_url, twitter_avatar (Twitter/X)
- Priority rules:
  * name and url: YouTube first, then NicoNico, then Twitter
  * avatar: NicoNico first, then YouTube, then Twitter

Usage:
python3 update_author_info.py

Optional arguments:
--db-path: Database path (default: ../backend/random-2hu-stuff.db)
--debug: Enable debug mode
--force: Force update all author info (including authors with existing info)
--author-id: Only update author with specified ID
--author-name: Only update author with specified name
--author-id-after: Update all authors with ID greater than specified value
--update-names: Enable author name update feature
--update-avatars: Enable avatar update feature
--update-links: Fill missing platform profile URLs from descriptions and external links
--dry-run: Preview without writing or creating a backup
--update-all: Update both author names and avatars (equivalent to --update-names --update-avatars)
"""

import argparse
import os
import sqlite3
import sys
import time
from pathlib import Path

import yt_dlp

from author_links import FIELDS, blank, discover_links


def create_connection(db_path):
    """Create database connection"""
    try:
        conn = sqlite3.connect(db_path)
        return conn
    except sqlite3.Error as e:
        print(f"Database connection error: {e}")
        return None


def _fxtwitter_request(screen_name):
    """Fetch user info from fxtwitter API, trying requests first, then system curl"""
    import json

    url = f"https://api.fxtwitter.com/{screen_name}"
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        import requests

        resp = requests.get(url, timeout=10, headers=headers)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass

    try:
        import subprocess

        out = subprocess.run(
            ["curl", "-sS", "--max-time", "15", "-A", "Mozilla/5.0", url],
            capture_output=True,
            text=True,
            timeout=20,
        )
        if out.returncode == 0 and out.stdout.strip():
            return json.loads(out.stdout)
    except Exception:
        pass

    return None


def get_author_info_from_url(author_url, debug=False):
    """Get author info (name and avatar) from author URL"""
    if not author_url:
        return None, None

    # Twitter/X user page (use fxtwitter API since yt-dlp has no Twitter user extractor)
    if "twitter.com" in author_url or "x.com" in author_url:
        try:
            import re

            match = re.search(r"(?:twitter\.com|x\.com)/([A-Za-z0-9_]+)", author_url)
            if not match:
                return None, None
            screen_name = match.group(1)
            if screen_name in ("i", "status", "intent", "search", "share", "home"):
                return None, None

            data = _fxtwitter_request(screen_name)
            if not data:
                return None, None

            user = data.get("user") or {}
            author_name = user.get("name")
            avatar = user.get("avatar_url")
            if avatar:
                # Use 200x200 like other records in database
                avatar = avatar.replace("_normal.jpg", "_200x200.jpg")

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

    try:
        options = {
            "quiet": not debug,
            "skip_download": True,
            "extract_flat": True,  # Use fast mode
            "playlistend": 1,  # Only get first video is enough
        }

        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(author_url, download=False)

            author_name = None
            avatar = None

            # YouTube channel
            if "youtube.com" in author_url:
                # Get author name
                author_name = (
                    info.get("uploader") or info.get("channel") or info.get("title")
                )

                # Method 1: Get avatar directly from channel info
                avatar = info.get("uploader_avatar") or info.get("channel_avatar")

                # Method 2: Look for avatar in thumbnails
                if not avatar:
                    thumbnails = info.get("thumbnails", [])
                    for thumb in thumbnails:
                        thumb_id = str(thumb.get("id", ""))
                        if "avatar" in thumb_id or thumb_id == "avatar_uncropped":
                            avatar = thumb.get("url")
                            break

                # Method 3: If still not found, get from first video (but don't download full info)
                if not avatar or not author_name:
                    entries = info.get("entries", [])
                    if entries:
                        # Only try to get channel info from first entry
                        first_entry = entries[0]
                        try:
                            # Use fast mode to get single video info
                            video_options = options.copy()
                            video_options["extract_flat"] = False

                            with yt_dlp.YoutubeDL(video_options) as video_ydl:
                                video_info = video_ydl.extract_info(
                                    first_entry.get("url"), download=False
                                )
                                if not author_name:
                                    author_name = video_info.get(
                                        "uploader"
                                    ) or video_info.get("channel")
                                if not avatar:
                                    avatar = video_info.get(
                                        "uploader_avatar"
                                    ) or video_info.get("channel_avatar")
                        except Exception as e:
                            if debug:
                                print(f"  Failed to get info from first video: {e}")
                            # Continue trying other methods, don't give up because one video failed

            # NicoNico user page
            elif "nicovideo.jp" in author_url and "/user/" in author_url:
                # Get author name from first video
                author_name = info.get("uploader") or info.get("title")

                if not author_name:
                    entries = info.get("entries", [])
                    if entries:
                        # Get first video to get author name
                        first_video_url = entries[0].get("url")
                        if first_video_url:
                            try:
                                video_options = options.copy()
                                video_options["extract_flat"] = False

                                with yt_dlp.YoutubeDL(video_options) as video_ydl:
                                    video_info = video_ydl.extract_info(
                                        first_video_url, download=False
                                    )
                                    author_name = video_info.get("uploader")
                            except Exception as e:
                                if debug:
                                    print(
                                        f"  Failed to get author name from video: {e}"
                                    )

                # Generate NicoNico avatar URL directly from user ID
                avatar = None
                try:
                    import re
                    import urllib.request

                    match = re.search(r"/user/(\d+)", author_url)
                    if match:
                        user_id = match.group(1)
                        # NicoNico avatar URL format: https://secure-dcdn.cdn.nimg.jp/nicoaccount/usericon/{prefix}/{user_id}.jpg
                        # Prefix length based on user ID length pattern observed:
                        # 9+ digits: 5 chars, 8 digits: 4 chars, 7 digits: 3 chars, 6 digits: 2 chars
                        prefixes_to_try = []
                        user_id_len = len(user_id)

                        if user_id_len >= 9:
                            # 9+ digit IDs: try 5, 4, 3 characters
                            prefixes_to_try = [user_id[:5], user_id[:4], user_id[:3]]
                        elif user_id_len == 8:
                            # 8 digit IDs: try 4, 3 characters
                            prefixes_to_try = [user_id[:4], user_id[:3]]
                        elif user_id_len == 7:
                            # 7 digit IDs: try 3, 4 characters (3 is more common)
                            prefixes_to_try = [user_id[:3], user_id[:4]]
                        elif user_id_len == 6:
                            # 6 digit IDs: try 2, 3 characters (2 is more common based on example)
                            prefixes_to_try = [user_id[:2], user_id[:3]]
                        elif user_id_len >= 3:
                            # 3-5 digit IDs: try 3, 2 characters
                            prefixes_to_try = [user_id[:3], user_id[:2]]
                        elif user_id_len >= 2:
                            # 2 digit IDs: try 2, full ID
                            prefixes_to_try = [user_id[:2], user_id]
                        else:
                            # Very short IDs: use full ID
                            prefixes_to_try = [user_id]

                        avatar_found = False
                        for prefix in prefixes_to_try:
                            constructed_avatar = f"https://secure-dcdn.cdn.nimg.jp/nicoaccount/usericon/{prefix}/{user_id}.jpg"

                            # Check if the constructed URL is valid (not 404)
                            try:
                                if debug:
                                    print(
                                        f"  Trying NicoNico avatar URL: {constructed_avatar}"
                                    )
                                req = urllib.request.Request(
                                    constructed_avatar, method="HEAD"
                                )
                                with urllib.request.urlopen(req, timeout=5) as response:
                                    if response.status == 200:
                                        avatar = constructed_avatar
                                        avatar_found = True
                                        if debug:
                                            print(
                                                f"  ✓ Found NicoNico avatar URL: {avatar}"
                                            )
                                        break
                            except urllib.error.HTTPError as http_err:
                                if debug:
                                    print(
                                        f"    HTTP {http_err.code} for prefix {prefix}"
                                    )
                                continue
                            except Exception as url_check_error:
                                if debug:
                                    print(
                                        f"    Error checking prefix {prefix}: {url_check_error}"
                                    )
                                continue

                        # If no valid avatar found, use default blank avatar
                        if not avatar_found:
                            avatar = "https://secure-dcdn.cdn.nimg.jp/nicoaccount/usericon/defaults/blank.jpg"
                            if debug:
                                print(
                                    f"  No custom avatar found, using default: {avatar}"
                                )
                except Exception as construct_error:
                    if debug:
                        print(f"  Failed to construct avatar URL: {construct_error}")

            # Bilibili user page
            elif "bilibili.com" in author_url and (
                "/space/" in author_url or "/u/" in author_url
            ):
                # Get from user space info
                author_name = info.get("uploader") or info.get("title")
                avatar = info.get("uploader_avatar") or info.get("avatar")

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


def get_authors_to_update(
    conn, force=False, author_id=None, author_name=None, author_id_after=None,
    update_names=False, update_avatars=False, update_links=False,
):
    """Select authors independently for missing links and requested metadata."""
    rows = conn.execute("""SELECT id,
        COALESCE(yt_name, nico_name, twitter_name),
        COALESCE(yt_url, nico_url, twitter_url),
        COALESCE(nico_avatar, yt_avatar, twitter_avatar),
        yt_name, yt_url, yt_avatar, nico_name, nico_url, nico_avatar,
        twitter_name, twitter_url, twitter_avatar FROM authors ORDER BY id""").fetchall()
    selected = []
    for row in rows:
        if author_id is not None:
            if row[0] == author_id:
                selected.append(row)
            continue
        if author_name:
            if row[1] == author_name:
                selected.append(row)
            continue
        if author_id_after is not None and row[0] <= author_id_after:
            continue
        platforms = [row[4:7], row[7:10], row[10:13]]
        if not any(not blank(url) for name, url, avatar in platforms):
            continue
        missing_links = update_links and any(blank(url) for name, url, avatar in platforms)
        needs_metadata = any(
            not blank(url) and (
                (update_names and (force or blank(name)))
                or (update_avatars and (force or blank(avatar)))
            ) for name, url, avatar in platforms
        )
        if missing_links or needs_metadata:
            selected.append(row)
    return selected


def update_author_info(
    conn, author_id, author_url, author_name=None, avatar_url=None, debug=False
):
    """Update author info based on URL source"""
    cursor = conn.cursor()

    try:
        # Determine which fields to update based on URL source
        if "youtube.com" in author_url:
            # YouTube source - update yt_* fields
            updates = []
            params = []

            if author_name:
                updates.append("yt_name = ?")
                params.append(author_name)
            if avatar_url:
                updates.append("yt_avatar = ?")
                params.append(avatar_url)

            if updates:
                params.append(author_id)
                query = f"UPDATE authors SET {', '.join(updates)} WHERE id = ?"
                cursor.execute(query, params)
                if debug:
                    if author_name and avatar_url:
                        print(f"  Updated YouTube name and avatar")
                    elif author_name:
                        print(f"  Updated YouTube name: {author_name}")
                    elif avatar_url:
                        print(f"  Updated YouTube avatar: {avatar_url}")

        elif "nicovideo.jp" in author_url:
            # NicoNico source - update nico_* fields
            updates = []
            params = []

            if author_name:
                updates.append("nico_name = ?")
                params.append(author_name)
            if avatar_url:
                updates.append("nico_avatar = ?")
                params.append(avatar_url)

            if updates:
                params.append(author_id)
                query = f"UPDATE authors SET {', '.join(updates)} WHERE id = ?"
                cursor.execute(query, params)
                if debug:
                    if author_name and avatar_url:
                        print(f"  Updated NicoNico name and avatar")
                    elif author_name:
                        print(f"  Updated NicoNico name: {author_name}")
                    elif avatar_url:
                        print(f"  Updated NicoNico avatar: {avatar_url}")

        elif "bilibili.com" in author_url:
            # Bilibili source - for now, treat as YouTube fields (can be adjusted)
            updates = []
            params = []

            if author_name:
                updates.append("yt_name = ?")
                params.append(author_name)
            if avatar_url:
                updates.append("yt_avatar = ?")
                params.append(avatar_url)

            if updates:
                params.append(author_id)
                query = f"UPDATE authors SET {', '.join(updates)} WHERE id = ?"
                cursor.execute(query, params)
                if debug:
                    if author_name and avatar_url:
                        print(f"  Updated Bilibili name and avatar")
                    elif author_name:
                        print(f"  Updated Bilibili name: {author_name}")
                    elif avatar_url:
                        print(f"  Updated Bilibili avatar: {avatar_url}")

        elif "twitter.com" in author_url or "x.com" in author_url:
            # Twitter/X source - update twitter_* fields
            updates = []
            params = []

            if author_name:
                updates.append("twitter_name = ?")
                params.append(author_name)
            if avatar_url:
                updates.append("twitter_avatar = ?")
                params.append(avatar_url)

            if updates:
                params.append(author_id)
                query = f"UPDATE authors SET {', '.join(updates)} WHERE id = ?"
                cursor.execute(query, params)
                if debug:
                    if author_name and avatar_url:
                        print(f"  Updated Twitter name and avatar")
                    elif author_name:
                        print(f"  Updated Twitter name: {author_name}")
                    elif avatar_url:
                        print(f"  Updated Twitter avatar: {avatar_url}")
        else:
            if debug:
                print(f"  Unknown URL source: {author_url}")
            return False

        if not updates:
            return False

        conn.commit()
        return True
    except Exception as e:
        if debug:
            print(f"  Database update failed: {e}")
        return False


def process_authors(
    conn,
    force=False,
    author_id=None,
    author_name=None,
    author_id_after=None,
    update_names=False,
    update_avatars=False,
    debug=False,
    update_links=False,
    dry_run=False,
):
    """Process author info updates"""
    # If no update options specified, default to update avatars
    if not update_names and not update_avatars and not update_links:
        update_avatars = True

    authors = get_authors_to_update(
        conn,
        force,
        author_id,
        author_name,
        author_id_after,
        update_names,
        update_avatars,
        update_links,
    )

    if not authors:
        print("No authors found that need updating")
        return

    backup_conn = None
    if dry_run:
        backup_conn = conn
        conn = sqlite3.connect(":memory:")
        backup_conn.backup(conn)
    elif update_links:
        from author_links import backup_database
        backup_database(conn)

    update_type = []
    if update_links:
        update_type.append("links")
    if update_names:
        update_type.append("names")
    if update_avatars:
        update_type.append("avatars")

    print(f"Found {len(authors)} authors need {'/'.join(update_type)} update")

    stats = {"total": len(authors), "updated": 0, "failed": 0, "skipped": 0}

    link_stats = {"filled": 0, "conflicts": 0, "failed": 0}
    for i, row in enumerate(authors, 1):
        # Unpack the row - now includes all the individual fields
        author_id, name, url, current_avatar = row[0], row[1], row[2], row[3]
        (
            yt_name,
            yt_url,
            yt_avatar,
            nico_name,
            nico_url,
            nico_avatar,
            twitter_name,
            twitter_url,
            twitter_avatar,
        ) = (
            row[4],
            row[5],
            row[6],
            row[7],
            row[8],
            row[9],
            row[10],
            row[11],
            row[12],
        )

        print(
            f"\n[{i}/{len(authors)}] Processing author: {name or 'Unknown'} (ID: {author_id})"
        )

        links_updated = False
        if update_links and any(blank(value) for value in (yt_url, nico_url, twitter_url)):
            existing = dict(zip(FIELDS, (yt_url, nico_url, twitter_url)))
            found, conflicts, failures = discover_links(existing, _fxtwitter_request)
            link_stats["conflicts"] += conflicts
            link_stats["failed"] += failures
            try:
                for field, value in found.items():
                    current = conn.execute(
                        f"SELECT {field} FROM authors WHERE id = ?", (author_id,)
                    ).fetchone()
                    if current is None or not blank(current[0]):
                        continue
                    cursor = conn.execute(
                        f"UPDATE authors SET {field} = ? WHERE id = ? "
                        f"AND {field} IS ?",
                        (value, author_id, current[0]),
                    )
                    link_stats["filled"] += cursor.rowcount
                    links_updated = links_updated or bool(cursor.rowcount)
                conn.commit()
            except sqlite3.Error:
                conn.rollback()
                raise
            yt_url, nico_url, twitter_url = conn.execute(
                "SELECT yt_url, nico_url, twitter_url FROM authors WHERE id = ?", (author_id,)
            ).fetchone()

        # Process YouTube URL if exists
        yt_updated = False
        if not blank(yt_url) and (update_names or update_avatars):
            print(f"  YouTube URL: {yt_url}")

            # Check if should skip based on existing data
            skip_yt_name = update_names and yt_name and not force
            skip_yt_avatar = update_avatars and yt_avatar and not force

            if (update_names and not skip_yt_name) or (update_avatars and not skip_yt_avatar):
                try:
                    fetched_name, fetched_avatar = get_author_info_from_url(
                        yt_url, debug
                    )

                    # Determine what info to update for YouTube
                    update_yt_name = None
                    update_yt_avatar = None

                    if update_names and fetched_name and (not yt_name or force):
                        update_yt_name = fetched_name

                    if update_avatars and fetched_avatar and (not yt_avatar or force):
                        update_yt_avatar = fetched_avatar

                    if update_yt_name or update_yt_avatar:
                        if update_author_info(
                            conn,
                            author_id,
                            yt_url,
                            update_yt_name,
                            update_yt_avatar,
                            debug,
                        ):
                            success_msg = "  ✓ YouTube update successful:"
                            if update_yt_name:
                                success_msg += f" Name: {update_yt_name}"
                            if update_yt_avatar:
                                success_msg += f" Avatar: {update_yt_avatar}"
                            print(success_msg)
                            yt_updated = True
                        else:
                            print(f"  ✗ YouTube database update failed")
                    else:
                        print(f"  - No updatable YouTube info found")

                except Exception as e:
                    print(f"  ✗ YouTube processing failed: {e}")
            else:
                print(f"  - Skipped YouTube: Already has complete info")

        # Process NicoNico URL if exists
        nico_updated = False
        if not blank(nico_url) and (update_names or update_avatars):
            print(f"  NicoNico URL: {nico_url}")

            # Check if should skip based on existing data
            skip_nico_name = update_names and nico_name and not force
            skip_nico_avatar = update_avatars and nico_avatar and not force

            if (update_names and not skip_nico_name) or (update_avatars and not skip_nico_avatar):
                try:
                    fetched_name, fetched_avatar = get_author_info_from_url(
                        nico_url, debug
                    )

                    # Determine what info to update for NicoNico
                    update_nico_name = None
                    update_nico_avatar = None

                    if update_names and fetched_name and (not nico_name or force):
                        update_nico_name = fetched_name

                    if update_avatars and fetched_avatar and (not nico_avatar or force):
                        update_nico_avatar = fetched_avatar

                    if update_nico_name or update_nico_avatar:
                        if update_author_info(
                            conn,
                            author_id,
                            nico_url,
                            update_nico_name,
                            update_nico_avatar,
                            debug,
                        ):
                            success_msg = "  ✓ NicoNico update successful:"
                            if update_nico_name:
                                success_msg += f" Name: {update_nico_name}"
                            if update_nico_avatar:
                                success_msg += f" Avatar: {update_nico_avatar}"
                            print(success_msg)
                            nico_updated = True
                        else:
                            print(f"  ✗ NicoNico database update failed")
                    else:
                        print(f"  - No updatable NicoNico info found")

                except Exception as e:
                    print(f"  ✗ NicoNico processing failed: {e}")
            else:
                print(f"  - Skipped NicoNico: Already has complete info")

        # Process Twitter URL if exists
        twitter_updated = False
        if not blank(twitter_url) and (update_names or update_avatars):
            print(f"  Twitter URL: {twitter_url}")

            # Check if should skip based on existing data
            skip_twitter_name = update_names and twitter_name and not force
            skip_twitter_avatar = update_avatars and twitter_avatar and not force

            if (update_names and not skip_twitter_name) or (update_avatars and not skip_twitter_avatar):
                try:
                    fetched_name, fetched_avatar = get_author_info_from_url(
                        twitter_url, debug
                    )

                    # Determine what info to update for Twitter
                    update_twitter_name = None
                    update_twitter_avatar = None

                    if update_names and fetched_name and (not twitter_name or force):
                        update_twitter_name = fetched_name

                    if (
                        update_avatars
                        and fetched_avatar
                        and (not twitter_avatar or force)
                    ):
                        update_twitter_avatar = fetched_avatar

                    if update_twitter_name or update_twitter_avatar:
                        if update_author_info(
                            conn,
                            author_id,
                            twitter_url,
                            update_twitter_name,
                            update_twitter_avatar,
                            debug,
                        ):
                            success_msg = "  ✓ Twitter update successful:"
                            if update_twitter_name:
                                success_msg += f" Name: {update_twitter_name}"
                            if update_twitter_avatar:
                                success_msg += f" Avatar: {update_twitter_avatar}"
                            print(success_msg)
                            twitter_updated = True
                        else:
                            print(f"  ✗ Twitter database update failed")
                    else:
                        print(f"  - No updatable Twitter info found")

                except Exception as e:
                    print(f"  ✗ Twitter processing failed: {e}")
            else:
                print(f"  - Skipped Twitter: Already has complete info")

        # Check if no URLs available
        if not yt_url and not nico_url and not twitter_url:
            print("  Skipped: No author URLs")
            stats["skipped"] += 1
        elif links_updated or yt_updated or nico_updated or twitter_updated:
            stats["updated"] += 1
        elif not yt_url and not nico_url and not twitter_url:
            stats["skipped"] += 1
        elif update_links and not update_names and not update_avatars:
            stats["skipped"] += 1
        else:
            stats["failed"] += 1

        # Add delay to avoid too frequent requests
        if i < len(authors):
            time.sleep(1)

    if dry_run:
        conn.close()
        print("Preview only: original database unchanged; no backup created.")
    if update_links:
        print(f"Links filled: {link_stats['filled']}; conflicts: {link_stats['conflicts']}; fetch failures: {link_stats['failed']}")

    # Print statistics
    print(f"\n=== Processing Complete ===")
    print(f"Total: {stats['total']} authors")
    print(f"Successfully updated: {stats['updated']}")
    print(f"Failed: {stats['failed']}")
    print(f"Skipped: {stats['skipped']}")


def main():
    _default_db = str(
        Path(os.environ.get("PROJECT_ROOT", str(Path(__file__).resolve().parents[2])))
        / "backend"
        / "random-2hu-stuff.db"
    )
    parser = argparse.ArgumentParser(
        description="Get author info from author URLs and update to database"
    )
    parser.add_argument("--db-path", default=_default_db, help="Database path")
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode, show detailed information",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force update all author info (including authors with existing info)",
    )
    parser.add_argument(
        "--author-id", type=int, help="Only update author with specified ID"
    )
    parser.add_argument("--author-name", help="Only update author with specified name")
    parser.add_argument(
        "--author-id-after",
        type=int,
        help="Update all authors with ID greater than specified value",
    )
    parser.add_argument(
        "--update-names", action="store_true", help="Enable author name update feature"
    )
    parser.add_argument(
        "--update-avatars", action="store_true", help="Enable avatar update feature"
    )
    parser.add_argument(
        "--update-all",
        action="store_true",
        help="Update both author names and avatars (equivalent to --update-names --update-avatars)",
    )

    parser.add_argument("--update-links", action="store_true", help="Fill missing platform URLs from profile descriptions and external links")
    parser.add_argument("--dry-run", action="store_true", help="Preview updates without modifying or backing up the database")

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
        if args.author_id is not None:
            print(f"*** Only update author ID: {args.author_id} ***")
        if args.author_name:
            print(f"*** Only update author: {args.author_name} ***")
        if args.author_id_after is not None:
            print(f"*** Update all authors with ID > {args.author_id_after} ***")

        # Show update options
        if update_names and update_avatars:
            print("*** Update author names and avatars ***")
        elif update_names:
            print("*** Only update author names ***")
        elif update_avatars:
            print("*** Only update avatars ***")
        elif not args.update_links:
            print("*** Default mode - Only update avatars ***")
        if args.update_links:
            print("*** Fill missing author profile links ***")
        if args.dry_run:
            print("*** Preview only ***")

        # Process author info updates
        process_authors(
            conn,
            args.force,
            args.author_id,
            args.author_name,
            args.author_id_after,
            update_names,
            update_avatars,
            args.debug,
            args.update_links,
            args.dry_run,
        )

    finally:
        conn.close()


if __name__ == "__main__":
    main()
