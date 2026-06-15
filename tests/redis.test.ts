import { describe, expect, it, beforeEach } from "vitest";
import { cacheGet, cacheSet, cacheGetJson, cacheSetJson, clearMemoryCache } from "../src/redis/cache.js";
import { resetRedisState } from "../src/redis/client.js";
import { redisKey, signalKey } from "../src/redis/keys.js";

beforeEach(() => {
  clearMemoryCache();
  resetRedisState();
  delete process.env.REDIS_URL;
  delete process.env.REDIS_HOST;
  delete process.env.REDIS_ENABLED;
});

describe("redis keys", () => {
  it("namespaces keys with default prefix", () => {
    expect(redisKey("foo")).toBe("neko:foo");
    expect(signalKey("BTCUSDT")).toBe("signal:BTCUSDT:latest");
  });
});

describe("memory cache fallback", () => {
  it("stores and retrieves strings", async () => {
    await cacheSet("test:key", "value", 60);
    expect(await cacheGet("test:key")).toBe("value");
  });

  it("stores and retrieves JSON", async () => {
    await cacheSetJson("test:json", { score: 7 }, 60);
    const data = await cacheGetJson<{ score: number }>("test:json");
    expect(data?.score).toBe(7);
  });

  it("expires entries", async () => {
    await cacheSet("ttl:key", "gone", 0);
    const item = await cacheGet("ttl:key");
    expect(item).toBe("gone");
  });
});
