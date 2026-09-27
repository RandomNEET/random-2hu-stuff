#!/usr/bin/env python3
"""
Video Metadata Update Script

Get thumbnails and durations from video links and update the database.

Usage:
python3 metadata-updater.py

Optional arguments:
--db-path: Database path (default: ../backend/random-2hu-stuff.db)
--debug: Enable debug mode
--dry-run: Check only, do not actually update
--limit: Limit the number of records to process
--workers: Number of concurrent metadata requests (default: 4)
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
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
import sqlite3
import sys
import threading
import time
from pathlib import Path
from urllib.parse import urlparse

import yt_dlp


class YdlLogger:
    """Keep concurrent yt-dlp output readable; errors are reported by the caller."""

    def __init__(self, debug=False):
        self.debug_enabled = debug

    def debug(self, message):
        if self.debug_enabled:
            print(message)

    def warning(self, message):
        if self.debug_enabled:
            print(f"WARNING: {message}")

    def error(self, _message):
        pass


_ydl_local = threading.local()


def build_ydl_options(debug=False, browser_cookies=None, cookies_file=None):
    """Build yt-dlp options shared by all worker-local instances."""
    options = {
        "quiet": not debug,
        "skip_download": True,
        "extract_flat": False,
        "no_playlist": True,
        "socket_timeout": 10,
        "no_warnings": not debug,
        "logger": YdlLogger(debug),
        # Retry the complete URL once in fetch_job instead of retrying each
        # internal yt-dlp request several times.
        "retries": 0,
        "extractor_retries": 0,
    }

    if cookies_file:
        options["cookiefile"] = cookies_file
    elif browser_cookies:
        if "+" in browser_cookies and ":" in browser_cookies:
            browser, remainder = browser_cookies.split("+", 1)
            if "::" in remainder:
                keyring_profile, container = remainder.split("::", 1)
                if ":" in keyring_profile:
                    keyring, profile = keyring_profile.split(":", 1)
                    options["cookiesfrombrowser"] = (browser, keyring, profile, container)
                else:
                    options["cookiesfrombrowser"] = (browser, keyring_profile, None, container)
            elif ":" in remainder:
                keyring, profile = remainder.split(":", 1)
                options["cookiesfrombrowser"] = (browser, keyring, profile)
            else:
                options["cookiesfrombrowser"] = (browser, remainder)
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


def get_worker_ydl(debug=False, browser_cookies=None, cookies_file=None):
    """Reuse one isolated YoutubeDL instance in each worker thread."""
    key = (debug, browser_cookies, cookies_file)
    if getattr(_ydl_local, "key", None) != key:
        _ydl_local.ydl = yt_dlp.YoutubeDL(
            build_ydl_options(debug, browser_cookies, cookies_file)
        )
        _ydl_local.key = key
    return _ydl_local.ydl


def create_connection(db_path):
    """Create database connection"""
    try:
        conn = sqlite3.connect(db_path)
        return conn
    except sqlite3.Error as e:
        print(f"Database connection error: {e}")
        return None


def get_video_metadata(url, debug=False, browser_cookies=None, cookies_file=None):
    """Get a video thumbnail and duration in seconds from a URL."""
    if not url or url.strip() == "" or url == "未转载":
        return None, None

    try:
        ydl = get_worker_ydl(debug, browser_cookies, cookies_file)
        info = ydl.extract_info(url, download=False)

        # If it's a playlist, get info from first video
        if "entries" in info and info["entries"]:
            info = info["entries"][0]

        thumbnail = info.get("thumbnail")
        if not thumbnail and "thumbnails" in info:
            thumbnails = info["thumbnails"]
            if thumbnails:
                thumbnails.sort(key=lambda x: x.get("preference", 0), reverse=True)
                thumbnail = thumbnails[0].get("url")

        if thumbnail and "hdslb.com" in thumbnail and thumbnail.startswith("http://"):
            thumbnail = thumbnail.replace("http://", "https://")

        raw_duration = info.get("duration")
        duration = None
        if isinstance(raw_duration, (int, float)) and raw_duration >= 0:
            duration = round(raw_duration)

        return thumbnail, duration

    except Exception as e:
        if debug:
            print(f"Failed to get video metadata {url}: {e}")
        raise e


def is_non_video_url(url):
    """Return True for known database entries that cannot have video metadata."""
    host = urlparse(url).netloc.lower()
    return host == "manga.nicovideo.jp"


def is_retryable_error(error):
    """Retry transient transport failures, not permanent access/content failures."""
    message = str(error).lower()
    permanent_markers = (
        "sign in to confirm your age",
        "video unavailable",
        "not available from your location",
        "geo restriction",
        "unsupported url",
        "keyerror('bvid')",
        "http error 412",
        "precondition failed",
        "private video",
        "this video has been removed",
    )
    return not any(marker in message for marker in permanent_markers)


def update_thumbnails(
    conn,
    debug=False,
    dry_run=False,
    limit=None,
    update_original=True,
    update_repost=True,
    force=False,
    browser_cookies=None,
    cookies_file=None,
    workers=4,
    metadata_fetcher=get_video_metadata,
):
    """Update missing video thumbnails and durations."""
    cursor = conn.cursor()

    # Build query conditions
    conditions = []
    if update_original and not force:
        conditions.append(
            "(original_url IS NOT NULL AND original_url != '' AND original_url != '未转载' AND "
            "(original_thumbnail IS NULL OR original_thumbnail = '' OR original_duration IS NULL))"
        )
    elif update_original and force:
        conditions.append(
            "(original_url IS NOT NULL AND original_url != '' AND original_url != '未转载')"
        )

    if update_repost and not force:
        conditions.append(
            "(repost_url IS NOT NULL AND repost_url != '' AND repost_url != '未转载' AND "
            "(repost_thumbnail IS NULL OR repost_thumbnail = '' OR repost_duration IS NULL))"
        )
    elif update_repost and force:
        conditions.append(
            "(repost_url IS NOT NULL AND repost_url != '' AND repost_url != '未转载')"
        )

    if not conditions:
        print("❌ No video type specified for update")
        return {"processed": 0, "updated": 0, "errors": 0}

    delete_keywords = [
        "已删除",
        "删除",
        "已隐藏",
        "隐藏",
        "已失效",
        "失效",
        "已注销",
        "注销",
        "非公开",
        "地域限制",
        "区域限制",
        "版权限制",
        "专享",
        "私享",
        "无法播放",
        "无补档",
    ]

    where_clause = " OR ".join(conditions)
    query = (
        "SELECT id, original_url, original_thumbnail, original_duration, "
        "repost_url, repost_thumbnail, repost_duration, comment "
        f"FROM videos WHERE {where_clause} ORDER BY id"
    )

    if limit:
        query += " LIMIT ?"
        cursor.execute(query, (limit,))
    else:
        cursor.execute(query)
    videos = cursor.fetchall()

    print(f"Found {len(videos)} videos to process")

    stats = {
        "processed": 0,
        "updated": 0,
        "errors": 0,
        "original_updated": 0,
        "repost_updated": 0,
        "original_duration_updated": 0,
        "repost_duration_updated": 0,
        "unique_urls": 0,
        "retries": 0,
        "skipped_non_video": 0,
        "original_url_tasks": 0,
        "repost_url_tasks": 0,
    }

    url_jobs = {}
    for video in videos:
        (
            video_id,
            original_url,
            original_thumbnail,
            original_duration,
            repost_url,
            repost_thumbnail,
            repost_duration,
            comment,
        ) = video
        stats["processed"] += 1
        skip_original = comment and any(kw in comment for kw in delete_keywords)

        if (
            update_original
            and original_url
            and original_url != "未转载"
            and (force or not original_thumbnail or original_duration is None)
            and not skip_original
        ):
            clean_url = original_url.strip()
            if is_non_video_url(clean_url):
                stats["skipped_non_video"] += 1
            else:
                url_jobs.setdefault(clean_url, []).append(
                    (video_id, "original", original_thumbnail, original_duration)
                )
                stats["original_url_tasks"] += 1
        if (
            update_repost
            and repost_url
            and repost_url != "未转载"
            and (force or not repost_thumbnail or repost_duration is None)
        ):
            url_jobs.setdefault(repost_url.strip(), []).append(
                (video_id, "repost", repost_thumbnail, repost_duration)
            )
            stats["repost_url_tasks"] += 1

    stats["unique_urls"] = len(url_jobs)
    total_references = stats["original_url_tasks"] + stats["repost_url_tasks"]
    print(
        f"Prepared {total_references} URL references "
        f"({stats['original_url_tasks']} original, {stats['repost_url_tasks']} repost)"
    )
    print(
        f"Fetching {len(url_jobs)} unique URLs with {workers} workers "
        f"({total_references - len(url_jobs)} duplicate references reused)"
    )

    def fetch_job(url):
        for attempt in range(2):
            try:
                thumbnail, duration = metadata_fetcher(
                    url, debug, browser_cookies, cookies_file
                )
                return thumbnail, duration, attempt, None
            except Exception as error:
                if attempt == 0 and is_retryable_error(error):
                    time.sleep(1)
                else:
                    return None, None, attempt, error

    updated_video_ids = set()
    pending_writes = 0
    executor = ThreadPoolExecutor(max_workers=workers)
    futures = {executor.submit(fetch_job, url): url for url in url_jobs}
    interrupted = False

    try:
        for completed_urls, future in enumerate(as_completed(futures), 1):
            url = futures[future]
            thumbnail, duration, retry_count, error = future.result()
            stats["retries"] += retry_count
            print(f"\n[{completed_urls}/{len(url_jobs)}] {url}")

            if error is not None:
                stats["errors"] += 1
                print(f"  ❌ Metadata failed: {error}")
                continue
            if retry_count:
                print("  ✅ Retry succeeded")

            updates_by_video = {}
            for video_id, side, old_thumbnail, old_duration in url_jobs[url]:
                fields = updates_by_video.setdefault(video_id, {})
                if thumbnail and (force or not old_thumbnail):
                    fields[f"{side}_thumbnail"] = thumbnail
                    stats[f"{side}_updated"] += 1
                if duration is not None and (force or old_duration is None):
                    fields[f"{side}_duration"] = duration
                    stats[f"{side}_duration_updated"] += 1

            for video_id, fields in updates_by_video.items():
                if not fields:
                    continue
                assignments = ", ".join(f"{field} = ?" for field in fields)
                values = list(fields.values())
                update_details = ", ".join(
                    f"{field}={value}s" if field.endswith("_duration") else f"{field}={value}"
                    for field, value in fields.items()
                )
                if dry_run:
                    print(f"  [DRY RUN] Video {video_id}: {update_details}")
                else:
                    cursor.execute(
                        f"UPDATE videos SET {assignments} WHERE id = ?",
                        (*values, video_id),
                    )
                    pending_writes += 1
                    if pending_writes >= 50:
                        conn.commit()
                        pending_writes = 0
                    print(f"  💾 Video {video_id} updated: {update_details}")
                updated_video_ids.add(video_id)
    except KeyboardInterrupt:
        interrupted = True
        print("\nInterrupted; cancelling pending metadata requests...")
        for future in futures:
            future.cancel()
        raise
    finally:
        executor.shutdown(wait=not interrupted, cancel_futures=True)
        if pending_writes and not dry_run:
            conn.commit()

    stats["updated"] = len(updated_video_ids)

    return stats


def fix_existing_http_thumbnails(conn, debug=False, dry_run=False):
    """Fix existing http thumbnail links in database, change them to https"""
    cursor = conn.cursor()

    # Find all thumbnail records containing http://i2.hdslb.com
    cursor.execute(
        """
        SELECT id, original_thumbnail, repost_thumbnail 
        FROM videos 
        WHERE (original_thumbnail LIKE 'http://i%.hdslb.com%' OR 
               repost_thumbnail LIKE 'http://i%.hdslb.com%')
    """
    )

    videos = cursor.fetchall()

    if not videos:
        print("No http thumbnail links found that need fixing")
        return {"processed": 0, "updated": 0}

    print(f"Found {len(videos)} videos with http links that need fixing")

    stats = {"processed": 0, "updated": 0}

    for video in videos:
        video_id, original_thumbnail, repost_thumbnail = video
        stats["processed"] += 1

        updated_fields = []
        update_params = []

        # Check and update original video thumbnail
        if (
            original_thumbnail
            and original_thumbnail.startswith("http://")
            and "hdslb.com" in original_thumbnail
        ):
            new_original_thumbnail = original_thumbnail.replace("http://", "https://")
            updated_fields.append("original_thumbnail = ?")
            update_params.append(new_original_thumbnail)
            if debug:
                print(
                    f"Video ID {video_id}: Original video thumbnail {original_thumbnail} -> {new_original_thumbnail}"
                )

        # Check and update repost video thumbnail
        if (
            repost_thumbnail
            and repost_thumbnail.startswith("http://")
            and "hdslb.com" in repost_thumbnail
        ):
            new_repost_thumbnail = repost_thumbnail.replace("http://", "https://")
            updated_fields.append("repost_thumbnail = ?")
            update_params.append(new_repost_thumbnail)
            if debug:
                print(
                    f"Video ID {video_id}: Repost video thumbnail {repost_thumbnail} -> {new_repost_thumbnail}"
                )

        # Update database
        if updated_fields:
            if not dry_run:
                try:
                    update_params.append(video_id)
                    update_query = (
                        f"UPDATE videos SET {', '.join(updated_fields)} WHERE id = ?"
                    )
                    cursor.execute(update_query, update_params)
                    conn.commit()
                    stats["updated"] += 1
                    if debug:
                        print(f"  ✅ Video ID {video_id} updated")
                except Exception as e:
                    print(f"  ❌ Video ID {video_id} update failed: {e}")
            else:
                print(
                    f"[DRY RUN] Video ID {video_id}: Will update {', '.join(updated_fields)}"
                )
                stats["updated"] += 1

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
        return {"processed": 0, "updated": 0}

    print(f"Found {len(records)} records need HTTP to HTTPS conversion")

    updated_count = 0

    for record in records:
        video_id, original_thumbnail, repost_thumbnail = record
        updated = False

        # Convert original_thumbnail
        if (
            original_thumbnail
            and original_thumbnail.startswith("http://")
            and "hdslb.com" in original_thumbnail
        ):
            new_original = original_thumbnail.replace("http://", "https://")
            if debug:
                print(
                    f"Video {video_id}: Original video thumbnail {original_thumbnail} -> {new_original}"
                )

            if not dry_run:
                cursor.execute(
                    "UPDATE videos SET original_thumbnail = ? WHERE id = ?",
                    (new_original, video_id),
                )
            updated = True

        # Convert repost_thumbnail
        if (
            repost_thumbnail
            and repost_thumbnail.startswith("http://")
            and "hdslb.com" in repost_thumbnail
        ):
            new_repost = repost_thumbnail.replace("http://", "https://")
            if debug:
                print(
                    f"Video {video_id}: Repost video thumbnail {repost_thumbnail} -> {new_repost}"
                )

            if not dry_run:
                cursor.execute(
                    "UPDATE videos SET repost_thumbnail = ? WHERE id = ?",
                    (new_repost, video_id),
                )
            updated = True

        if updated:
            updated_count += 1

    if not dry_run:
        conn.commit()
        print(f"✅ Successfully updated {updated_count} records' thumbnail links")
    else:
        print(f"🔍 [Preview mode] Will update {updated_count} records' thumbnail links")

    return {"processed": len(records), "updated": updated_count}


def main():
    _default_db = str(
        Path(os.environ.get("PROJECT_ROOT", str(Path(__file__).parent.parent.parent)))
        / "backend"
        / "random-2hu-stuff.db"
    )
    parser = argparse.ArgumentParser(
        description="Update video thumbnails and durations in database"
    )
    parser.add_argument("--db-path", default=_default_db, help="Database path")
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode, show detailed information",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Check only, do not actually update database",
    )
    parser.add_argument(
        "--limit", type=int, help="Limit the number of records to process"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Number of concurrent metadata requests (default: 4)",
    )
    parser.add_argument(
        "--update-original",
        action="store_true",
        default=True,
        help="Update original video metadata (enabled by default)",
    )
    parser.add_argument(
        "--no-update-original",
        dest="update_original",
        action="store_false",
        help="Do not update original video metadata",
    )
    parser.add_argument(
        "--update-repost",
        action="store_true",
        default=True,
        help="Update repost video metadata (enabled by default)",
    )
    parser.add_argument(
        "--no-update-repost",
        dest="update_repost",
        action="store_false",
        help="Do not update repost video metadata",
    )
    parser.add_argument(
        "--force", action="store_true", help="Force update existing metadata"
    )
    parser.add_argument(
        "--cookies-from-browser",
        type=str,
        help="Extract cookies from specified browser to handle restricted videos. "
        "Supported browsers: brave, chrome, chromium, edge, firefox, opera, safari, vivaldi, whale. "
        "Format: BROWSER[+KEYRING][:PROFILE][::CONTAINER]. "
        'For keyring list on your system: python3 -c "import keyring.util.platform_; print(keyring.util.platform_.data_root())". '
        "Note: qutebrowser is not directly supported, use --cookies with qutebrowser cookie file instead.",
    )
    parser.add_argument(
        "--cookies",
        type=str,
        help="Netscape formatted file to read cookies from and dump cookie jar in",
    )
    parser.add_argument(
        "--fix-http-links",
        action="store_true",
        help="Fix existing http thumbnail links in database, change them to https",
    )

    args = parser.parse_args()

    if args.workers < 1:
        parser.error("--workers must be at least 1")

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
        print(f"Starting video metadata update")
        print(f"Database: {args.db_path}")

        if args.dry_run:
            print("*** DRY RUN mode - Database will not be actually modified ***")
        if args.force:
            print("*** Force mode - Will update existing metadata ***")
        if args.cookies_from_browser:
            print(f"*** Using {args.cookies_from_browser} browser cookies ***")
        if args.cookies:
            print(f"*** Using cookies from file: {args.cookies} ***")
        if args.limit:
            print(f"*** Limiting to {args.limit} records ***")
        print(f"*** Concurrent workers: {args.workers} ***")

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
            cookies_file=args.cookies,
            workers=args.workers,
        )

        # Print statistics
        print(f"\n=== 📊 Processing Complete ===")
        print(f"Records processed: {stats['processed']}")
        print(f"Records updated: {stats['updated']}")
        print(f"Original URL references: {stats['original_url_tasks']}")
        print(f"Repost URL references: {stats['repost_url_tasks']}")
        print(f"Unique URLs requested: {stats['unique_urls']}")
        print(f"Requests retried: {stats['retries']}")
        print(f"Non-video URLs skipped: {stats['skipped_non_video']}")
        print(f"Original video thumbnails updated: {stats['original_updated']}")
        print(f"Repost video thumbnails updated: {stats['repost_updated']}")
        print(
            f"Original video durations updated: {stats['original_duration_updated']}"
        )
        print(f"Repost video durations updated: {stats['repost_duration_updated']}")
        print(f"Errors: {stats['errors']}")

    except KeyboardInterrupt:
        print("Stopped by user. Completed database updates have been saved.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
