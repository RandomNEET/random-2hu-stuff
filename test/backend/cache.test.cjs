const { test } = require("node:test");
const assert = require("node:assert/strict");
const { AsyncLruCache, CACHE_TTL } = require("../../backend/src/cache.cjs");

test("concurrent cache misses share one loader and one serialized result", async () => {
  const cache = new AsyncLruCache();
  let loads = 0;
  const loader = async () => { loads++; await new Promise(resolve => setImmediate(resolve)); return "payload"; };
  assert.deepEqual(await Promise.all(Array.from({length: 20}, () => cache.load("a", loader))), Array(20).fill("payload"));
  assert.equal(loads, 1);
  assert.equal(cache.pending.size, 0);
  assert.equal(cache.size, 1);
});

test("expiry and failed loads are retried instead of caching errors", async () => {
  let now = 0;
  const cache = new AsyncLruCache({now: () => now});
  await assert.rejects(cache.load("a", () => Promise.reject(new Error("offline"))), /offline/);
  assert.equal(cache.size, 0);
  assert.equal(cache.pending.size, 0);
  assert.equal(await cache.load("a", () => "first"), "first");
  now = CACHE_TTL;
  assert.equal(await cache.load("a", () => "second"), "second");
});

test("LRU eviction enforces both entry and UTF-8 byte budgets", () => {
  const cache = new AsyncLruCache({maxEntries: 2, maxWeight: 7});
  cache.set("a", "东方");
  cache.set("b", "b");
  cache.get("a");
  cache.set("c", "c");
  assert.equal(cache.get("b"), undefined);
  assert.equal(cache.get("a"), "东方");
  assert.equal(cache.weight, 7);
  cache.set("too-large", "12345678");
  assert.equal(cache.get("too-large"), undefined);
  assert.equal(cache.size, 2);
  cache.set("a", "a");
  assert.equal(cache.weight, 2);
});
