// Independent known AV/BV pairs, including a 15-digit AV number.
// Large pair: bilibili-API-collect docs/misc/bvid_desc.md example.
const biliPairs = [
  ["170001", "BV17x411w7KC"],
  ["455017605", "BV1Q541167Qg"],
  ["111298867365120", "BV1L9Uoa9EUx"],
];
const nicoIds = ["sm33678186", "sm9", "sm12345678"];
const authors = [
  {
    id: 1,
    yt_name: "频道甲",
    yt_url: "https://www.youtube.com/@Creator",
    nico_url: "https://www.nicovideo.jp/user/123",
    twitter_url: "https://twitter.com/Creator",
    worksCount: 10,
  },
  {
    id: 2,
    yt_name: "频道乙",
    yt_url: "https://www.youtube.com/channel/UCabcdefghijklmnopqrstuv",
    nico_url: null,
    twitter_url: "",
    worksCount: 0,
  },
];
const videos = [
  ...nicoIds.map((id, i) => ({
    id: i + 1,
    original_url: `https://www.nicovideo.jp/watch/${id}`,
  })),
  ...biliPairs.map(([av, bv], i) => ({
    id: i + 4,
    repost_url: `https://www.bilibili.com/video/${bv}`,
  })),
  { id: 7, original_url: "https://www.youtube.com/watch?v=dQw4w9WgXcQ" },
  {
    id: 8,
    original_url: "https://www.bilibili.com/video/av170001",
    repost_url: "https://www.bilibili.com/video/BV17x411w7KC",
  },
  { id: 9, original_url: null, repost_url: "" },
  { id: 10, original_url: "https://example.org/video?id=1" },
].map((video) => ({
  author: 1,
  original_name: "东方作品",
  repost_name: "中文字幕",
  date: "2026-10-01",
  translation_status: 1,
  original_duration: 60,
  ...video,
}));
module.exports = { biliPairs, nicoIds, authors, videos };
