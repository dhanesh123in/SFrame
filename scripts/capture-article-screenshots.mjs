#!/usr/bin/env node
/**
 * Capture Medium article screenshots. Requires dev servers on :3000 and :8100.
 * Usage: node scripts/capture-article-screenshots.mjs
 */
import { chromium } from "playwright";
import { mkdir } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, "..");
const OUT = path.join(ROOT, "docs/medium-article/screenshots");
const SAMPLE = path.join(ROOT, "docs/medium-article/sample.jpg");
const BASE = "http://127.0.0.1:3000";

async function shot(page, name, opts = {}) {
  const file = path.join(OUT, name);
  await page.screenshot({ path: file, fullPage: false, ...opts });
  console.log("wrote", file);
}

async function main() {
  await mkdir(OUT, { recursive: true });

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    deviceScaleFactor: 2,
    colorScheme: "dark",
  });
  const page = await context.newPage();

  // 1 — Import / home
  await page.goto(BASE, { waitUntil: "networkidle" });
  await shot(page, "01-import.png");

  // 2 — Upload → crop (wait until crop UI is ready, not mid-upload)
  await page.locator('input[type="file"]').setInputFiles(SAMPLE);
  await page.getByRole("heading", { name: "Crop & color" }).waitFor({ timeout: 30_000 });
  await page.waitForTimeout(1200);
  await shot(page, "02-crop.png");

  // 3 — Enhance (UltraSharp default)
  await page.getByRole("tab", { name: "Enhance" }).click();
  await page.getByText("Super-Resolution").waitFor();
  await page.waitForTimeout(500);
  await shot(page, "03-enhance-ultrasharp.png");

  // 4 — UltraSharp export + before/after slider (smaller file for reasonable capture time)
  const small = path.join(ROOT, "docs/medium-article/sample-small.jpg");
  await page.getByRole("button", { name: "Start over" }).click().catch(() => {});
  await page.goto(BASE, { waitUntil: "networkidle" });
  await page.locator('input[type="file"]').setInputFiles(small);
  await page.getByRole("heading", { name: "Crop & color" }).waitFor({ timeout: 30_000 });
  await page.getByRole("tab", { name: "Enhance" }).click();
  await page.getByRole("button", { name: "UltraSharp v2" }).click();
  await page.getByRole("button", { name: "Upscale 4×" }).click();
  await page.getByRole("link", { name: /Download upscaled/i }).waitFor({ timeout: 300_000 });
  await page.getByRole("tab", { name: "Export" }).click();
  await page.waitForTimeout(800);
  await shot(page, "04-export-before-after.png");

  // 5 — History
  await page.getByRole("tab", { name: "History" }).click();
  await page.getByRole("heading", { name: "History" }).waitFor({ timeout: 15_000 });
  await page.waitForTimeout(800);
  await shot(page, "05-history.png");

  // 6 — API health (GPU)
  const health = await context.newPage();
  await health.goto("http://127.0.0.1:8100/health", { waitUntil: "networkidle" });
  await shot(health, "06-health-gpu.png");

  await browser.close();
  console.log("\nDone. Screenshots in docs/medium-article/screenshots/");
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
