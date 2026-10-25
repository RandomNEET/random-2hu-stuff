// Synthetic, in-memory benchmark. Never opens the project's SQLite database.
const assert = require("node:assert/strict");
const { performance } = require("node:perf_hooks");
const Fuse = require("../../backend/node_modules/fuse.js");
const { createRepository } = require("../../backend/src/database.cjs");
const {
  createSearchService,
  parseSearchFilters,
} = require("../../backend/src/search.cjs");
const queries = require("../../backend/src/queries.cjs");
const { fixtureDatabase, all, close } = require("./fixtures/database.cjs");
const { legacyApi } = require("./fixtures/legacy.cjs");

async function median(operation, samples = 7) {
  const times = [];
  for (let i = 0; i < samples; i++) {
    const start = performance.now();
    await operation();
    times.push(performance.now() - start);
  }
  return times.sort((a, b) => a - b)[Math.floor(samples / 2)];
}
async function main() {
  const db = await fixtureDatabase(":memory:", { authors: 300, videos: 20000 });
  try {
    const old = legacyApi(db);
    const newRepository = createRepository(db);
    for (const [endpoint, sql] of [
      ["/api/authors", queries.AUTHORS],
      ["/api/authors/list", queries.AUTHORS_LIST],
      ["/api/stats", queries.STATS],
    ]) {
      const before = old.queries.length;
      const baseline = (await old.request(endpoint)).body;
      const originalSql = old.queries[before].sql;
      const actual = await all(db, sql);
      assert.deepEqual(
        endpoint === "/api/stats" ? actual[0] : actual,
        baseline,
      );
      const oldMs = await median(() => all(db, originalSql));
      const newMs = await median(() => all(db, sql));
      console.log(
        JSON.stringify({
          endpoint,
          oldMedianMs: +oldMs.toFixed(2),
          newMedianMs: +newMs.toFixed(2),
          speedup: +(oldMs / newMs).toFixed(2),
        }),
      );
    }
    let oldBuilds = 0,
      newBuilds = 0;
    class OldFuse extends Fuse {
      constructor(...args) {
        super(...args);
        oldBuilds++;
      }
    }
    class NewFuse extends Fuse {
      constructor(...args) {
        super(...args);
        newBuilds++;
      }
    }
    const legacySearch = legacyApi(db, { FuseClass: OldFuse });
    const newSearch = createSearchService(newRepository, {
      FuseClass: NewFuse,
    });
    const filters = parseSearchFilters({
      translationStatus: "1",
      limit: "100",
    });
    const terms = Array.from({ length: 20 }, (_, i) => `东方 第${i + 1}话`);
    const started = performance.now();
    const expected = [];
    for (const term of terms)
      expected.push(
        (
          await legacySearch.request(
            `/api/search/videos?q=${encodeURIComponent(term)}&translationStatus=1`,
          )
        ).body,
      );
    const oldMs = performance.now() - started;
    const next = performance.now();
    const actualResults = [];
    for (const term of terms)
      actualResults.push(
        JSON.parse(JSON.stringify(await newSearch.videos(term, filters))),
      );
    const newMs = performance.now() - next;
    for (let i = 0; i < terms.length; i++)
      assert.deepEqual(actualResults[i], expected[i]);
    console.log(
      JSON.stringify({
        workload: "20 distinct queries, same filter",
        oldMs: +oldMs.toFixed(2),
        newMs: +newMs.toFixed(2),
        oldIndexBuilds: oldBuilds,
        newIndexBuilds: newBuilds,
      }),
    );
  } finally {
    await close(db);
  }
}
main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
