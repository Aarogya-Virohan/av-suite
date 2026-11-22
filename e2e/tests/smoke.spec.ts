import { expect, test } from "@playwright/test";
import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { apiToken, ensureSharedPatient, login, RUN, SHARED_PATIENT, shot, T } from "./helpers";

// One smoke per launch flow (launch-plan EN-3). Each test creates its own
// rows with a RUN suffix, so reruns on the same demo clinic never collide.
// Demo phones stay in the fixed 90000 series used by tests/seed.py.

const phone = (n: number) => `90000${String(800 + n).padStart(5, "0")}`;

const SHARED = `${SHARED_PATIENT.first} ${SHARED_PATIENT.last}`;

test.beforeAll(async () => {
  await ensureSharedPatient();
});

test("01 login: CRM sign-in and dashboard", async ({ page }, info) => {
  await page.goto(`${T.crm}/login`);
  await shot(page, info, "login", "CRM login page");
  await page.locator('input[type="email"]').fill(T.email);
  await page.locator('input[type="password"]').fill("wrong-password");
  await page.locator('button[type="submit"]').click();
  await expect(page.getByText(/invalid|incorrect|wrong/i).first()).toBeVisible();
  await shot(page, info, "login", "Wrong password: error shown, no sign-in");
  await login(page, T.crm);
  await page.goto(`${T.crm}/dashboard`);
  await expect(page.getByText("AV Demo Physio").first()).toBeVisible();
  await shot(page, info, "login", "Dashboard after sign-in (demo clinic)");
});

test("02 lead: add a lead from the Leads page", async ({ page }, info) => {
  await login(page, T.crm);
  await page.goto(`${T.crm}/leads`);
  await shot(page, info, "lead", "Leads list (seeded)");
  await page.locator("main button").filter({ has: page.locator("svg.lucide-plus") }).first().click();
  await page.locator("#lead-name").fill(`Smoke Lead ${RUN}`);
  await page.locator("#lead-phone").fill(phone(1));
  await page.locator("#lead-source").selectOption("referral");
  await shot(page, info, "lead", "Add Lead form filled");
  await page.locator('form button[type="submit"]').click();
  await expect(page.getByText(`Smoke Lead ${RUN}`).first()).toBeVisible();
  await shot(page, info, "lead", "New lead visible in the list");
});

test("03 patient: add a patient and open the record", async ({ page }, info) => {
  await login(page, T.crm);
  await page.goto(`${T.crm}/patients`);
  await page.getByRole("button", { name: /add patient/i }).first().click();
  const form = page.locator("form").last();
  await form.locator('input[placeholder="Rajesh"]').fill("UI");
  await form.locator('input[placeholder="Kumar"]').fill(`Patient ${RUN}`);
  await form.locator("textarea").first().fill("Smoke test: lower back pain");
  await form.locator('input[type="tel"]').fill(phone(2));
  await shot(page, info, "patient", "Add Patient form filled");
  await form.locator('button[type="submit"]').click();
  await expect(page.getByText(/created successfully/i).first()).toBeVisible();
  await page.getByPlaceholder(/search by patient name/i).fill(`Patient ${RUN}`);
  const row = page.getByRole("row", { name: new RegExp(`Patient ${RUN}`) }).first();
  await expect(row).toBeVisible();
  await shot(page, info, "patient", "New patient found by search");
  await row.getByText(`Patient ${RUN}`).click();
  await expect(page).toHaveURL(/\/patients\/[0-9a-f-]{36}/);
  await page.waitForLoadState("networkidle");
  await shot(page, info, "patient", "Patient record opened");
});

test("04 invoice: create an invoice and open its PDF", async ({ page }, info) => {
  await login(page, T.crm);
  await page.goto(`${T.crm}/billing`);
  await shot(page, info, "invoice", "Billing: seeded invoices (paid / partial / issued)");
  await page.getByRole("button", { name: /create invoice/i }).first().click();
  const panel = page.getByRole("dialog", { name: "Create Invoice" });
  await expect(panel).toBeVisible();
  await shot(page, info, "invoice", "Create Invoice panel");
  const combo = panel.getByRole("combobox", { name: /patient/i });
  const label = await combo.locator("option", { hasText: SHARED }).first().textContent();
  await combo.selectOption({ label: (label ?? "").trim() });
  await panel.getByRole("textbox", { name: "Item 1 description" }).fill("Physiotherapy session (smoke)");
  await panel.getByRole("spinbutton", { name: "Item 1 unit price" }).fill("800");
  await shot(page, info, "invoice", "Invoice filled: 1 line, Rs 800");
  await panel.getByRole("button", { name: "Generate Invoice" }).click();
  await expect(panel).toBeHidden();
  await page.getByPlaceholder(/search invoices/i).fill(SHARED);
  await expect(page.locator("tr", { hasText: SHARED }).first()).toBeVisible();
  await shot(page, info, "invoice", "Invoice created and listed");
  const row = page.locator("tr", { hasText: SHARED }).first();
  await row.getByRole("button", { name: /invoice/i }).first().click();
  const preview = page.getByRole("dialog").filter({ hasText: /INV-\d+/ }).first();
  await expect(preview).toBeVisible();
  await expect(preview.getByText(SHARED).first()).toBeVisible();
  await shot(page, info, "invoice", "Invoice preview with clinic letterhead");
});

test("05 rx: build a prescription and download the PDF", async ({ page }, info) => {
  await login(page, T.el);
  await shot(page, info, "rx", "Exercise Library after sign-in");
  await page.getByRole("button", { name: /^Add / }).nth(0).click();
  await page.getByRole("button", { name: /^Add / }).nth(2).click();
  await shot(page, info, "rx", "Two exercises added to the prescription");
  // 390 px: library and prescription are tabs.
  const rxTab = page.getByRole("tab", { name: /^Prescription/ });
  if (await rxTab.isVisible()) await rxTab.click();
  await page.getByRole("button", { name: "Choose a patient" }).click();
  await page.keyboard.type(SHARED);
  await page.getByText(SHARED).last().click();
  await shot(page, info, "rx", "Patient picked");
  const download = page.waitForEvent("download", { timeout: 60_000 });
  await page.getByRole("button", { name: /pdf|download/i }).first().click();
  const file = await download;
  expect(file.suggestedFilename()).toMatch(/\.pdf$/i);
  const saved = join(__dirname, "..", "out", "artifacts", `${info.project.name}-${file.suggestedFilename()}`);
  await file.saveAs(saved);
  expect(readFileSync(saved).subarray(0, 4).toString()).toBe("%PDF");
  await shot(page, info, "rx", `Rx PDF downloaded: ${file.suggestedFilename()}`);
});

test("06 posture: start an assessment with uploaded photos", async ({ page }, info) => {
  await login(page, T.posture);
  await shot(page, info, "posture", "Posture tool: new assessment");
  const form = page.locator("main");
  await form.getByLabel(/name/i).first().fill(`Smoke Patient ${RUN}`);
  await form.getByLabel(/age/i).first().fill("34");
  await form.getByLabel(/height/i).first().fill("170");
  await shot(page, info, "posture", "Patient details filled");
  const images = T.postureImages ? readdirSync(T.postureImages).filter((f) => /\.(jpe?g|png)$/i.test(f)).sort() : [];
  test.skip(images.length < 3, "Set E2E_POSTURE_IMAGES to a folder with front / side / back photos of a standing person (sorted names) to run the analysis; without real photos only the form is checked.");
  const inputs = page.locator('input[type="file"]');
  for (let i = 0; i < 3; i++) await inputs.nth(i).setInputFiles(join(T.postureImages, images[i]));
  await shot(page, info, "posture", "Three photos uploaded");
  await page.getByRole("button", { name: /continue to landmark check/i }).click();
  await expect(page.getByText(/landmark/i).first()).toBeVisible({ timeout: 90_000 });
  await shot(page, info, "posture", "Landmark check");
});

test("07 screening: assign Tool 03 to a patient", async ({ page }, info) => {
  await login(page, T.screening);
  await page.goto(`${T.screening}/patients`);
  await shot(page, info, "screening", "Screening: patients");
  await page.locator('input[type="search"], input[type="text"]').first().fill(SHARED);
  await page.getByText(SHARED).first().click();
  await expect(page).toHaveURL(/\/patients\//);
  await shot(page, info, "screening", "Patient page in Screening");
  await page.getByRole("button", { name: "Send screener" }).click();
  await page.getByText("PHQ-9").click();
  await page.getByText("GAD-7").click();
  await shot(page, info, "screening", "Send a screener: PHQ-9 + GAD-7 chosen, 7 days");
  await page.getByRole("button", { name: "Create link" }).click();
  await expect(page.getByText(/choose at least one/i)).toHaveCount(0);
  await expect(page.getByText(/copy|whatsapp|link (is )?ready|created/i).first()).toBeVisible();
  await shot(page, info, "screening", "Link created (token masked in this PDF)", [
    page.locator('input[value*="/screener/"], code, [data-link]'),
  ]);
  // The assignment must exist server-side too (status only, no clinical data).
  const token = await apiToken();
  const res = await fetch(`${T.api}/api/v1/psychosocial/assignments?status=pending&page_size=100`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  expect(res.status).toBe(200);
  expect(JSON.stringify(await res.json())).toContain(SHARED_PATIENT.last);
});
