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

test("06 posture: CRM patient -> report -> PDF -> open it again", async ({ page, context }, info) => {
  // POS-2: a posture report belongs to a CRM patient. The patient is created
  // through the API with an age (a patient without one cannot be assessed).
  const token = await apiToken();
  const created = await fetch(`${T.api}/api/v1/patients`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
    body: JSON.stringify({
      first_name: "Posture",
      last_name: `Smoke ${RUN}`,
      phone: phone(6),
      age: 34,
      gender: "female",
      chief_complaint: "Posture smoke test patient",
    }),
  });
  expect(created.status).toBeLessThan(300);
  const patient = ((await created.json()) as { data?: { id: string }; id?: string });
  const patientId = (patient.data ?? patient).id as string;
  const fullName = `Posture Smoke ${RUN}`;

  await login(page, T.crm);
  await page.goto(`${T.crm}/patients/${patientId}`);
  await shot(page, info, "posture", "CRM patient page with the AI Posture Analysis button");

  const [tool] = await Promise.all([
    context.waitForEvent("page"),
    page.getByRole("link", { name: /AI Posture Analysis/i }).click(),
  ]);
  await tool.locator('input[type="email"], [data-testid="patient-name"]').first().waitFor();
  if (await tool.locator('input[type="email"]').isVisible()) {
    // The posture tool is its own origin outside hub mode: sign in once.
    await tool.locator('input[type="email"]').fill(T.email);
    await tool.locator('input[type="password"]').fill(T.password);
    await tool.locator('button[type="submit"]').click();
  }
  await expect(tool.getByTestId("patient-name")).toHaveText(fullName);
  await expect(tool.getByTestId("patient-locked")).toBeVisible();
  await expect(tool.getByTestId("patient-case-id")).toHaveText(/^[A-Z]{1,3}-\d{6}$/);
  const caseId = (await tool.getByTestId("patient-case-id").textContent()) ?? "";
  await expect(tool.getByTestId("patient-search")).toHaveCount(0);
  await shot(tool, info, "posture", "Posture opened from the CRM: patient filled and locked, CRM ID shown");

  await tool.getByLabel(/height/i).first().fill("170");
  const images = T.postureImages ? readdirSync(T.postureImages).filter((f) => /\.(jpe?g|png)$/i.test(f)).sort() : [];
  test.skip(images.length < 3, "Set E2E_POSTURE_IMAGES to a folder with front / side / back photos of a standing person (sorted names) to run the analysis; without real photos only the patient step is checked.");
  const inputs = tool.locator('input[type="file"]');
  for (let i = 0; i < 3; i++) await inputs.nth(i).setInputFiles(join(T.postureImages, images[i]));
  await shot(tool, info, "posture", "Three photos uploaded");
  await tool.getByRole("button", { name: /continue to landmark check/i }).click();
  await expect(tool.getByText(/landmark/i).first()).toBeVisible({ timeout: 90_000 });
  await shot(tool, info, "posture", "Landmark check");
  // Walk through the three views, then "Confirm Alignment" builds the report.
  const primary = tool.getByRole("button", { name: /^(Next: .* view|Review and confirm|Confirm Alignment)$/ });
  for (let i = 0; i < 8; i++) {
    const label = (await primary.textContent()) ?? "";
    await primary.click();
    if (/Confirm Alignment/.test(label)) break;
  }
  await expect(tool.getByText(/^PT-\d{8}-[0-9A-F]{8}$/).first()).toBeVisible({ timeout: 90_000 });
  await expect(tool.getByText(caseId).first()).toBeVisible();
  await shot(tool, info, "posture", "Report: CRM patient ID shown as the case ID");

  const pdf = tool.waitForEvent("download", { timeout: 60_000 });
  await tool.getByRole("button", { name: /download pdf/i }).click();
  const file = await pdf;
  const saved = join(__dirname, "..", "out", "artifacts", `${info.project.name}-posture-${file.suggestedFilename()}`);
  await file.saveAs(saved);
  expect(readFileSync(saved).subarray(0, 4).toString()).toBe("%PDF");

  // Back to the first step: the report is listed and opens again.
  await tool.getByRole("button", { name: /new assessment/i }).click();
  await expect(tool.getByTestId("previous-reports")).toBeVisible();
  await shot(tool, info, "posture", "Earlier reports of this patient");
  await tool.getByTestId("open-report").first().click();
  await expect(tool.getByTestId("saved-note")).toBeVisible();
  await expect(tool.getByText(caseId).first()).toBeVisible();
  await shot(tool, info, "posture", "Saved report opened again");
  const again = tool.waitForEvent("download", { timeout: 60_000 });
  await tool.getByRole("button", { name: /download pdf/i }).click();
  const second = await again;
  const saved2 = join(__dirname, "..", "out", "artifacts", `${info.project.name}-posture-again-${second.suggestedFilename()}`);
  await second.saveAs(saved2);
  expect(readFileSync(saved2).subarray(0, 4).toString()).toBe("%PDF");
});

test("06b posture: opened directly, a patient is picked, no free text", async ({ page }, info) => {
  await login(page, T.posture);
  await page.goto(`${T.posture}/`);
  await expect(page.getByTestId("patient-search")).toBeVisible();
  await expect(page.getByLabel(/^name/i)).toHaveCount(0);
  await expect(page.getByLabel(/case reference/i)).toHaveCount(0);
  await shot(page, info, "posture", "Posture opened directly: pick a patient of the clinic");
  await page.getByTestId("patient-search").fill(SHARED_PATIENT.last);
  await page.getByTestId("patient-option").first().click();
  await expect(page.getByTestId("patient-card")).toBeVisible();
  await expect(page.getByTestId("patient-locked")).toHaveCount(0);
  await expect(page.getByTestId("patient-change")).toBeVisible();
  await shot(page, info, "posture", "Patient picked (can be changed)");
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
