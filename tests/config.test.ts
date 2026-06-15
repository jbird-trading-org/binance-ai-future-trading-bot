import { describe, expect, it } from "vitest";
import { config, SAFE_COINS } from "../src/config.js";
import { getProjectRoot, loadEnv } from "../src/lib/env.js";

describe("config", () => {
  it("exports trading defaults from config.py", () => {
    expect(config.leverage).toBe(10);
    expect(config.minScoreNormal).toBe(8);
    expect(config.dynamicCoinsEnabled).toBe(true);
    expect(SAFE_COINS).toContain("BTCUSDT");
  });
});

describe("env", () => {
  it("resolves project root", () => {
    const root = getProjectRoot();
    expect(root.endsWith("neko-futures-trader")).toBe(true);
  });

  it("loads env without throwing", () => {
    expect(() => loadEnv()).not.toThrow();
  });
});
