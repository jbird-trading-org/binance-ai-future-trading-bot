import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import { config } from "../config.js";
import { loadEnv, getProjectRoot } from "../lib/env.js";
import { fetchAccountData } from "./accountData.js";
import { ensureRedisReady } from "../redis/client.js";

loadEnv();

const ROOT = getProjectRoot();
const STATIC_DIR = path.join(ROOT, "static");
const HTML_FILE = path.join(STATIC_DIR, "neko-light.html");

const MIME: Record<string, string> = {
  ".html": "text/html",
  ".js": "application/javascript",
  ".css": "text/css",
  ".json": "application/json",
  ".png": "image/png",
};

function serveStatic(urlPath: string, res: http.ServerResponse): void {
  const rel = urlPath === "/" ? HTML_FILE : path.join(ROOT, urlPath.replace(/^\//, ""));
  const resolved = path.resolve(rel);
  if (!resolved.startsWith(ROOT)) {
    res.writeHead(403);
    res.end("Forbidden");
    return;
  }
  if (!fs.existsSync(resolved)) {
    res.writeHead(404);
    res.end("Not found");
    return;
  }
  const ext = path.extname(resolved);
  const data = fs.readFileSync(resolved);
  res.writeHead(200, { "Content-Type": MIME[ext] ?? "text/plain" });
  res.end(data);
}

async function handleApi(res: http.ServerResponse): Promise<void> {
  try {
    const data = await fetchAccountData();
    res.writeHead(200, {
      "Content-Type": "application/json",
      "Access-Control-Allow-Origin": "*",
      "Cache-Control": "no-store",
    });
    res.end(JSON.stringify(data));
  } catch (err) {
    res.writeHead(500, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ error: err instanceof Error ? err.message : String(err) }));
  }
}

export function createDashboardServer(): http.Server {
  return http.createServer(async (req, res) => {
    res.setHeader("Access-Control-Allow-Origin", "*");
    res.setHeader("Access-Control-Allow-Methods", "GET, OPTIONS");
    if (req.method === "OPTIONS") {
      res.writeHead(200);
      res.end();
      return;
    }
    const url = (req.url ?? "/").split("?")[0];
    if (url === "/api") await handleApi(res);
    else serveStatic(url, res);
  });
}

async function main(): Promise<void> {
  await ensureRedisReady();
  const server = createDashboardServer();
  server.listen(config.dashboardPort, () => {
    console.log(`🚀 Neko Dashboard (TypeScript) on http://localhost:${config.dashboardPort}`);
  });
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
