"""Extract and normalize author profile links, without crawling external sites."""

import html
from datetime import datetime
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sqlite3
from urllib.parse import parse_qs, unquote, urljoin, urlsplit

import requests


FIELDS = ("yt_url", "nico_url", "twitter_url")
HEADERS = {"User-Agent": "Mozilla/5.0"}


def backup_database(conn):
    path = next((row[2] for row in conn.execute("PRAGMA database_list")
                 if row[1] == "main"), "")
    if not path:
        raise ValueError("A file-backed database is required for backup")
    path = Path(path)
    backup = path.with_name(path.name + ".backup-" + datetime.now().strftime("%Y%m%d-%H%M%S-%f"))
    with backup.open("xb"):
        pass
    target = sqlite3.connect(backup)
    try:
        conn.backup(target)
        if list(target.execute("PRAGMA integrity_check")) != [("ok",)]:
            raise ValueError("Backup integrity check failed")
    finally:
        target.close()
    print(f"Backup: {backup}")
    return backup


def blank(value):
    return value is None or not value.strip()


def normalize_profile_url(value):
    """Return (database column, canonical URL), or None for non-profile URLs."""
    value = html.unescape(value).strip().rstrip(".,;:!?。、、）)]}〉》\"'")
    if value.startswith("//"):
        value = "https:" + value
    elif re.match(r"(?:www\.|m\.|mobile\.)?(?:youtube\.com|nicovideo\.jp|twitter\.com|x\.com)/", value, re.I):
        value = "https://" + value
    try:
        parsed = urlsplit(value)
        if parsed.scheme not in ("http", "https") or parsed.username or parsed.password:
            return None
        if parsed.port not in (None, 80, 443):
            return None
        host = (parsed.hostname or "").lower()
    except ValueError:
        return None
    path = parsed.path.rstrip("/")
    if host in ("youtube.com", "www.youtube.com", "m.youtube.com"):
        parts = path.split("/")[1:]
        if parts and parts[-1] in ("videos", "shorts", "streams", "featured", "about", "playlists", "community"):
            parts.pop()
        if len(parts) == 1 and re.fullmatch(r"@[^/\s?#]+", parts[0]):
            if re.search(r"[/\s?#]", unquote(parts[0][1:])):
                return None
        elif len(parts) == 2 and parts[0] in ("channel", "user", "c"):
            pattern = r"UC[A-Za-z0-9_-]{22}" if parts[0] == "channel" else r"[A-Za-z0-9_.-]+"
            if not re.fullmatch(pattern, parts[1]):
                return None
        else:
            return None
        return "yt_url", "https://www.youtube.com/" + "/".join(parts)
    if host in ("nicovideo.jp", "www.nicovideo.jp", "sp.nicovideo.jp"):
        match = re.fullmatch(r"/user/(\d+)(?:/(?:video|videos|mylist|profile))?", path)
        if match:
            return "nico_url", f"https://www.nicovideo.jp/user/{int(match[1])}"
    if host in ("twitter.com", "www.twitter.com", "mobile.twitter.com", "x.com", "www.x.com", "mobile.x.com"):
        match = re.fullmatch(r"/([A-Za-z0-9_]{1,15})", path)
        if match and match[1].lower() not in {
            "i", "intent", "search", "share", "home", "explore", "settings",
            "login", "logout", "signup", "messages", "notifications", "tos", "privacy",
        }:
            return "twitter_url", "https://x.com/" + match[1]
    return None


def unwrap_url(value):
    value = html.unescape(value)
    for _ in range(3):
        parsed = urlsplit(value)
        if parsed.hostname not in ("www.youtube.com", "youtube.com") or parsed.path != "/redirect":
            break
        query = parse_qs(parsed.query)
        target = (query.get("q") or query.get("url") or [None])[0]
        if not target:
            break
        value = target
    if urlsplit(value).hostname == "t.co":
        for _ in range(5):
            response = requests.get(value, headers=HEADERS, timeout=10, allow_redirects=False)
            if response.status_code not in (301, 302, 303, 307, 308):
                response.raise_for_status()
                break
            target = response.headers.get("Location")
            if not target:
                break
            value = urljoin(value, target)
            if urlsplit(value).hostname != "t.co":
                break
    return value


def text_urls(text):
    return re.findall(r"(?:https?://|//|(?:www\.)?(?:youtube\.com|nicovideo\.jp|twitter\.com|x\.com)/)[^\s<>\"']+", html.unescape(text))


class ProfileHTML(HTMLParser):
    """Capture structured profile data; never scan all page navigation links."""

    def __init__(self):
        super().__init__()
        self.meta = []
        self.states = []
        self.script = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "meta" and (attrs.get("name") == "description" or attrs.get("property") == "og:description"):
            self.meta.append(attrs.get("content", ""))
        if tag == "script" and attrs.get("id") == "__NEXT_DATA__":
            self.script = ""
        # Older NicoNico user pages expose the profile in this JSON attribute.
        if attrs.get("id") == "js-initial-userpage-data" and attrs.get("data-initial-data"):
            self.states.append(json.loads(attrs["data-initial-data"]))

    def handle_data(self, data):
        if self.script is not None:
            self.script += data

    def handle_endtag(self, tag):
        if tag == "script" and self.script is not None:
            self.states.append(json.loads(self.script))
            self.script = None


def walk(node):
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from walk(value)
    elif isinstance(node, list):
        for value in node:
            yield from walk(value)


def profile_page_urls(page, platform):
    parser = ProfileHTML()
    parser.feed(page)
    urls = [url for text in parser.meta for url in text_urls(text)]
    if platform == "yt_url":
        match = re.search(r"(?:var\s+)?ytInitialData\s*=\s*", page)
        if match:
            state, _ = json.JSONDecoder().raw_decode(page[match.end():])
            parser.states.append(state)
        profile_keys = {"channelMetadataRenderer", "channelAboutFullMetadataRenderer", "aboutChannelViewModel", "channelExternalLinkViewModel"}
        sections = [value for state in parser.states for node in walk(state)
                    for key, value in node.items() if key in profile_keys]
    else:
        # Only inspect the owner's profile, excluding recommended users/videos.
        sections = []
        for state in parser.states:
            for path in (("user",), ("userDetails",), ("data", "user"),
                         ("props", "pageProps", "user"),
                         ("props", "pageProps", "userDetails"),
                         ("props", "pageProps", "initialState", "user")):
                section = state
                for key in path:
                    section = section.get(key) if isinstance(section, dict) else None
                if isinstance(section, dict):
                    sections.append(section)
    for section in sections:
        for node in walk(section):
            for key, value in node.items():
                if isinstance(value, str) and key in {
                    "description", "descriptionText", "content", "text", "url", "href",
                    "link", "value", "youtube", "twitter", "website",
                }:
                    urls.extend(text_urls(value))
    if not parser.meta and not sections:
        raise ValueError("No supported profile description/link section found")
    return urls


def fetch_profile_urls(url, twitter_request):
    normalized = normalize_profile_url(url)
    if not normalized:
        raise ValueError("Unsupported author profile URL")
    platform, canonical = normalized
    if platform == "twitter_url":
        data = twitter_request(canonical.rsplit("/", 1)[1])
        user = (data or {}).get("user")
        if not isinstance(user, dict):
            raise ValueError("Twitter profile request failed")
        urls = text_urls(user.get("description") or "")
        for key in ("website", "url"):
            value = user.get(key)
            if isinstance(value, str):
                urls.extend(text_urls(value))
            elif isinstance(value, dict):
                for field in ("expanded_url", "url"):
                    if isinstance(value.get(field), str):
                        urls.extend(text_urls(value[field]))
        for node in walk(user.get("entities", {})):
            if isinstance(node.get("expanded_url"), str):
                urls.append(node["expanded_url"])
        return urls
    if platform == "yt_url":
        canonical += "/about"
    response = requests.get(canonical, headers=HEADERS, timeout=15)
    response.raise_for_status()
    return profile_page_urls(response.text, platform)


def discover_links(existing, twitter_request):
    candidates = {field: {} for field in FIELDS}
    failures = 0
    resolved = {}
    for source in existing.values():
        if blank(source):
            continue
        try:
            urls = fetch_profile_urls(source, twitter_request)
        except Exception as exc:
            failures += 1
            print(f"  Link source failed: {source}: {exc}")
            continue
        for raw in urls:
            try:
                if raw not in resolved:
                    resolved[raw] = normalize_profile_url(unwrap_url(raw))
                normalized = resolved[raw]
                if normalized:
                    field, url = normalized
                    if blank(existing[field]):
                        key = url.lower() if field == "twitter_url" else url
                        entry = candidates[field].setdefault(key, [url, set()])
                        entry[1].add(source)
            except Exception as exc:
                failures += 1
                print(f"  Link resolution failed: {raw}: {exc}")
    found = {}
    conflicts = 0
    for field, entries in candidates.items():
        if len(entries) > 1:
            conflicts += 1
            print(f"  Conflicting {field}, skipped:")
        for url, sources in entries.values():
            print(f"  {field}: {url} (from {', '.join(sorted(sources))})")
            if len(entries) == 1:
                found[field] = url
    return found, conflicts, failures
