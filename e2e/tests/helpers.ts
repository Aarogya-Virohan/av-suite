import { expect, Locator, Page, TestInfo } from "@playwright/test";
import { appendFileSync, mkdirSync } from "node:fs";
import { join } from "node:path";

// Targets. Defaults = the container stack from scripts/local-stack.sh.
export const T = {
  api: env("E2E_API_URL", "http://localhost:8000"),
  crm: env("E2E_CRM_URL", "http://localhost:3000"),
  el: env("E2E_EL_URL", "http://localhost:3001"),
  posture: env("E2E_POSTURE_URL", "http://localhost:3002"),
  screening: env("E2E_SCREENING_URL", "http://localhost:3005"),
  email: env("E2E_EMAIL", "admin@physiodemo.in"),
  password: process.env.E2E_PASSWORD || process.env.AV_SEED_PASSWORD || "",
  postureImages: process.env.E2E_POSTURE_IMAGES || "",
};

function env(name: string, fallback: string): string {
  return (process.env[name] || fallback).replace(/\/$/, "");
}

// Hard stop: this suite writes data. A remote host must look like staging
// ("staging" in the name, e.g. the Vercel `-git-staging-` alias) or be listed
// in E2E_ALLOW_HOSTS; known production hosts are always refused.
const PROD_HOSTS = [
  "av-suite-production.up.railway.app",
  ...(process.env.E2E_FORBIDDEN_HOSTS || "").split(",").map((h) => h.trim()).filter(Boolean),
];
const ALLOW = (process.env.E2E_ALLOW_HOSTS || "").split(",").map((h) => h.trim()).filter(Boolean);
for (const url of [T.api, T.crm, T.el, T.posture, T.screening]) {
  const host = new URL(url).host;
  const local = /^(localhost|127\.0\.0\.1)(:\d+)?$/.test(host);
  if (PROD_HOSTS.includes(host)) {
    throw new Error(`REFUSED: ${url} is production. The smoke suite only runs on staging or local.`);
  }
  if (!local && !host.includes("staging") && !ALLOW.includes(host)) {
    throw new Error(`REFUSED: ${url} is not local and not a staging host (add it to E2E_ALLOW_HOSTS only if it is staging).`);
  }
}
if (!T.password) {
  throw new Error("Set E2E_PASSWORD (or AV_SEED_PASSWORD): the demo clinic password from tests/seed.py.");
}

/** Unique, readable suffix so reruns never collide. */
export const RUN = new Date().toISOString().slice(5, 19).replace(/[-T:]/g, "");

const SHOT_DIR = join(__dirname, "..", "out", "shots");
let counter = 0;

/** One screenshot per step, with a caption for the PDF. */
export async function shot(page: Page, info: TestInfo, flow: string, caption: string, mask: Locator[] = []) {
  const project = info.project.name;
  const dir = join(SHOT_DIR, project);
  mkdirSync(dir, { recursive: true });
  counter += 1;
  const file = join(dir, `${String(counter).padStart(3, "0")}-${flow}.png`);
  await page.waitForTimeout(400);
  await page.screenshot({ path: file, fullPage: false, mask });
  appendFileSync(
    join(SHOT_DIR, "manifest.jsonl"),
    JSON.stringify({ project, flow, caption, file, at: new Date().toISOString() }) + "\n",
  );
}

/** Every AV app uses the same email + password form. */
export async function login(page: Page, baseUrl: string) {
  await page.goto(`${baseUrl}/login`);
  await page.locator('input[type="email"]').fill(T.email);
  await page.locator('input[type="password"]').fill(T.password);
  await page.locator('button[type="submit"]').click();
  await expect(page).not.toHaveURL(/\/login(\?|$)/);
  await page.waitForLoadState("networkidle");
}

/** API helper with a fresh token (for lookups the UI step does not show). */
export async function apiToken(): Promise<string> {
  const res = await fetch(`${T.api}/api/v1/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email: T.email, password: T.password }),
  });
  const body = await res.json();
  const token = body.access_token ?? body.data?.access_token;
  if (!token) throw new Error(`login failed: ${res.status}`);
  return token;
}

/** Shared patient for the invoice / Rx / screening flows (created once via the API). */
export const SHARED_PATIENT = { first: "Smoke", last: `Shared ${RUN}` };

export async function ensureSharedPatient(): Promise<string> {
  const token = await apiToken();
  const h = { Authorization: `Bearer ${token}`, "Content-Type": "application/json" };
  const q = encodeURIComponent(SHARED_PATIENT.last);
  const found = await (await fetch(`${T.api}/api/v1/patients?search=${q}`, { headers: h })).json();
  const rows = (found.data ?? found.items ?? found) as Array<{ id: string; last_name: string }>;
  const hit = Array.isArray(rows) ? rows.find((r) => r.last_name === SHARED_PATIENT.last) : undefined;
  if (hit) return hit.id;
  const res = await fetch(`${T.api}/api/v1/patients`, {
    method: "POST",
    headers: h,
    body: JSON.stringify({
      first_name: SHARED_PATIENT.first,
      last_name: SHARED_PATIENT.last,
      phone: "9000000899",
      chief_complaint: "Smoke test patient (shared)",
    }),
  });
  if (!res.ok) throw new Error(`create shared patient: ${res.status} ${await res.text()}`);
  const body = await res.json();
  return (body.data ?? body).id;
}
