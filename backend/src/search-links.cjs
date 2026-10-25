// Local identity matching only: never follows redirects or calls platform APIs.
// AV/BV arithmetic: https://github.com/1422384664/bilibili-API-collect-2026/blob/main/docs/misc/bvid_desc.md
const BV_ALPHABET =
  "FcwAPNKTMug3GV5Lj7EJnHpWsx4tb8haYeviqBz6rkCy12mUSDQX9RdoZf";
const MAX_AID = 1n << 51n;
const XOR_CODE = 23442827791579n;

function encodeBv(aid) {
  const chars = Array.from("BV1000000000");
  let value = (MAX_AID | aid) ^ XOR_CODE;
  for (let i = 11; value > 0n; i--, value /= 58n)
    chars[i] = BV_ALPHABET[Number(value % 58n)];
  [chars[3], chars[9]] = [chars[9], chars[3]];
  [chars[4], chars[7]] = [chars[7], chars[4]];
  return chars.join("");
}

function bilibiliKey(value) {
  if (/^av\d+$/i.test(value)) {
    const aid = BigInt(value.slice(2));
    return aid > 0n && aid < MAX_AID ? `bili:${aid}` : null;
  }
  if (!/^bv1[A-Za-z0-9]{9}$/i.test(value)) return null;
  const canonical = "BV" + value.slice(2);
  const chars = Array.from(canonical);
  [chars[3], chars[9]] = [chars[9], chars[3]];
  [chars[4], chars[7]] = [chars[7], chars[4]];
  let value58 = 0n;
  for (const char of chars.slice(3)) {
    const digit = BV_ALPHABET.indexOf(char);
    if (digit < 0) return null;
    value58 = value58 * 58n + BigInt(digit);
  }
  const aid = (value58 & (MAX_AID - 1n)) ^ XOR_CODE;
  // Reject non-canonical/invalid codes rather than aliasing unrelated videos.
  return aid > 0n && aid < MAX_AID && encodeBv(aid) === canonical
    ? `bili:${aid}`
    : null;
}

function parseLink(value) {
  if (typeof value !== "string") return null;
  let input = value.trim();
  if (input.startsWith("//")) input = "https:" + input;
  else if (/^[\w.-]+\.[a-z]{2,}\//i.test(input)) input = "https://" + input;
  try {
    const url = new URL(input);
    return ["http:", "https:"].includes(url.protocol) &&
      !url.username &&
      !url.password &&
      (!url.port || ["80", "443"].includes(url.port))
      ? url
      : null;
  } catch {
    return null;
  }
}

function fallbackKey(url) {
  // Unknown URLs retain meaningful parameters; only common tracking is removed.
  const copy = new URL(url);
  copy.protocol = "https:";
  copy.port = "";
  copy.hash = "";
  copy.pathname = copy.pathname.replace(/\/+$/, "") || "/";
  for (const key of [...copy.searchParams.keys()])
    if (/^(utm_.+|spm_id_from|si|feature)$/i.test(key))
      copy.searchParams.delete(key);
  copy.searchParams.sort();
  return `url:${copy.href}`;
}

function videoKey(value) {
  if (typeof value !== "string") return null;
  const input = value.trim();
  if (/^(sm|nm|so)\d+$/i.test(input)) return `nico:${input.toLowerCase()}`;
  const bili = bilibiliKey(input);
  if (bili) return bili;
  const url = parseLink(input);
  if (!url) return null;
  const host = url.hostname.toLowerCase();
  const path = url.pathname.replace(/\/+$/, "");
  if (
    [
      "youtube.com",
      "www.youtube.com",
      "m.youtube.com",
      "music.youtube.com",
      "youtu.be",
      "www.youtu.be",
    ].includes(host)
  ) {
    const id = host.endsWith("youtu.be")
      ? path.match(/^\/([^/]+)$/)?.[1]
      : path === "/watch"
        ? url.searchParams.get("v")
        : path.match(/^\/(?:shorts|live|embed)\/([^/]+)$/)?.[1];
    if (id && /^[A-Za-z0-9_-]{11}$/.test(id)) return `youtube:${id}`;
  }
  if (
    ["nicovideo.jp", "www.nicovideo.jp", "sp.nicovideo.jp", "nico.ms"].includes(
      host,
    )
  ) {
    const id = path.match(
      host === "nico.ms"
        ? /^\/((?:sm|nm|so)\d+)$/i
        : /^\/watch\/((?:sm|nm|so)\d+)$/i,
    )?.[1];
    if (id) return `nico:${id.toLowerCase()}`;
  }
  if (["bilibili.com", "www.bilibili.com", "m.bilibili.com"].includes(host)) {
    const id = path.match(/^\/video\/([^/]+)$/)?.[1];
    const key = id && bilibiliKey(id);
    if (key) return key;
  }
  return fallbackKey(url);
}

function authorKey(value) {
  const url = parseLink(value);
  if (!url) return null;
  const host = url.hostname.toLowerCase();
  const path = url.pathname.replace(/\/+$/, "");
  if (["youtube.com", "www.youtube.com", "m.youtube.com"].includes(host)) {
    const profile = path.replace(
      /\/(videos|shorts|streams|featured|about|playlists|community)$/,
      "",
    );
    if (/^\/@[^/\s]+$/.test(profile)) {
      try {
        return `youtube-profile:${decodeURIComponent(profile).toLowerCase()}`;
      } catch {
        return fallbackKey(url);
      }
    }
    if (/^\/(channel|user|c)\/[^/\s]+$/.test(profile))
      return `youtube-profile:${profile}`;
  }
  if (["nicovideo.jp", "www.nicovideo.jp", "sp.nicovideo.jp"].includes(host)) {
    const id = path.match(
      /^\/user\/(\d+)(?:\/(?:video|videos|mylist|profile))?$/,
    )?.[1];
    if (id) return `nico-profile:${BigInt(id)}`;
  }
  if (
    [
      "twitter.com",
      "www.twitter.com",
      "mobile.twitter.com",
      "x.com",
      "www.x.com",
      "mobile.x.com",
    ].includes(host) &&
    /^\/[A-Za-z0-9_]{1,15}$/.test(path)
  )
    return `twitter-profile:${path.toLowerCase()}`;
  return fallbackKey(url);
}

function createLinkIndex(items, fields, keyOf) {
  const index = new Map();
  for (const item of items) {
    const keys = new Set(
      fields.map((field) => keyOf(item[field])).filter(Boolean),
    );
    for (const key of keys) {
      if (!index.has(key)) index.set(key, []);
      index.get(key).push(item);
    }
  }
  return index;
}

module.exports = { videoKey, authorKey, createLinkIndex };
