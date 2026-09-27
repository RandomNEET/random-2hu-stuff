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
--from-id: Process videos whose ID is at least this value
--to-id: Process videos whose ID is at most this value
--workers: Number of concurrent metadata requests (default: 4)
--state-file: Invalid-link state file path (default: scripts/state/metadata-updater.json)
--retry-invalid: Retry URLs previously recorded as invalid
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
from datetime import datetime, timezone
from http.cookiejar import MozillaCookieJar
import json
import os
import re
import sqlite3
import sys
import threading
import time
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import requests
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


def cache_prefetched_metadata(url, thumbnail, duration):
    """Keep validation metadata for the extraction step in the same worker."""
    if not hasattr(_ydl_local, "prefetched_metadata"):
        _ydl_local.prefetched_metadata = {}
    _ydl_local.prefetched_metadata[url] = (thumbnail, duration)


def mark_duration_unavailable(url):
    """Mark a URL whose provider explicitly has no usable duration."""
    if not hasattr(_ydl_local, "duration_unavailable_urls"):
        _ydl_local.duration_unavailable_urls = set()
    _ydl_local.duration_unavailable_urls.add(url)


def get_requests_cookies(cookies_file):
    """Load a Netscape cookie file once per worker for validation requests."""
    if not cookies_file:
        return None
    cache = getattr(_ydl_local, "request_cookie_jars", {})
    if cookies_file not in cache:
        jar = MozillaCookieJar(cookies_file)
        jar.load(ignore_discard=True, ignore_expires=True)
        cache[cookies_file] = jar
        _ydl_local.request_cookie_jars = cache
    return cache[cookies_file]


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

    prefetched = getattr(_ydl_local, "prefetched_metadata", {})
    if url in prefetched:
        return prefetched.pop(url)

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


BILIBILI_STATUS_MESSAGES = {
    62012: "稿件不存在或不可访问（具体原因未知）",
}


def validate_video_url(url, timeout=10, cookies_file=None):
    """Validate every URL before extraction; None means the result is inconclusive."""
    parsed = urlparse(url)
    host = parsed.netloc.lower().split(":", 1)[0]
    normalized_host = host.removeprefix("www.").removeprefix("m.")
    headers = {"User-Agent": "Mozilla/5.0 (metadata-updater/1.0)"}

    try:
        if normalized_host == "bilibili.com":
            bv_match = re.search(r"/video/(BV[a-zA-Z0-9]+)", parsed.path)
            av_match = re.search(r"/video/av(\d+)", parsed.path, re.IGNORECASE)
            if bv_match:
                params = {"bvid": bv_match.group(1)}
            elif av_match:
                params = {"aid": av_match.group(1)}
            else:
                return _validate_http_status(url, headers, timeout)
            response = requests.get(
                "https://api.bilibili.com/x/web-interface/view",
                params=params,
                headers=headers,
                cookies=get_requests_cookies(cookies_file),
                timeout=timeout,
            )
            response.raise_for_status()
            payload = response.json()
            code = payload.get("code")
            if code == 0:
                data = payload.get("data") or {}
                raw_duration = data.get("duration")
                duration = (
                    round(raw_duration)
                    if isinstance(raw_duration, (int, float)) and raw_duration >= 0
                    else None
                )
                thumbnail = data.get("pic")
                if thumbnail and thumbnail.startswith("http://"):
                    thumbnail = thumbnail.replace("http://", "https://", 1)
                cache_prefetched_metadata(url, thumbnail, duration)
                return True, ""
            # VideoCard.vue treats every non-zero result as unavailable. State
            # files need to be safer: persist content-status codes, but not
            # request blocking/authentication codes such as -352 or -412.
            if code == -404 or (
                isinstance(code, int) and 62000 <= code < 63000
            ):
                message = BILIBILI_STATUS_MESSAGES.get(
                    code, payload.get("message") or "video is unavailable"
                )
                return False, f"Bilibili API code {code}: {message}"
            return None, ""

        if normalized_host in {"x.com", "twitter.com"} or re.search(
            r"(?:x|twitter)\.com/[^/]+/status/\d+", url, re.IGNORECASE
        ):
            tweet_match = re.search(r"/status/(\d+)", url)
            if not tweet_match:
                return None, ""
            response = requests.get(
                f"https://api.fxtwitter.com/status/{tweet_match.group(1)}",
                headers=headers,
                timeout=timeout,
            )
            if response.status_code == 200:
                payload = response.json()
                tweet = payload.get("tweet")
                if not tweet:
                    return None, ""
                media = tweet.get("media") or {}
                videos = media.get("videos") or media.get("all") or []
                if videos:
                    video = videos[0]
                    raw_duration = video.get("duration")
                    duration = (
                        round(raw_duration)
                        if isinstance(raw_duration, (int, float))
                        and raw_duration > 0
                        else None
                    )
                    if raw_duration == 0:
                        mark_duration_unavailable(url)
                    cache_prefetched_metadata(
                        url, video.get("thumbnail_url"), duration
                    )
                return True, ""
            if response.status_code == 404:
                return False, "FxTwitter reports that the post does not exist"
            return None, ""

        if normalized_host in {"youtube.com", "youtu.be"}:
            video_id = (
                parsed.path.strip("/")
                if normalized_host == "youtu.be"
                else parse_qs(parsed.query).get("v", [""])[0]
            )
            if not video_id:
                return _validate_http_status(url, headers, timeout)
            watch_response = requests.get(
                "https://www.youtube.com/watch",
                params={"v": video_id},
                headers=headers,
                timeout=timeout,
            )
            if watch_response.status_code in {404, 410}:
                return False, f"YouTube returned HTTP {watch_response.status_code}"
            page = watch_response.text.lower()
            playability_match = re.search(
                r'"playabilitystatus":\{"status":"([^"]+)"'
                r'(?:,"reason":"([^"]*)")?',
                page,
            )
            if not playability_match:
                return None, ""
            status, reason = playability_match.groups()
            reason = reason or ""
            gone_markers = (
                "video unavailable",
                "video has been removed",
                "video is no longer available",
            )
            if status in {"error", "unplayable"} and any(
                marker in reason for marker in gone_markers
            ):
                return False, "YouTube reports that the video is unavailable"
            if status == "login_required" and reason == "private video":
                return False, "YouTube reports that the video is private"
            membership_markers = (
                "members-only",
                "channel's members",
                "channel members",
            )
            if status in {"login_required", "unplayable"} and any(
                marker in reason for marker in membership_markers
            ):
                return False, "YouTube reports that the video is members-only"
            if status == "ok":
                return True, ""
            return None, ""

        if normalized_host == "nicovideo.jp":
            video_match = re.search(r"/watch/([a-zA-Z0-9]+)", parsed.path)
            if not video_match:
                return _validate_http_status(url, headers, timeout)
            response = requests.get(
                f"https://ext.nicovideo.jp/api/getthumbinfo/{video_match.group(1)}",
                headers=headers,
                timeout=timeout,
            )
            if response.status_code in {404, 410}:
                return False, f"Niconico returned HTTP {response.status_code}"
            response.raise_for_status()
            body = response.text.upper()
            if 'STATUS="FAIL"' in body and re.search(
                r"<CODE>\s*(DELETED|NOT_FOUND|NOT_FOUND_OR_DELETED)\s*</CODE>",
                body,
            ):
                return False, "Niconico reports that the video was deleted"
            if 'STATUS="OK"' in body:
                return True, ""
            return None, ""

        return _validate_http_status(url, headers, timeout)
    except (OSError, requests.RequestException, ValueError):
        return None, ""


def _validate_http_status(url, headers, timeout):
    """Fallback validation for X, AcFun, and unknown providers."""
    response = requests.head(
        url,
        headers=headers,
        timeout=timeout,
        allow_redirects=True,
    )
    if response.status_code == 405:
        response = requests.get(
            url,
            headers=headers,
            timeout=timeout,
            allow_redirects=True,
            stream=True,
        )
    if response.status_code in {404, 410}:
        return False, f"URL returned HTTP {response.status_code}"
    if 200 <= response.status_code < 400:
        return True, ""
    return None, ""


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


def is_stateworthy_metadata_error(url, error):
    """Accept explicit access/content failures when preflight is blocked."""
    host = urlparse(url).netloc.lower().split(":", 1)[0]
    normalized_host = host.removeprefix("www.").removeprefix("m.")
    message = str(error).lower()
    if normalized_host in {"youtube.com", "youtu.be"}:
        return any(
            marker in message
            for marker in (
                "video unavailable",
                "private video",
                "members-only",
                "available to this channel's members",
            )
        )
    if normalized_host in {"x.com", "twitter.com"} or re.search(
        r"(?:x|twitter)\.com/[^/]+/status/\d+", url, re.IGNORECASE
    ):
        return any(
            marker in message
            for marker in (
                "protected tweet",
                "not authorized to view this protected tweet",
            )
        )
    return False


def load_invalid_state(state_file):
    """Load invalid URL records, tolerating absent or malformed state files."""
    if not state_file.exists():
        return {"version": 1, "invalid_urls": {}, "unavailable_duration_urls": {}}
    try:
        with state_file.open("r", encoding="utf-8") as handle:
            state = json.load(handle)
        if not isinstance(state, dict) or not isinstance(
            state.get("invalid_urls"), dict
        ):
            raise ValueError("invalid state structure")
        state["version"] = 1
        if not isinstance(state.get("unavailable_duration_urls", {}), dict):
            raise ValueError("invalid unavailable-duration state structure")
        state.setdefault("unavailable_duration_urls", {})
        return state
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"⚠️  Unable to read invalid-link state {state_file}: {error}")
        return {"version": 1, "invalid_urls": {}, "unavailable_duration_urls": {}}


def save_invalid_state(state_file, state):
    """Atomically persist invalid URL records."""
    state_file.parent.mkdir(parents=True, exist_ok=True)
    temporary_file = state_file.with_name(f"{state_file.name}.tmp")
    with temporary_file.open("w", encoding="utf-8") as handle:
        json.dump(state, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
    os.replace(temporary_file, state_file)


def update_thumbnails(
    conn,
    debug=False,
    dry_run=False,
    limit=None,
    from_id=None,
    to_id=None,
    update_original=True,
    update_repost=True,
    force=False,
    browser_cookies=None,
    cookies_file=None,
    workers=4,
    metadata_fetcher=get_video_metadata,
    url_validator=validate_video_url,
    invalid_state=None,
    state_file=None,
    retry_invalid=False,
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

    where_parts = [f"({' OR '.join(conditions)})"]
    query_params = []
    if from_id is not None:
        where_parts.append("id >= ?")
        query_params.append(from_id)
    if to_id is not None:
        where_parts.append("id <= ?")
        query_params.append(to_id)

    where_clause = " AND ".join(where_parts)
    query = (
        "SELECT id, original_url, original_thumbnail, original_duration, "
        "repost_url, repost_thumbnail, repost_duration "
        f"FROM videos WHERE {where_clause} ORDER BY id"
    )

    if limit is not None:
        query += " LIMIT ?"
        query_params.append(limit)
    cursor.execute(query, query_params)
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
        "skipped_invalid": 0,
        "skipped_unavailable_duration": 0,
        "new_invalid": 0,
        "new_unavailable_duration": 0,
        "state_write_errors": 0,
    }

    if invalid_state is None:
        invalid_state = {
            "version": 1,
            "invalid_urls": {},
            "unavailable_duration_urls": {},
        }
    invalid_urls = invalid_state["invalid_urls"]
    unavailable_duration_urls = invalid_state.setdefault(
        "unavailable_duration_urls", {}
    )
    url_jobs = {}

    def persist_invalid_state():
        if state_file is None or dry_run:
            return
        try:
            save_invalid_state(state_file, invalid_state)
        except OSError as error:
            stats["state_write_errors"] += 1
            print(f"  ⚠️  Unable to save invalid-link state: {error}")

    def add_url_job(url, reference):
        clean_url = url.strip()
        if is_non_video_url(clean_url):
            stats["skipped_non_video"] += 1
            return
        if clean_url in invalid_urls and not retry_invalid:
            stats["skipped_invalid"] += 1
            return
        _, _, old_thumbnail, old_duration = reference
        if (
            clean_url in unavailable_duration_urls
            and old_thumbnail
            and old_duration is None
            and not force
        ):
            stats["skipped_unavailable_duration"] += 1
            return
        url_jobs.setdefault(clean_url, []).append(reference)
        stats[f"{reference[1]}_url_tasks"] += 1

    for video in videos:
        (
            video_id,
            original_url,
            original_thumbnail,
            original_duration,
            repost_url,
            repost_thumbnail,
            repost_duration,
        ) = video
        stats["processed"] += 1
        original_needs_metadata = (
            update_original
            and original_url
            and original_url != "未转载"
            and (force or not original_thumbnail or original_duration is None)
        )
        if original_needs_metadata:
            add_url_job(
                original_url,
                (video_id, "original", original_thumbnail, original_duration),
            )
        if (
            update_repost
            and repost_url
            and repost_url != "未转载"
            and (force or not repost_thumbnail or repost_duration is None)
        ):
            add_url_job(
                repost_url,
                (video_id, "repost", repost_thumbnail, repost_duration),
            )

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
        if url_validator is validate_video_url:
            valid, invalid_reason = url_validator(
                url, cookies_file=cookies_file
            )
        else:
            valid, invalid_reason = url_validator(url)
        if valid is False:
            return None, None, 0, None, invalid_reason, False
        for attempt in range(2):
            try:
                thumbnail, duration = metadata_fetcher(
                    url, debug, browser_cookies, cookies_file
                )
                unavailable_set = getattr(
                    _ydl_local, "duration_unavailable_urls", set()
                )
                duration_unavailable = url in unavailable_set
                unavailable_set.discard(url)
                return (
                    thumbnail,
                    duration,
                    attempt,
                    None,
                    None,
                    duration_unavailable,
                )
            except Exception as error:
                if attempt == 0 and is_retryable_error(error):
                    time.sleep(1)
                else:
                    return None, None, attempt, error, None, False

    updated_video_ids = set()
    pending_writes = 0
    executor = ThreadPoolExecutor(max_workers=workers)
    futures = {executor.submit(fetch_job, url): url for url in url_jobs}
    interrupted = False

    try:
        for completed_urls, future in enumerate(as_completed(futures), 1):
            url = futures[future]
            (
                thumbnail,
                duration,
                retry_count,
                error,
                invalid_reason,
                duration_unavailable,
            ) = future.result()
            stats["retries"] += retry_count
            print(f"\n[{completed_urls}/{len(url_jobs)}] {url}")

            if invalid_reason is not None:
                invalid_urls[url] = {
                    "reason": invalid_reason,
                    "recorded_at": datetime.now(timezone.utc).isoformat(),
                }
                stats["new_invalid"] += 1
                print(f"  🗃️  Link validation failed: {invalid_reason}")
                persist_invalid_state()
                continue

            if error is not None:
                stats["errors"] += 1
                print(f"  ❌ Metadata failed: {error}")
                if is_stateworthy_metadata_error(url, error):
                    invalid_urls[url] = {
                        "reason": str(error)[:500],
                        "recorded_at": datetime.now(timezone.utc).isoformat(),
                    }
                    stats["new_invalid"] += 1
                    print("  🗃️  Recorded from explicit availability error")
                    persist_invalid_state()
                continue
            if retry_count:
                print("  ✅ Retry succeeded")
            if retry_invalid and url in invalid_urls:
                del invalid_urls[url]
                persist_invalid_state()
            if duration_unavailable:
                unavailable_duration_urls[url] = {
                    "reason": "Provider reports no usable duration",
                    "recorded_at": datetime.now(timezone.utc).isoformat(),
                }
                stats["new_unavailable_duration"] += 1
                print("  ⏭️  Duration unavailable; future duration checks skipped")
                persist_invalid_state()

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
        "--from-id",
        type=int,
        help="Only process videos whose ID is greater than or equal to this value",
    )
    parser.add_argument(
        "--to-id",
        type=int,
        help="Only process videos whose ID is less than or equal to this value",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Number of concurrent metadata requests (default: 4)",
    )
    parser.add_argument(
        "--state-file",
        type=str,
        help="Invalid-link state file (default: scripts/state/metadata-updater.json)",
    )
    parser.add_argument(
        "--retry-invalid",
        action="store_true",
        help="Retry URLs recorded as invalid and remove them if they succeed",
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
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be at least 1")
    if args.from_id is not None and args.from_id < 1:
        parser.error("--from-id must be at least 1")
    if args.to_id is not None and args.to_id < 1:
        parser.error("--to-id must be at least 1")
    if (
        args.from_id is not None
        and args.to_id is not None
        and args.from_id > args.to_id
    ):
        parser.error("--from-id cannot be greater than --to-id")

    # Check if database file exists
    if not os.path.exists(args.db_path):
        print(f"Error: Database file does not exist: {args.db_path}")
        sys.exit(1)

    state_file = (
        Path(args.state_file).expanduser()
        if args.state_file
        else Path(__file__).parent / "state" / "metadata-updater.json"
    )
    invalid_state = load_invalid_state(state_file)

    # Connect to database
    conn = create_connection(args.db_path)
    if not conn:
        print("Unable to connect to database")
        sys.exit(1)

    try:
        print(f"Starting video metadata update")
        print(f"Database: {args.db_path}")
        print(f"Invalid-link state: {state_file}")
        print(f"Known invalid URLs: {len(invalid_state['invalid_urls'])}")
        print(
            "Known unavailable durations: "
            f"{len(invalid_state['unavailable_duration_urls'])}"
        )

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
        if args.from_id is not None or args.to_id is not None:
            range_start = args.from_id if args.from_id is not None else "first"
            range_end = args.to_id if args.to_id is not None else "last"
            print(f"*** Video ID range: {range_start}–{range_end} ***")
        if args.retry_invalid:
            print("*** Retrying URLs previously recorded as invalid ***")
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
            from_id=args.from_id,
            to_id=args.to_id,
            update_original=args.update_original,
            update_repost=args.update_repost,
            force=args.force,
            browser_cookies=args.cookies_from_browser,
            cookies_file=args.cookies,
            workers=args.workers,
            invalid_state=invalid_state,
            state_file=state_file,
            retry_invalid=args.retry_invalid,
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
        print(f"Known invalid URLs skipped: {stats['skipped_invalid']}")
        print(
            "Known unavailable durations skipped: "
            f"{stats['skipped_unavailable_duration']}"
        )
        print(f"New invalid URLs recorded: {stats['new_invalid']}")
        print(
            "New unavailable durations recorded: "
            f"{stats['new_unavailable_duration']}"
        )
        print(f"State write errors: {stats['state_write_errors']}")
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
