#!/usr/bin/env python3
"""
CSV Video Data Import Script

Import video data from CSV file to database. CSV format:
Author,Original Video Link,Repost Title,Repost Link,Translation Status,Notes,Supplementary Note

Usage:
python3 csv_import.py input.csv

Optional arguments:
--db-path: Database path (default: ../backend/random-2hu-stuff.db)
--dry-run: Check only, do not actually import
--skip-metadata: Skip metadata retrieval from links, use titles from CSV
--workers: Number of concurrent metadata requests (default: 4)
--cookies: Netscape formatted cookie file to read cookies from
--cookies-from-browser: Extract cookies from specified browser to handle restricted videos
                       Supported browsers: brave, chrome, chromium, edge, firefox, opera, safari, vivaldi, whale, qutebrowser
                       Format: BROWSER[+KEYRING][:PROFILE][::CONTAINER]
                       Examples: firefox, chrome, edge+gnomekeyring, safari:Default::Facebook Container, qutebrowser
                       Supported keyrings: basictext, gnomekeyring, kwallet, kwallet5, kwallet6
When a duplicate original video link is found, all matching records are shown and
you can choose how to handle the new record:
   - Skip: Keep existing record
   - Overwrite: Completely replace existing record with new record
   - Add: Force add as new record (will have duplicate links)
"""

import argparse
import csv
import os
import sqlite3
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

import yt_dlp

_ydl_local = threading.local()


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
    name = name.lstrip("\ufeff")

    # Remove leading and trailing whitespace
    name = name.strip()

    # Normalize whitespace (replace multiple spaces with single space)
    import re

    name = re.sub(r"\s+", " ", name)

    return name


def clean_bilibili_url(url):
    """Clean Bilibili links, keep only necessary parameters"""
    if not url or "bilibili.com" not in url:
        return url

    try:
        parsed = urlparse(url)
        query_params = parse_qs(parsed.query)

        # Only keep 'p' parameter (page number for multi-part videos)
        cleaned_params = {}
        if "p" in query_params:
            cleaned_params["p"] = query_params["p"]

        # Rebuild URL
        new_query = urlencode(cleaned_params, doseq=True) if cleaned_params else ""

        # If there are query parameters, ensure it starts with & (maintain original format consistency)
        if new_query and not new_query.startswith("&"):
            new_query = "&" + new_query

        cleaned_url = urlunparse(
            (
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                parsed.params,
                new_query.lstrip(
                    "&"
                ),  # Remove leading &, as urlunparse handles it automatically
                parsed.fragment,
            )
        )

        return cleaned_url

    except Exception as e:
        print(f"Failed to clean Bilibili link {url}: {e}")
        return url


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


@lru_cache(maxsize=None)
def get_twitter_avatar(screen_name):
    """Get Twitter user avatar URL via fxtwitter API (best effort)"""
    if not screen_name:
        return None

    try:
        data = _fxtwitter_request(screen_name)
        if not data:
            return None

        avatar = (data.get("user") or {}).get("avatar_url")
        if not avatar:
            return None

        # Prefer higher resolution like other records in database
        return avatar.replace("_normal.jpg", "_400x400.jpg")
    except Exception as e:
        print(f"Failed to get Twitter avatar for {screen_name}: {e}")
        return None


def build_ydl_options(browser_cookies=None, cookies_file=None):
    """Build yt-dlp options shared by each worker-local instance."""
    options = {
        "quiet": True,
        "skip_download": True,
        "extract_flat": False,
    }

    if cookies_file:
        options["cookiefile"] = cookies_file

    elif browser_cookies:
        if "+" in browser_cookies and ":" in browser_cookies:
            parts = browser_cookies.split("+", 1)
            browser = parts[0]
            keyring_profile_container = parts[1]
            if "::" in keyring_profile_container:
                keyring_profile, container = keyring_profile_container.split("::", 1)
                if ":" in keyring_profile:
                    keyring, profile = keyring_profile.split(":", 1)
                    options["cookiesfrombrowser"] = (
                        browser,
                        keyring,
                        profile,
                        container,
                    )
                else:
                    options["cookiesfrombrowser"] = (
                        browser,
                        keyring_profile,
                        None,
                        container,
                    )
            elif ":" in keyring_profile_container:
                keyring, profile = keyring_profile_container.split(":", 1)
                options["cookiesfrombrowser"] = (browser, keyring, profile)
            else:
                options["cookiesfrombrowser"] = (
                    browser,
                    keyring_profile_container,
                )
        elif "::" in browser_cookies:
            browser_profile, container = browser_cookies.split("::", 1)
            if ":" in browser_profile:
                browser, profile = browser_profile.split(":", 1)
                options["cookiesfrombrowser"] = (browser, None, profile, container)
            else:
                options["cookiesfrombrowser"] = (
                    browser_profile,
                    None,
                    None,
                    container,
                )
        elif ":" in browser_cookies:
            browser, profile = browser_cookies.split(":", 1)
            options["cookiesfrombrowser"] = (browser, None, profile)
        else:
            options["cookiesfrombrowser"] = (browser_cookies,)

    return options


def get_worker_ydl(browser_cookies=None, cookies_file=None):
    """Reuse one isolated YoutubeDL instance in each metadata worker."""
    key = (browser_cookies, cookies_file)
    if getattr(_ydl_local, "key", None) != key:
        _ydl_local.ydl = yt_dlp.YoutubeDL(
            build_ydl_options(browser_cookies, cookies_file)
        )
        _ydl_local.key = key
    return _ydl_local.ydl


def get_video_metadata(url, browser_cookies=None, cookies_file=None):
    """Get video metadata from URL."""
    if not url or url.strip() == "" or url == "未转载":
        return None, None, None, None, None

    try:
        ydl = get_worker_ydl(browser_cookies, cookies_file)

        info = ydl.extract_info(url, download=False)
        title = info.get("title")
        uploader = info.get("uploader")
        upload_date = (
            info.get("upload_date")
            or info.get("release_date")
            or info.get("timestamp")
            or info.get("upload_timestamp")
        )

        formatted_date = None
        if upload_date:
            try:
                if isinstance(upload_date, (int, float)):
                    formatted_date = datetime.fromtimestamp(upload_date).strftime(
                        "%Y-%m-%d"
                    )
                else:
                    date_str = str(upload_date)
                    if len(date_str) == 8 and date_str.isdigit():
                        formatted_date = (
                            f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
                        )
                    else:
                        formatted_date = date_str
            except Exception as error:
                print(f"Date formatting error: {upload_date} -> {error}")

        author_info = {
            "name": uploader,
            "url": None,
            "avatar": None,
            "platform": None,
        }
        if "youtube.com" in url or "youtu.be" in url:
            author_info["platform"] = "youtube"
            author_info["url"] = info.get("uploader_url") or info.get("channel_url")
        elif "nicovideo.jp" in url:
            author_info["platform"] = "niconico"
            uploader_id = info.get("uploader_id")
            if uploader_id:
                author_info["url"] = f"https://www.nicovideo.jp/user/{uploader_id}"
        elif "twitter.com" in url or "x.com" in url:
            author_info["platform"] = "twitter"
            uploader_id = info.get("uploader_id")
            if uploader_id:
                author_info["url"] = f"https://x.com/{uploader_id}"
                author_info["avatar"] = get_twitter_avatar(uploader_id)

        raw_duration = info.get("duration")
        duration = None
        if isinstance(raw_duration, (int, float)) and raw_duration >= 0:
            duration = round(raw_duration)

        thumbnail = info.get("thumbnail")
        if not thumbnail:
            thumbnails = info.get("thumbnails") or []
            if thumbnails:
                thumbnail = max(
                    thumbnails,
                    key=lambda item: (
                        item.get("preference") or 0,
                        item.get("width") or 0,
                        item.get("height") or 0,
                    ),
                ).get("url")
        if thumbnail and "hdslb.com" in thumbnail and thumbnail.startswith("http://"):
            thumbnail = thumbnail.replace("http://", "https://")

        return title, formatted_date, author_info, thumbnail, duration

    except Exception:
        raise


def get_or_create_author(conn, csv_author_name, author_info):
    """Get or create author with new platform-specific fields, return author ID"""
    cursor = conn.cursor()

    # Clean author name
    csv_author_name = clean_author_name(csv_author_name)

    # Step 1: Try to find by CSV author name in both platform name fields
    cursor.execute(
        """
        SELECT id, yt_name, yt_url, nico_name, nico_url, twitter_name, twitter_url, twitter_avatar
        FROM authors 
        WHERE yt_name = ? OR nico_name = ? OR twitter_name = ?
    """,
        (csv_author_name, csv_author_name, csv_author_name),
    )
    result = cursor.fetchone()

    if result:
        author_id = result[0]
        print(f"Found existing author by name: {csv_author_name} (ID: {author_id})")

        # If we have video metadata, update the corresponding platform fields
        if author_info and author_info.get("platform"):
            platform = author_info["platform"]
            name = author_info.get("name")
            url = author_info.get("url")

            if platform == "youtube" and url:
                # Update YouTube fields if empty
                if not result[2]:  # yt_url is empty
                    cursor.execute(
                        "UPDATE authors SET yt_url = ? WHERE id = ?", (url, author_id)
                    )
                    print(f"Updated YouTube URL for author: {csv_author_name}")
                if not result[1] and name:  # yt_name is empty
                    cursor.execute(
                        "UPDATE authors SET yt_name = ? WHERE id = ?", (name, author_id)
                    )
                    print(f"Updated YouTube name for author: {csv_author_name}")

            elif platform == "niconico" and url:
                # Update NicoNico fields if empty
                if not result[4]:  # nico_url is empty
                    cursor.execute(
                        "UPDATE authors SET nico_url = ? WHERE id = ?", (url, author_id)
                    )
                    print(f"Updated NicoNico URL for author: {csv_author_name}")
                if not result[3] and name:  # nico_name is empty
                    cursor.execute(
                        "UPDATE authors SET nico_name = ? WHERE id = ?",
                        (name, author_id),
                    )
                    print(f"Updated NicoNico name for author: {csv_author_name}")

            elif platform == "twitter" and url:
                # Update Twitter fields if empty
                if not result[6]:  # twitter_url is empty
                    cursor.execute(
                        "UPDATE authors SET twitter_url = ? WHERE id = ?",
                        (url, author_id),
                    )
                    print(f"Updated Twitter URL for author: {csv_author_name}")
                if not result[5] and name:  # twitter_name is empty
                    cursor.execute(
                        "UPDATE authors SET twitter_name = ? WHERE id = ?",
                        (name, author_id),
                    )
                    print(f"Updated Twitter name for author: {csv_author_name}")
                avatar = author_info.get("avatar")
                if not result[7] and avatar:  # twitter_avatar is empty
                    cursor.execute(
                        "UPDATE authors SET twitter_avatar = ? WHERE id = ?",
                        (avatar, author_id),
                    )
                    print(f"Updated Twitter avatar for author: {csv_author_name}")

        return author_id

    # Step 2: If not found by name, try to find by URL
    if author_info and author_info.get("url"):
        platform = author_info.get("platform")
        url = author_info["url"]

        if platform == "youtube":
            cursor.execute("SELECT id FROM authors WHERE yt_url = ?", (url,))
        elif platform == "niconico":
            cursor.execute("SELECT id FROM authors WHERE nico_url = ?", (url,))
        elif platform == "twitter":
            cursor.execute("SELECT id FROM authors WHERE twitter_url = ?", (url,))
        else:
            cursor.execute(
                "SELECT id FROM authors WHERE yt_url = ? OR nico_url = ? OR twitter_url = ?",
                (url, url, url),
            )

        result = cursor.fetchone()
        if result:
            author_id = result[0]
            print(f"Found existing author by URL (ID: {author_id})")

            # Get current author names to check if update is needed
            cursor.execute(
                "SELECT yt_name, nico_name, twitter_name, twitter_avatar FROM authors WHERE id = ?",
                (author_id,),
            )
            current_names = cursor.fetchone()
            (
                current_yt_name,
                current_nico_name,
                current_twitter_name,
                current_twitter_avatar,
            ) = current_names

            # Only update name if current name is empty or clearly inferior
            updated = False
            if platform == "youtube":
                if not current_yt_name or len(current_yt_name.strip()) == 0:
                    cursor.execute(
                        "UPDATE authors SET yt_name = ? WHERE id = ?",
                        (csv_author_name, author_id),
                    )
                    updated = True
                    print(f"Updated empty YouTube name to: {csv_author_name}")
                else:
                    print(
                        f"Keeping existing YouTube name: {current_yt_name} (not updating to: {csv_author_name})"
                    )
            elif platform == "niconico":
                if not current_nico_name or len(current_nico_name.strip()) == 0:
                    cursor.execute(
                        "UPDATE authors SET nico_name = ? WHERE id = ?",
                        (csv_author_name, author_id),
                    )
                    updated = True
                    print(f"Updated empty NicoNico name to: {csv_author_name}")
                else:
                    print(
                        f"Keeping existing NicoNico name: {current_nico_name} (not updating to: {csv_author_name})"
                    )
            elif platform == "twitter":
                if not current_twitter_name or len(current_twitter_name.strip()) == 0:
                    cursor.execute(
                        "UPDATE authors SET twitter_name = ? WHERE id = ?",
                        (csv_author_name, author_id),
                    )
                    updated = True
                    print(f"Updated empty Twitter name to: {csv_author_name}")
                else:
                    print(
                        f"Keeping existing Twitter name: {current_twitter_name} (not updating to: {csv_author_name})"
                    )
                avatar = author_info.get("avatar")
                if not current_twitter_avatar and avatar:
                    cursor.execute(
                        "UPDATE authors SET twitter_avatar = ? WHERE id = ?",
                        (avatar, author_id),
                    )
                    updated = True
                    print(f"Updated empty Twitter avatar for author: {csv_author_name}")
            else:
                # If platform unknown, only update empty fields
                if (not current_yt_name or len(current_yt_name.strip()) == 0) and (
                    not current_nico_name or len(current_nico_name.strip()) == 0
                ):
                    cursor.execute(
                        "UPDATE authors SET yt_name = ?, nico_name = ? WHERE id = ?",
                        (csv_author_name, csv_author_name, author_id),
                    )
                    updated = True
                    print(f"Updated empty author names to: {csv_author_name}")

            return author_id

    # Step 3: Create new author
    # Determine which fields to populate based on platform
    yt_name = None
    yt_url = None
    nico_name = None
    nico_url = None
    twitter_name = None
    twitter_url = None
    twitter_avatar = None

    if author_info and author_info.get("platform"):
        platform = author_info["platform"]
        metadata_name = (
            clean_author_name(author_info.get("name"))
            if author_info.get("name")
            else None
        )
        metadata_url = author_info.get("url")

        if platform == "youtube":
            # For YouTube, use metadata name if available, otherwise CSV name
            yt_name = metadata_name or csv_author_name
            yt_url = metadata_url
            print(f"Creating new author with YouTube info: {yt_name}")
        elif platform == "niconico":
            # For NicoNico, use metadata name if available, otherwise CSV name
            nico_name = metadata_name or csv_author_name
            nico_url = metadata_url
            print(f"Creating new author with NicoNico info: {nico_name}")
        elif platform == "twitter":
            # For Twitter, use metadata name if available, otherwise CSV name
            twitter_name = metadata_name or csv_author_name
            twitter_url = metadata_url
            twitter_avatar = author_info.get("avatar")
            print(f"Creating new author with Twitter info: {twitter_name}")
    else:
        # No platform info, use CSV name for both (fallback for compatibility)
        yt_name = csv_author_name
        nico_name = csv_author_name
        print(
            f"Creating new author without platform info, using CSV name: {csv_author_name}"
        )

    cursor.execute(
        """
        INSERT INTO authors (yt_name, yt_url, nico_name, nico_url, twitter_name, twitter_url, twitter_avatar) 
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """,
        (
            yt_name,
            yt_url,
            nico_name,
            nico_url,
            twitter_name,
            twitter_url,
            twitter_avatar,
        ),
    )
    author_id = cursor.lastrowid

    # Show which fields were populated
    populated_fields = []
    if yt_name:
        populated_fields.append(f"yt_name='{yt_name}'")
    if yt_url:
        populated_fields.append(f"yt_url='{yt_url}'")
    if nico_name:
        populated_fields.append(f"nico_name='{nico_name}'")
    if nico_url:
        populated_fields.append(f"nico_url='{nico_url}'")
    if twitter_name:
        populated_fields.append(f"twitter_name='{twitter_name}'")
    if twitter_url:
        populated_fields.append(f"twitter_url='{twitter_url}'")
    if twitter_avatar:
        populated_fields.append(f"twitter_avatar='{twitter_avatar}'")

    print(f"Created new author (ID: {author_id}): {', '.join(populated_fields)}")
    return author_id


def simulate_author_creation(csv_author_name, author_info):
    """Simulate author creation for dry-run mode, return mock author info"""
    csv_author_name = clean_author_name(csv_author_name)

    # Simulate the logic without database operations
    yt_name = None
    yt_url = None
    nico_name = None
    nico_url = None
    twitter_name = None
    twitter_url = None
    twitter_avatar = None

    if author_info and author_info.get("platform"):
        platform = author_info["platform"]
        metadata_name = (
            clean_author_name(author_info.get("name"))
            if author_info.get("name")
            else None
        )
        metadata_url = author_info.get("url")

        if platform == "youtube":
            yt_name = metadata_name or csv_author_name
            yt_url = metadata_url
        elif platform == "niconico":
            nico_name = metadata_name or csv_author_name
            nico_url = metadata_url
        elif platform == "twitter":
            twitter_name = metadata_name or csv_author_name
            twitter_url = metadata_url
            twitter_avatar = author_info.get("avatar")
    else:
        # No platform info, use CSV name for both
        yt_name = csv_author_name
        nico_name = csv_author_name

    # Show which fields would be populated
    populated_fields = []
    if yt_name:
        populated_fields.append(f"yt_name='{yt_name}'")
    if yt_url:
        populated_fields.append(f"yt_url='{yt_url}'")
    if nico_name:
        populated_fields.append(f"nico_name='{nico_name}'")
    if nico_url:
        populated_fields.append(f"nico_url='{nico_url}'")
    if twitter_name:
        populated_fields.append(f"twitter_name='{twitter_name}'")
    if twitter_url:
        populated_fields.append(f"twitter_url='{twitter_url}'")
    if twitter_avatar:
        populated_fields.append(f"twitter_avatar='{twitter_avatar}'")

    print(f"[DRY RUN] Would create author: {', '.join(populated_fields)}")

    # Return display name for video assignment
    return yt_name or nico_name or twitter_name or csv_author_name


def get_author_display_name(conn, author_id):
    """Get author display name based on priority: yt_name > nico_name > twitter_name"""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT yt_name, nico_name, twitter_name FROM authors WHERE id = ?",
        (author_id,),
    )
    result = cursor.fetchone()
    if result:
        yt_name, nico_name, twitter_name = result
        return yt_name or nico_name or twitter_name or "Unknown"
    return "Unknown"


def insert_video_wrapper(
    conn,
    author_id,
    title,
    original_url,
    date_str,
    repost_name,
    repost_url,
    original_thumbnail,
    original_duration,
    repost_thumbnail,
    repost_duration,
    translation_status,
    comment=None,
    supplementary_note=None,
):
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
            cursor.execute(
                """
                SELECT id, original_name, date, repost_name, repost_url, translation_status, comment, author FROM videos 
                WHERE original_url = ?
                ORDER BY id
            """,
                (original_url,),
            )

            existing_records = cursor.fetchall()
        else:
            existing_records = []

        if existing_records:
            print(f"\n🔄 Found duplicate original video link:")
            print(f"   URL: {original_url}")
            print(f"\n📹 Existing records in database ({len(existing_records)}):")

            for index, existing in enumerate(existing_records, 1):
                (
                    existing_id,
                    existing_title,
                    existing_date,
                    existing_repost_name,
                    existing_repost_url,
                    existing_translation_status,
                    existing_comment,
                    existing_author_id,
                ) = existing
                existing_author_name = get_author_display_name(conn, existing_author_id)
                print(f"\n   [{index}] Record ID: {existing_id}")
                print(f"   Title: {existing_title}")
                print(f"   Date: {existing_date or 'Unknown'}")
                print(f"   Repost title: {existing_repost_name or 'None'}")
                print(f"   Repost link: {existing_repost_url or 'None'}")
                print(
                    f"   Translation status: {get_translation_status_text(existing_translation_status)}"
                )
                print(f"   Notes: {existing_comment or 'None'}")
                print(f"   Author: {existing_author_name}")

            print(f"\n🆕 New record information:")
            print(f"   Title: {title}")
            print(f"   Date: {date_str or 'Unknown'}")
            print(f"   Repost title: {repost_name or 'None'}")
            print(f"   Repost link: {repost_url or 'None'}")
            print(
                f"   Translation status: {get_translation_status_text(translation_status)}"
            )
            print(f"   Notes: {comment or 'None'}")
            if supplementary_note:
                print(f"   📝 Supplementary note: {supplementary_note}")
            new_author_name = get_author_display_name(conn, author_id)
            print(f"   Author: {new_author_name}")

            print(f"\nPlease choose action:")
            print(f"  [1] Skip - Keep existing records")
            print(
                f"  [2] Overwrite - Completely replace one existing record with new record"
            )
            print(f"  [3] Add - Force add as new record (will have duplicate links)")
            print(f"  [q] Exit program")

            while True:
                choice = input("Please enter choice [1/2/3/q]: ").strip().lower()
                if choice in ["1", "2", "3", "q"]:
                    break
                print("❌ Invalid choice, please enter again")

            if choice == "q":
                print("🛑 User chose to exit program")
                return "cancelled"
            if choice == "1":
                print("⏭️  Skipped, keeping existing records")
                return "skipped"
            if choice == "2":
                if len(existing_records) == 1:
                    target = existing_records[0]
                else:
                    while True:
                        target_choice = (
                            input(
                                f"Please select record to overwrite [1-{len(existing_records)}/q]: "
                            )
                            .strip()
                            .lower()
                        )
                        if target_choice == "q":
                            print("🛑 User chose to exit program")
                            return "cancelled"
                        if target_choice.isdigit():
                            target_index = int(target_choice)
                            if 1 <= target_index <= len(existing_records):
                                target = existing_records[target_index - 1]
                                break
                        print("❌ Invalid record number, please enter again")

                cursor.execute(
                    """
                    UPDATE videos SET
                    author = ?, original_name = ?,
                    original_thumbnail = COALESCE(?, original_thumbnail),
                    original_duration = COALESCE(?, original_duration), date = ?,
                    repost_name = ?, repost_url = ?,
                    repost_thumbnail = COALESCE(?, repost_thumbnail),
                    repost_duration = COALESCE(?, repost_duration),
                    translation_status = ?, comment = ?
                    WHERE id = ?
                """,
                    (
                        author_id,
                        title,
                        original_thumbnail,
                        original_duration,
                        date_str,
                        repost_name,
                        repost_url,
                        repost_thumbnail,
                        repost_duration,
                        translation_status,
                        comment,
                        target[0],
                    ),
                )
                print(f"✅ Overwritten existing record (ID: {target[0]})")
                return "updated"
            if choice == "3":
                cursor.execute(
                    """
                    INSERT INTO videos
                    (author, original_name, original_url, original_thumbnail,
                     original_duration, date, repost_name, repost_url,
                     repost_thumbnail, repost_duration, translation_status, comment)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        author_id,
                        title,
                        original_url,
                        original_thumbnail,
                        original_duration,
                        date_str,
                        repost_name,
                        repost_url,
                        repost_thumbnail,
                        repost_duration,
                        translation_status,
                        comment,
                    ),
                )
                print("➕ Force added as new record")
                return "inserted"
        # Insert new video
        cursor.execute(
            """
            INSERT INTO videos 
            (author, original_name, original_url, original_thumbnail,
             original_duration, date, repost_name, repost_url,
             repost_thumbnail, repost_duration, translation_status, comment)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                author_id,
                title,
                original_url,
                original_thumbnail,
                original_duration,
                date_str,
                repost_name,
                repost_url,
                repost_thumbnail,
                repost_duration,
                translation_status,
                comment,
            ),
        )

        print(f"➕ Inserted new video: {title or 'No title'}")
        if repost_name:
            print(f"   Repost title: {repost_name}")
        if repost_url:
            print(f"   Repost link: {repost_url}")
        if comment:
            print(f"   Notes: {comment}")
        print(
            f"   Translation status: {get_translation_status_text(translation_status)}"
        )

        return "inserted"

    except Exception as e:
        print(f"❌ Failed to insert video: {e}")
        print(f"   Title: {title}")
        print(f"   URL: {original_url}")
        return "error"


def get_translation_status_text(status):
    """Get text description of translation status"""
    status_map = {
        1: "Chinese Embedded",
        2: "CC Subtitles",
        3: "Danmaku Translation",
        4: "No Translation Needed",
        5: "No Translation Yet",
        0: "Not Set",
        None: "Not Set",
    }
    return status_map.get(status, f"Unknown Status({status})")


def video_exists(conn, original_url):
    """Check if video already exists"""
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM videos WHERE original_url = ?", (original_url,))
    return cursor.fetchone() is not None


def insert_video(
    cursor,
    author_id,
    title,
    url,
    date,
    repost_name,
    repost_url,
    original_thumbnail,
    original_duration,
    repost_thumbnail,
    repost_duration,
    translation_status,
    comment,
):
    """Insert video record to database"""
    cursor.execute(
        """
        INSERT INTO videos 
        (author, original_name, original_url, original_thumbnail,
         original_duration, date, repost_name, repost_url,
         repost_thumbnail, repost_duration, translation_status, comment)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            author_id,
            title,
            url,
            original_thumbnail,
            original_duration,
            date,
            repost_name,
            repost_url,
            repost_thumbnail,
            repost_duration,
            translation_status,
            comment,
        ),
    )

    print(f"  Inserted video: {title} (Author ID: {author_id})")
    if repost_name and repost_name != "":
        print(f"    Repost title: {repost_name}")
    if repost_url and repost_url != "":
        print(f"    Repost link: {repost_url}")
    print(f"    Translation status: {translation_status}")
    if comment:
        print(f"    Notes: {comment}")
    print()


def parse_csv_line(line):
    """Parse CSV line, return processed data"""
    parts = [part.strip() for part in line.split(",")]

    # Ensure at least 7 columns
    while len(parts) < 7:
        parts.append("")

    author_name = parts[0]
    original_url = parts[1]
    repost_name = parts[2] if parts[2] else None  # Repost title
    repost_url = parts[3] if parts[3] else None  # Repost link
    translation_status = parts[4]
    comment = parts[5] if parts[5] else None  # Notes (for database)
    supplementary_note = (
        parts[6] if parts[6] else None
    )  # Supplementary note (for display only)

    print(f"Parsing CSV line:")
    print(f"  Author: {author_name}")
    print(f"  Original video link: {original_url}")
    print(f"  Repost title: {repost_name}")
    print(f"  Repost link: {repost_url}")
    print(f"  Translation status: {translation_status}")
    print(f"  Notes: {comment}")
    if supplementary_note:
        print(f"  Supplementary note: {supplementary_note}")

    return (
        author_name,
        original_url,
        repost_name,
        repost_url,
        translation_status,
        comment,
        supplementary_note,
    )


def write_error_to_csv(error_file, line_num, line_content, error_msg):
    """Write error line to error CSV file"""
    import csv as csv_module

    # If file doesn't exist, create and write header
    file_exists = os.path.exists(error_file)

    with open(error_file, "a", encoding="utf-8", newline="") as f:
        writer = csv_module.writer(f)

        if not file_exists:
            writer.writerow(["Line Number", "CSV Content", "Error Message"])

        writer.writerow([line_num, line_content, error_msg])


def read_csv_rows(input_file):
    """Parse and normalize input rows before any network or database work."""
    rows = []
    with open(input_file, "r", encoding="utf-8-sig", newline="") as source:
        for line_num, line in enumerate(source, 1):
            original_line = line.rstrip("\r\n")
            if not original_line.strip():
                continue
            parts = next(csv.reader([original_line]))
            if len(parts) < 2:
                print(f"Skipping line {line_num}: Incorrect format")
                continue
            parts.extend([""] * (7 - len(parts)))
            csv_author = clean_author_name(parts[0])
            if not csv_author:
                print(f"Skipping line {line_num}: Author name is empty")
                continue
            original_url = clean_bilibili_url(parts[1].strip())
            repost_url = clean_bilibili_url(parts[3].strip()) or None
            rows.append(
                {
                    "line_num": line_num,
                    "original_line": original_line,
                    "author": csv_author,
                    "original_url": original_url,
                    "repost_name": parts[2].strip() or None,
                    "repost_url": repost_url,
                    "translation_status": parts[4].strip(),
                    "comment": parts[5].strip() or None,
                    "supplementary_note": parts[6].strip() or None,
                }
            )
    return rows


def prefetch_metadata(
    rows,
    workers,
    browser_cookies=None,
    cookies_file=None,
    metadata_fetcher=None,
):
    """Fetch every unique original/repost URL once and return cached outcomes."""
    if workers < 1:
        raise ValueError("workers must be at least 1")
    metadata_fetcher = metadata_fetcher or get_video_metadata
    urls = []
    references = 0
    seen = set()
    for row in rows:
        for url in (row["original_url"], row["repost_url"]):
            if not url or url == "未转载":
                continue
            references += 1
            if url not in seen:
                seen.add(url)
                urls.append(url)

    print(
        f"Fetching {len(urls)} unique URLs with {workers} workers "
        f"({references - len(urls)} duplicate references reused)"
    )
    if not urls:
        return {}

    def fetch_job(url):
        try:
            return metadata_fetcher(url, browser_cookies, cookies_file), None
        except Exception as error:
            return None, error

    results = {}
    executor = ThreadPoolExecutor(max_workers=workers)
    futures = {executor.submit(fetch_job, url): url for url in urls}
    interrupted = False
    try:
        for completed, future in enumerate(as_completed(futures), 1):
            url = futures[future]
            metadata, error = future.result()
            results[url] = (metadata, error)
            print(f"[{completed}/{len(urls)}] {url}")
            if error is None:
                title = metadata[0] or "No title"
                print(f"  ✅ {title}")
            else:
                print(f"  ❌ Metadata failed: {error}")
    except KeyboardInterrupt:
        interrupted = True
        print("\nInterrupted; cancelling pending metadata requests...")
        for future in futures:
            future.cancel()
        raise
    finally:
        executor.shutdown(wait=not interrupted, cancel_futures=True)
    return results


def process_csv(
    input_file,
    conn,
    dry_run=False,
    skip_metadata=False,
    browser_cookies=None,
    cookies_file=None,
    workers=4,
    metadata_fetcher=None,
):
    """Process a CSV with concurrent metadata fetching and ordered DB writes."""
    stats = {
        "total_rows": 0,
        "processed_rows": 0,
        "new_authors": 0,
        "new_videos": 0,
        "updated_videos": 0,
        "skipped_videos": 0,
        "errors": 0,
        "cancelled": 0,
    }
    error_file = str(Path(input_file).with_suffix("")) + "_errors.csv"
    error_rows = set()
    reported_metadata_errors = set()
    author_cache = {}
    author_id_cache = {}
    pending_writes = 0

    try:
        rows = read_csv_rows(input_file)
    except Exception as error:
        print(f"Error reading CSV file: {error}")
        return stats

    stats["total_rows"] = len(rows)
    metadata_results = {}
    if not skip_metadata:
        metadata_results = prefetch_metadata(
            rows,
            workers,
            browser_cookies,
            cookies_file,
            metadata_fetcher,
        )

    def record_metadata_error(row, url, label, error):
        key = (row["line_num"], url)
        if key in reported_metadata_errors:
            return
        reported_metadata_errors.add(key)
        error_rows.add(row["line_num"])
        error_msg = str(error)
        print(f"Line {row['line_num']} failed to get {label} metadata: {error_msg}")
        write_error_to_csv(
            error_file,
            row["line_num"],
            row["original_line"],
            error_msg,
        )

    for row in rows:
        line_num = row["line_num"]
        csv_author = row["author"]
        original_url = row["original_url"]
        repost_name = row["repost_name"]
        repost_url = row["repost_url"]
        print(f"\nProcessing line {line_num}: {csv_author}")
        print(f"  Original video link: {original_url}")
        if repost_name:
            print(f"  Repost title: {repost_name}")
        if repost_url:
            print(f"  Repost link: {repost_url}")
        if row["comment"]:
            print(f"  Notes: {row['comment']}")

        try:
            original_metadata, original_error = metadata_results.get(
                original_url, (None, None)
            )
            repost_metadata, repost_error = metadata_results.get(
                repost_url, (None, None)
            )

            if csv_author not in author_cache:
                author_cache[csv_author] = (
                    original_metadata[2] if original_metadata is not None else None
                )
            author_info = author_cache[csv_author]

            if not dry_run:
                if csv_author in author_id_cache:
                    author_id = author_id_cache[csv_author]
                    print(f"Using cached author ID: {csv_author} (ID: {author_id})")
                else:
                    author_id = get_or_create_author(conn, csv_author, author_info)
                    author_id_cache[csv_author] = author_id
            else:
                if csv_author not in author_id_cache:
                    author_id_cache[csv_author] = simulate_author_creation(
                        csv_author, author_info
                    )
                else:
                    print(
                        f"[DRY RUN] Using cached author: {author_id_cache[csv_author]}"
                    )
                author_id = 1

            title = repost_name if skip_metadata or not original_url else None
            date_str = None
            original_thumbnail = None
            original_duration = None
            repost_thumbnail = None
            repost_duration = None
            if original_metadata is not None:
                (
                    title,
                    date_str,
                    _,
                    original_thumbnail,
                    original_duration,
                ) = original_metadata
            elif original_error is not None:
                record_metadata_error(
                    row, original_url, "original video", original_error
                )
            elif not original_url:
                print(f"  Original video link is empty, using repost title: {title}")

            if repost_metadata is not None:
                _, _, _, repost_thumbnail, repost_duration = repost_metadata
            elif repost_error is not None:
                record_metadata_error(row, repost_url, "repost", repost_error)

            translation_status = row["translation_status"]
            translation_status_int = (
                int(translation_status) if translation_status.isdigit() else 0
            )
            if not dry_run:
                result = insert_video_wrapper(
                    conn,
                    author_id,
                    title,
                    original_url,
                    date_str,
                    repost_name,
                    repost_url,
                    original_thumbnail,
                    original_duration,
                    repost_thumbnail,
                    repost_duration,
                    translation_status_int,
                    row["comment"],
                    row["supplementary_note"],
                )
                if result == "inserted":
                    stats["new_videos"] += 1
                elif result == "updated":
                    stats["updated_videos"] += 1
                elif result == "skipped":
                    stats["skipped_videos"] += 1
                elif result == "cancelled":
                    stats["cancelled"] += 1
                    conn.commit()
                    print("🛑 Program cancelled by user")
                    stats["errors"] = len(error_rows)
                    return stats
                else:
                    error_rows.add(line_num)

                pending_writes += 1
                if pending_writes >= 50:
                    conn.commit()
                    pending_writes = 0
            else:
                print(f"[DRY RUN] Will add video: {title or 'No title'}")
                print(f"  → Assigned to author: {author_id_cache[csv_author]}")
                stats["new_videos"] += 1

            stats["processed_rows"] += 1
        except Exception as error:
            print(f"Error processing line {line_num}: {error}")
            print(f"Line content: {row['original_line']}")
            write_error_to_csv(error_file, line_num, row["original_line"], str(error))
            error_rows.add(line_num)

    if pending_writes and not dry_run:
        conn.commit()
    stats["errors"] = len(error_rows)
    if stats["errors"]:
        print(f"\nError records saved to: {error_file}")
    return stats


def main():
    _default_db = str(
        Path(os.environ.get("PROJECT_ROOT", str(Path(__file__).parent.parent.parent)))
        / "backend"
        / "random-2hu-stuff.db"
    )
    parser = argparse.ArgumentParser(
        description="Import video data from CSV file to database"
    )
    parser.add_argument("csv_file", help="CSV file path")
    parser.add_argument("--db-path", default=_default_db, help="Database path")
    parser.add_argument(
        "--dry-run", action="store_true", help="Check only, do not actually import"
    )
    parser.add_argument(
        "--skip-metadata",
        action="store_true",
        help="Skip metadata retrieval from links, use titles from CSV",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Number of concurrent metadata requests (default: 4)",
    )
    parser.add_argument(
        "--cookies",
        type=str,
        help="Netscape formatted file to read cookies from and dump cookie jar in. For qutebrowser, use: ~/.local/share/qutebrowser/cookies",
    )
    parser.add_argument(
        "--cookies-from-browser",
        type=str,
        help="Extract cookies from specified browser to handle restricted videos. Supported browsers: brave, chrome, chromium, edge, firefox, opera, safari, vivaldi, whale. Format: BROWSER[+KEYRING][:PROFILE][::CONTAINER]. Supported keyrings: basictext, gnomekeyring, kwallet, kwallet5, kwallet6. Note: qutebrowser not supported, use --cookies instead",
    )
    args = parser.parse_args()

    if args.workers < 1:
        parser.error("--workers must be at least 1")

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
            print(
                "*** Skip metadata mode - Use titles from CSV, do not get release dates ***"
            )
        else:
            print(f"*** Concurrent metadata workers: {args.workers} ***")
        if args.cookies:
            print(f"*** Using cookies from file: {args.cookies} ***")
        if args.cookies_from_browser:
            print(
                f"*** Using {args.cookies_from_browser} browser cookies to handle restricted videos ***"
            )

        # Process CSV
        stats = process_csv(
            args.csv_file,
            conn,
            args.dry_run,
            args.skip_metadata,
            args.cookies_from_browser,
            args.cookies,
            args.workers,
        )

        # Print statistics
        print(f"\n=== 📊 Processing Complete ===")
        print(f"Total rows: {stats['total_rows']}")
        print(f"Processed rows: {stats['processed_rows']}")
        print(f"New videos: {stats['new_videos']}")
        print(f"Updated videos: {stats['updated_videos']}")
        print(f"Skipped videos: {stats['skipped_videos']}")
        if stats["cancelled"] > 0:
            print(f"User cancelled: {stats['cancelled']}")
        print(f"Error rows: {stats['errors']}")

    except KeyboardInterrupt:
        conn.commit()
        print("\nInterrupted; committed completed CSV rows.")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
