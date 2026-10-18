const CACHE_TTL = 5 * 60 * 1000;

class AsyncLruCache {
  constructor({
    ttl = CACHE_TTL,
    maxEntries = 256,
    maxWeight = 32 * 1024 * 1024,
    weightOf = (value) => Buffer.byteLength(value ?? "", "utf8"),
    now = Date.now,
  } = {}) {
    this.ttl = ttl;
    this.maxEntries = maxEntries;
    this.maxWeight = maxWeight;
    this.weightOf = weightOf;
    this.now = now;
    this.entries = new Map();
    this.pending = new Map();
    this.weight = 0;
  }

  get size() {
    return this.entries.size;
  }

  delete(key) {
    const entry = this.entries.get(key);
    if (entry) this.weight -= entry.weight;
    this.entries.delete(key);
  }

  get(key) {
    const entry = this.entries.get(key);
    if (!entry) return undefined;
    if (this.now() >= entry.expiresAt) {
      this.delete(key);
      return undefined;
    }
    this.entries.delete(key);
    this.entries.set(key, entry);
    return entry.value;
  }

  set(key, value) {
    this.delete(key);
    const weight = Math.max(1, this.weightOf(value));
    if (weight > this.maxWeight || this.maxEntries < 1) return;
    this.prune();
    while (
      this.entries.size >= this.maxEntries ||
      this.weight + weight > this.maxWeight
    ) {
      this.delete(this.entries.keys().next().value);
    }
    this.entries.set(key, {
      value,
      weight,
      expiresAt: this.now() + this.ttl,
    });
    this.weight += weight;
  }

  load(key, loader) {
    const cached = this.get(key);
    if (cached !== undefined) return Promise.resolve(cached);
    if (this.pending.has(key)) return this.pending.get(key);
    const promise = Promise.resolve()
      .then(loader)
      .then((value) => {
        this.set(key, value);
        return value;
      })
      .finally(() => this.pending.delete(key));
    this.pending.set(key, promise);
    return promise;
  }

  prune() {
    const now = this.now();
    for (const [key, entry] of this.entries) {
      if (now >= entry.expiresAt) this.delete(key);
    }
  }
}

module.exports = { AsyncLruCache, CACHE_TTL };
