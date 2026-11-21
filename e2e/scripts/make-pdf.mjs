// Builds out/smoke-report.pdf: a results table, then every screenshot with
// its caption, desktop first, then mobile. Usage: node scripts/make-pdf.mjs
import { chromium } from "@playwright/test";
import { existsSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const out = join(root, "out");
const manifest = join(out, "shots", "manifest.jsonl");
if (!existsSync(manifest)) {
  console.error("No screenshots: run `npx playwright test` first.");
  process.exit(1);
}

const shots = readFileSync(manifest, "utf8").trim().split("\n").map((l) => JSON.parse(l));
const order = ["desktop-1440", "mobile-390"];
shots.sort((a, b) => order.indexOf(a.project) - order.indexOf(b.project) || a.file.localeCompare(b.file));

const rows = [];
const resultsFile = join(out, "results.json");
if (existsSync(resultsFile)) {
  const res = JSON.parse(readFileSync(resultsFile, "utf8"));
  const walk = (suite) => {
    for (const s of suite.suites ?? []) walk(s);
    for (const spec of suite.specs ?? []) {
      for (const t of spec.tests) {
        const r = t.results.at(-1) ?? {};
        const note = (t.annotations ?? []).map((a) => a.description).filter(Boolean).join(" ");
        rows.push({ title: spec.title, project: t.projectName, status: r.status ?? "not run", ms: r.duration ?? 0, note });
      }
    }
  };
  walk(res);
}

const esc = (s) => String(s).replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" })[c]);
const stamp = new Date().toLocaleString("en-IN", { timeZone: "Asia/Kolkata" });
const targets = ["E2E_CRM_URL", "E2E_EL_URL", "E2E_POSTURE_URL", "E2E_SCREENING_URL", "E2E_API_URL"]
  .map((k) => `${k}=${process.env[k] || "(local default)"}`)
  .join(" · ");

const html = `<!doctype html><html><head><meta charset="utf-8"><style>
body{font:12px/1.4 -apple-system,Segoe UI,Arial,sans-serif;margin:0;color:#14213d}
.page{page-break-after:always;padding:18px 22px}
h1{font-size:18px;margin:0 0 4px} .muted{color:#667}
table{border-collapse:collapse;width:100%;margin-top:12px} td,th{border:1px solid #ccd;padding:5px 7px;text-align:left}
.passed{color:#0a7a3d;font-weight:600}.failed,.timedOut{color:#b00020;font-weight:700}.skipped{color:#8a6d00}
.cap{font-weight:600;margin-bottom:6px} img{max-width:100%;max-height:640px;border:1px solid #ccd}
</style></head><body>
<div class="page"><h1>AV Suite smoke suite (EN-3)</h1>
<div class="muted">${esc(stamp)} IST · ${esc(targets)}</div>
<table><tr><th>Flow</th><th>Viewport</th><th>Result</th><th>Time</th><th>Note</th></tr>
${rows.map((r) => `<tr><td>${esc(r.title)}</td><td>${r.project}</td><td class="${r.status}">${r.status}</td><td>${(r.ms / 1000).toFixed(1)} s</td><td>${esc(r.note)}</td></tr>`).join("")}
</table></div>
${shots
  .map(
    (s, i) => `<div class="page"><div class="cap">${i + 1}. [${s.project}] ${esc(s.flow)}: ${esc(s.caption)}</div>
<img src="data:image/png;base64,${readFileSync(s.file).toString("base64")}"></div>`,
  )
  .join("\n")}
</body></html>`;

const browser = await chromium.launch();
const page = await browser.newPage();
await page.setContent(html, { waitUntil: "load" });
const pdf = join(out, "smoke-report.pdf");
await page.pdf({ path: pdf, format: "A4", landscape: true, printBackground: true });
await browser.close();
console.log(`${pdf}: ${rows.length} results, ${shots.length} screenshots`);
