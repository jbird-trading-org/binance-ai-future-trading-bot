import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import dotenv from "dotenv";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");

let loaded = false;

/** Project root directory (neko-futures-trader). */
export function getProjectRoot(): string {
  return ROOT;
}

/** Load `.env` from project root once. */
export function loadEnv(): void {
  if (loaded) return;
  const envPath = path.join(ROOT, ".env");
  if (fs.existsSync(envPath)) {
    dotenv.config({ path: envPath });
  }
  loaded = true;
}

export function requireEnv(name: string): string {
  loadEnv();
  const value = process.env[name]?.trim();
  if (!value) throw new Error(`Missing required env: ${name}`);
  return value;
}

export function envOr(name: string, fallback = ""): string {
  loadEnv();
  return process.env[name]?.trim() || fallback;
}
