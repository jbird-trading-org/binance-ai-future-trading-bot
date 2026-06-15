import { loadEnv } from "../src/lib/env.js";
import { closeRedisClient, ensureRedisReady, isRedisEnabled, resetRedisState } from "../src/redis/client.js";
import { cacheSet, cacheGet, clearMemoryCache } from "../src/redis/cache.js";

loadEnv();

async function main(): Promise<void> {
  const enabled = isRedisEnabled();
  console.log(`Redis enabled: ${enabled}`);

  if (!enabled) {
    console.log("Set REDIS_URL or REDIS_HOST to enable Redis. Using in-memory fallback.");
    await cacheSet("health:ping", "ok", 10);
    const val = await cacheGet("health:ping");
    console.log(`Memory fallback OK: ${val}`);
    clearMemoryCache();
    return;
  }

  const ready = await ensureRedisReady();
  if (!ready) {
    console.error("Redis unreachable.");
    process.exit(1);
  }

  await cacheSet("health:ping", "ok", 30);
  const val = await cacheGet("health:ping");
  console.log(`Redis ping OK: ${val}`);
  await closeRedisClient();
}

main().catch((err) => {
  console.error(err);
  resetRedisState();
  process.exit(1);
});
