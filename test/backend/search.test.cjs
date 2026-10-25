const { test } = require("node:test");
const assert = require("node:assert/strict");
const Fuse = require("../../backend/node_modules/fuse.js");
const {
  createSearchService,
  parseSearchFilters,
} = require("../../backend/src/search.cjs");
const { CACHE_TTL } = require("../../backend/src/cache.cjs");

function repository() {
  const counts = { videos: 0, authors: 0 };
  return {
    counts,
    async searchVideos() {
      counts.videos++;
      return [1, 2, 3].map((id) => ({
        id,
        author: 1,
        original_name: `东方 第${id}话`,
        repost_name: `字幕 ${id}`,
        translation_status: 1,
      }));
    },
    async searchAuthors() {
      counts.authors++;
      return [{ id: 1, yt_name: "作者 ニコ" }];
    },
  };
}

test("different terms and limits reuse the same filtered index and author index", async () => {
  const repo = repository();
  let builds = 0;
  class CountingFuse extends Fuse {
    constructor(...args) {
      super(...args);
      builds++;
    }
  }
  const search = createSearchService(repo, { FuseClass: CountingFuse });
  await search.videos("东方", parseSearchFilters({ author: "1", limit: "1" }));
  await search.videos("字幕", parseSearchFilters({ author: "1", limit: "2" }));
  await search.authors("作者", 1);
  await search.authors("ニコ", 2);
  assert.equal(builds, 2);
  assert.deepEqual(repo.counts, { videos: 1, authors: 1 });
});

test("concurrent distinct searches share each snapshot load and rebuild after TTL", async () => {
  const repo = repository();
  let now = 0,
    builds = 0;
  class CountingFuse extends Fuse {
    constructor(...args) {
      super(...args);
      builds++;
    }
  }
  const search = createSearchService(repo, {
    now: () => now,
    FuseClass: CountingFuse,
  });
  await Promise.all(
    Array.from({ length: 20 }, (_, i) =>
      search.videos(`东方 ${i}`, parseSearchFilters({})),
    ),
  );
  assert.deepEqual(repo.counts, { videos: 1, authors: 1 });
  assert.equal(builds, 1);
  now = CACHE_TTL;
  await search.videos("东方", parseSearchFilters({}));
  assert.deepEqual(repo.counts, { videos: 2, authors: 2 });
  assert.equal(builds, 2);
});

test("a late partial refresh cannot overwrite the next successful snapshot", async () => {
  let releaseFirst;
  let attempts = 0;
  const repo = {
    searchVideos() {
      attempts++;
      if (attempts === 1)
        return new Promise((resolve) => {
          releaseFirst = resolve;
        });
      return Promise.resolve([{ id: 2, original_name: "东方 new", author: 2 }]);
    },
    searchAuthors() {
      return attempts === 1
        ? Promise.reject(new Error("authors unavailable"))
        : Promise.resolve([{ id: 2, yt_name: "new author" }]);
    },
  };
  const search = createSearchService(repo);
  await assert.rejects(
    search.videos("东方", parseSearchFilters({})),
    /authors unavailable/,
  );
  assert.deepEqual(
    (await search.videos("东方", parseSearchFilters({}))).map((v) => v.id),
    [2],
  );
  releaseFirst([{ id: 1, original_name: "东方 old", author: 1 }]);
  await new Promise((resolve) => setImmediate(resolve));
  assert.deepEqual(
    (await search.videos("东方", parseSearchFilters({}))).map((v) => v.id),
    [2],
  );
  assert.equal(attempts, 2);
});
