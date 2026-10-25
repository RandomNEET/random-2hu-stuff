const { test } = require("node:test");
const assert = require("node:assert/strict");
const { videoKey, authorKey } = require("../../backend/src/search-links.cjs");
const {
  createSearchService,
  parseSearchFilters,
} = require("../../backend/src/search.cjs");
const { CACHE_TTL } = require("../../backend/src/cache.cjs");
const {
  biliPairs,
  nicoIds,
  authors,
  videos,
} = require("./fixtures/search-links.cjs");
const repo = {
  searchVideos: async () => videos,
  searchAuthors: async () => authors,
};
const ids = (items) => items.map((item) => item.id);

test("multiple Nico IDs and link variants match exactly, not by a shared prefix", async () => {
  const service = createSearchService(repo);
  for (const [i, id] of nicoIds.entries()) {
    for (const query of [
      id,
      id.toUpperCase(),
      `https://www.nicovideo.jp/watch/${id}?from=search#t=20`,
      `https://nico.ms/${id}?from=share`,
      `sp.nicovideo.jp/watch/${id}/`,
    ]) {
      assert.deepEqual(
        ids(await service.videos(query, parseSearchFilters({}))),
        [i + 1],
        query,
      );
    }
  }
  assert.deepEqual(
    await service.videos("sm33678187", parseSearchFilters({})),
    [],
  );
  assert.notEqual(videoKey("sm9"), videoKey("sm90"));
});

test("known AV/BV pairs interoperate in both directions, retaining BV body case", async () => {
  const service = createSearchService(repo);
  for (const [i, [av, bv]] of biliPairs.entries()) {
    assert.equal(videoKey(bv), `bili:${av}`);
    for (const query of [
      `av${av}`,
      bv,
      `bv${bv.slice(2)}`,
      `https://m.bilibili.com/video/${bv}/?p=2&spm_id_from=333.1`,
      `https://www.bilibili.com/video/av${av}?t=50`,
    ]) {
      assert.deepEqual(
        ids(await service.videos(query, parseSearchFilters({}))),
        i === 0 ? [4, 8] : [i + 4],
      );
    }
  }
  const avOnly = createSearchService({
    ...repo,
    searchVideos: async () => [
      { id: 1, original_url: "https://bilibili.com/video/av170001" },
    ],
  });
  assert.deepEqual(
    ids(await avOnly.videos("BV17x411w7KC", parseSearchFilters({}))),
    [1],
  );
  assert.notEqual(videoKey("BV17x411w7KC"), videoKey("BV17x411w7Kc"));
  for (const bad of [
    "av0",
    "av2251799813685248",
    "BV1000000000",
    "BV17x411w7K",
    "BV17x411w7KCextra",
  ])
    assert.equal(videoKey(bad), null, bad);
});

test("YouTube video forms share identity and unknown URLs retain meaningful query params", async () => {
  const service = createSearchService(repo);
  for (const query of [
    "https://youtu.be/dQw4w9WgXcQ?si=abc",
    "https://m.youtube.com/watch?v=dQw4w9WgXcQ&t=40",
    "https://www.youtube.com/shorts/dQw4w9WgXcQ",
    "youtube.com/live/dQw4w9WgXcQ",
  ]) {
    const results = await service.videos(query, parseSearchFilters({}));
    assert.deepEqual(ids(results), [7]);
    assert.equal(results[0].searchScore, 0);
    assert.equal(results[0].translation_status_text, "中文内嵌");
  }
  assert.deepEqual(
    ids(
      await service.videos(
        "http://example.org/video/?utm_source=x&id=1#top",
        parseSearchFilters({}),
      ),
    ),
    [10],
  );
  for (const query of [
    "https://example.org/video?id=2",
    "https://youtube.com.evil.test/watch?v=dQw4w9WgXcQ",
    "https://youtu.be/dQw4w9WgXCQ",
    "https://b23.tv/unknown",
  ])
    assert.deepEqual(await service.videos(query, parseSearchFilters({})), []);
  for (const query of [null, undefined, "", " ", "not a link"])
    assert.equal(videoKey(query), null);
});

test("link results retain every filter and slice limit behavior", async () => {
  const service = createSearchService({
    ...repo,
    searchVideos: async () => [
      { ...videos[3], id: 1 },
      {
        ...videos[3],
        id: 2,
        author: 2,
        date: "2026-09-01",
        translation_status: 2,
        original_duration: 0,
      },
      { ...videos[3], id: 3, original_duration: null, repost_duration: null },
    ],
  });
  for (const [query, expected] of [
    [{}, [1, 2, 3]],
    [{ author: "2" }, [2]],
    [{ dateFrom: "2026-10-01" }, [1, 3]],
    [{ dateTo: "2026-09-01" }, [2]],
    [{ translationStatus: "2" }, [2]],
    [{ minDuration: "0", maxDuration: "0" }, [2]],
    [{ minDuration: "60" }, [1]],
    [{ minDuration: "60", includeUnknownDuration: "1" }, [1, 3]],
    [{ limit: "1" }, [1]],
    [{ limit: "-1" }, [1, 2]],
  ])
    assert.deepEqual(
      ids(await service.videos("av170001", parseSearchFilters(query))),
      expected,
    );
});

test("author profile links normalize platform variants but do not infer unrelated identities", async () => {
  const service = createSearchService(repo);
  for (const query of [
    "https://youtube.com/@creator/videos?si=test",
    "//m.youtube.com/@Creator/about/",
    "https://sp.nicovideo.jp/user/00123/video?from=x",
    "x.com/CREATOR/?utm_source=x",
  ]) {
    const results = await service.authors(query, 10);
    assert.deepEqual(ids(results), [1], query);
    assert.equal(results[0].displayName, "频道甲");
  }
  assert.deepEqual(
    ids(await service.authors(authors[1].yt_url + "/streams", 10)),
    [2],
  );
  for (const query of [
    "https://x.com/Creator2",
    "https://youtube.com/@unknown",
    "https://youtube.com/user/Creator",
  ])
    assert.deepEqual(await service.authors(query, 10), []);
  assert.notEqual(
    authorKey(authors[1].yt_url),
    authorKey(authors[1].yt_url.toLowerCase()),
  );
  assert.equal(authorKey(null), null);
  assert.deepEqual(await service.authors("https://x.com/Creator", -1), []);
});

test("identity indexes expire with the complete snapshot and never add internal fields to results", async () => {
  let now = 0,
    loads = 0;
  const service = createSearchService(
    {
      ...repo,
      searchVideos: async () => {
        loads++;
        return loads === 1 ? videos : [];
      },
    },
    { now: () => now },
  );
  const result = await service.videos("sm9", parseSearchFilters({}));
  assert.deepEqual(
    Object.keys(result[0]).sort(),
    [
      ...Object.keys(videos[1]),
      "searchScore",
      "translation_status_text",
    ].sort(),
  );
  await service.videos("av170001", parseSearchFilters({}));
  assert.equal(loads, 1);
  now = CACHE_TTL;
  assert.deepEqual(await service.videos("sm9", parseSearchFilters({})), []);
  assert.equal(loads, 2);
});

test("ordinary text searches avoid parsing links and link queries reuse the identity index", async () => {
  let reads = 0;
  const video = { id: 1, original_name: "东方作品" };
  Object.defineProperty(video, "original_url", {
    get() {
      reads++;
      return "https://nicovideo.jp/watch/sm9";
    },
  });
  const service = createSearchService({
    ...repo,
    searchVideos: async () => [video],
  });
  await service.videos("东方", parseSearchFilters({}));
  assert.equal(reads, 0);
  assert.deepEqual(
    ids(await service.videos("sm9", parseSearchFilters({}))),
    [1],
  );
  assert.equal(reads, 1);
  assert.deepEqual(
    ids(await service.videos("https://nico.ms/sm9", parseSearchFilters({}))),
    [1],
  );
  assert.equal(reads, 1);
});
