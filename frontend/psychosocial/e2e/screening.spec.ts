import { expect, test } from '@playwright/test';
import { readFileSync } from 'node:fs';
import { API, assignVia, completeVia, makeClinic, shot, signIn, watch } from './support';

test('physio sends a screener, patient answers, physio reviews and logs a referral', async ({ page, browser, request }) => {
  const c = await makeClinic(request);
  const problems = watch(page);

  // --- physio: send a screener from the patient page -----------------------
  await signIn(page, c.therapistEmail, c.password);
  await expect(page.getByRole('heading', { name: 'Screenings' })).toBeVisible();
  await shot(page, '01-worklist-empty');

  if (page.viewportSize()!.width < 600) {
    await page.getByRole('button', { name: 'Open menu' }).click();
  }
  await page.getByRole('link', { name: 'Patients' }).first().click();
  await page.getByRole('link', { name: new RegExp(`Ritu ${c.patientLast}`) }).click();
  await expect(page.getByRole('heading', { name: `Ritu ${c.patientLast}` })).toBeVisible();
  await page.getByRole('button', { name: 'Send screener' }).first().click();
  const drawer = page.getByRole('dialog', { name: 'Send a screener' });
  await drawer.getByText('PHQ-9').click();
  await drawer.getByText('GAD-7').click();
  await shot(page, '02-assign-drawer');
  await drawer.getByRole('button', { name: 'Create link' }).click();
  const ready = page.getByRole('dialog', { name: 'Send the link' });
  await expect(ready.getByText('Link ready')).toBeVisible();
  const wa = await ready.getByRole('link', { name: 'Send on WhatsApp' }).getAttribute('href');
  expect(wa).toMatch(/^https:\/\/wa\.me\/919876543210\?text=/);
  const url = await ready.getByLabel('Patient link').inputValue();
  expect(url).toMatch(/\/screener\/[A-Za-z0-9_-]{40,}$/);
  await shot(page, '03-link-ready');
  await ready.getByRole('button', { name: 'Close' }).click();

  // --- patient: answer on their own device ---------------------------------
  const patientCtx = await browser.newContext({ viewport: page.viewportSize()! });
  const p = await patientCtx.newPage();
  const patientProblems = watch(p);
  await p.goto(url);
  await expect(p.getByRole('heading', { name: 'Before you start' })).toBeVisible();
  await expect(p.getByText(c.patientLast)).toHaveCount(0); // no identity on the public page
  await shot(p, '04-consent');
  await expect(p.getByRole('button', { name: 'Continue' })).toBeDisabled();
  await p.getByText('I have read this and I agree').click();
  await p.getByRole('button', { name: 'Continue' }).click();

  await expect(p.getByRole('heading', { name: 'How you have been feeling' })).toBeVisible();
  await shot(p, '05-intro');
  await p.getByRole('button', { name: 'Start' }).click();

  // PHQ-9: 2,1,1,1,1,0,0,0 then item 9 = 1 ("Several days") -> total 7, risk flag
  const phq = [2, 1, 1, 1, 1, 0, 0, 0, 1];
  const labels = ['Not at all', 'Several days', 'More than half the days', 'Nearly every day'];
  for (let i = 0; i < phq.length; i++) {
    await expect(p.getByText(`Question ${i + 1} of 9`)).toBeVisible();
    if (i === 0) await shot(p, '06-question');
    await p.getByRole('radio', { name: labels[phq[i]] }).click();
    if (i === 3) {
      // Resume: reload mid-way, answers are already on the server.
      await expect(p.getByText('All answers saved')).toBeVisible();
      await p.getByRole('button', { name: 'Next' }).click();
      await expect(p.getByText('Question 5 of 9')).toBeVisible();
      await expect(p.getByText('All answers saved')).toBeVisible();
      await p.reload();
      await expect(p.getByText('Question 5 of 9')).toBeVisible();
      continue;
    }
    await p.getByRole('button', { name: 'Next' }).click();
  }
  await expect(p.getByText('One last, optional question')).toBeVisible();
  await p.getByRole('button', { name: 'Skip this question' }).click();
  await expect(p.getByRole('heading', { name: 'All questions answered' })).toBeVisible();
  await p.getByRole('button', { name: 'Send answers' }).click();

  await expect(p.getByRole('heading', { name: 'Thank you, that part is done' })).toBeVisible();
  await expect(p.getByRole('heading', { name: "You don't have to face this alone" })).toBeVisible();
  await expect(p.getByRole('link', { name: 'Call 14416' })).toHaveAttribute('href', 'tel:14416');
  await shot(p, '07-between-support');
  await p.getByRole('button', { name: 'Continue' }).click();
  await p.getByRole('button', { name: 'Start' }).click();
  for (let i = 0; i < 7; i++) {
    await p.getByRole('radio', { name: 'Not at all' }).click();
    await p.getByRole('button', { name: /Next|Finish/ }).click();
  }
  await p.getByRole('button', { name: 'Skip this question' }).click();
  await p.getByRole('button', { name: 'Send answers' }).click();
  await expect(p.getByRole('heading', { name: 'Thank you', exact: true })).toBeVisible();
  await expect(p.getByText(/may help to talk things through/)).toBeVisible();
  await expect(p.getByText(/\b7\b/)).toHaveCount(0); // never shows the score
  await shot(p, '08-done');

  // Nothing went wrong during the real flow (checked before the deliberate
  // 409 below, so a stray conflict mid-flow would still fail the test).
  expect(patientProblems).toEqual([]);
  await p.goto(url);
  await expect(p.getByRole('heading', { name: 'You have already answered these questions' })).toBeVisible();
  await patientCtx.close();

  // --- physio: worklist shows the risk first, then the result --------------
  await page.goto('/sessions');
  const row = page.getByRole('link', { name: `Ritu ${c.patientLast}` }).first();
  await expect(row).toBeVisible();
  await expect(page.getByText('Risk answer').first()).toBeVisible();
  await shot(page, '09-worklist-attention');
  await row.click();
  await expect(page.getByRole('alert').filter({ hasText: 'Thoughts of self-harm reported' })).toBeVisible();
  await expect(page.getByText('"Several days"').or(page.getByText('“Several days”'))).toBeVisible();
  await expect(page.getByText('7', { exact: true }).first()).toBeVisible();
  await expect(page.getByRole('img', { name: 'Mild, band 2 of 5' })).toBeVisible();
  await shot(page, '10-result');

  await page.getByLabel('Record what you did').selectOption('referred_psychologist');
  await page.getByLabel('Note (optional)').fill('Discussed in clinic, referred to Dr Iyer.');
  await page.getByRole('button', { name: 'Save action' }).click();
  await expect(page.getByRole('listitem').filter({ hasText: 'Referred to psychologist' })).toBeVisible();
  await expect(page.getByText('Discussed in clinic, referred to Dr Iyer.')).toBeVisible();
  await shot(page, '11-referral-logged');

  expect(problems).toEqual([]);
});

test('admin manages access and cannot open individual results', async ({ page, request }) => {
  const c = await makeClinic(request);
  await assignVia(request, c.therapistToken, c.patientId, ['phq9']);
  const problems = watch(page, [403]);

  await signIn(page, c.adminEmail, c.password);
  await expect(page.getByText("You don't have access to screening results")).toBeVisible();
  if (page.viewportSize()!.width < 600) await page.getByRole('button', { name: 'Open menu' }).click();
  await expect(page.getByRole('link', { name: 'Screenings' })).toHaveCount(0);
  await page.getByRole('link', { name: 'Access' }).click();
  await expect(page.getByText('Arjun Mehta')).toBeVisible();
  const send = page.getByRole('switch', { name: 'Send screeners' });
  await expect(send).toHaveAttribute('aria-checked', 'true');
  await shot(page, '12-access');
  await send.click();
  await page.getByRole('button', { name: 'Save' }).click();
  await expect(page.getByText('Access updated for Arjun Mehta')).toBeVisible();

  // The switch really revoked it: the therapist can no longer send links.
  const res = await request.post(`${API}/patients/${c.patientId}/psychosocial/sessions`, {
    headers: { Authorization: `Bearer ${c.therapistToken}` },
    data: { instruments: ['gad7'] },
  });
  expect(res.status()).toBe(403);
  expect(problems.filter((x) => !x.includes('http 403') && !x.includes('http 404') && !x.includes('http 422'))).toEqual([]);
});

test('invalid link shows a calm error', async ({ page }) => {
  const problems = watch(page, [404]);
  await page.goto(`/screener/${'x'.repeat(43)}`);
  await expect(page.getByRole('heading', { name: 'This link is not valid' })).toBeVisible();
  await shot(page, '13-invalid-link');
  expect(problems).toEqual([]);
});

test('admin deletes a patient\'s screening data on request', async ({ page, request }) => {
  const c = await makeClinic(request);
  // One completed PHQ-9 (through the public API) and one open GAD-7 link.
  const token = (await assignVia(request, c.therapistToken, c.patientId, ['phq9'])).split('/').pop()!;
  const screener = `${API}/screener/${token}`;
  const state = await (await request.get(screener)).json();
  expect((await request.post(`${screener}/consent`, { data: { text_version: state.data.consent.text_version } })).ok()).toBeTruthy();
  for (let n = 1; n <= 9; n++) {
    const res = await request.post(`${screener}/answers`, { data: { instrument_id: 'phq9', item_id: `phq9_${n}`, value: 0 } });
    expect(res.ok()).toBeTruthy();
  }
  expect((await request.post(`${screener}/submit`, { data: { instrument_id: 'phq9' } })).ok()).toBeTruthy();
  const openToken = (await assignVia(request, c.therapistToken, c.patientId, ['gad7'])).split('/').pop()!;
  const problems = watch(page);

  await signIn(page, c.adminEmail, c.password);
  if (page.viewportSize()!.width < 600) await page.getByRole('button', { name: 'Open menu' }).click();
  await page.getByRole('link', { name: 'Patients' }).first().click();
  await page.getByRole('link', { name: new RegExp(`Ritu ${c.patientLast}`) }).click();
  await expect(page.getByText('2 questionnaires, 2 links, 0 referral notes and 1 consent record')).toBeVisible();
  await shot(page, '14-delete-panel');

  await page.getByRole('button', { name: 'Delete screening data' }).click();
  const drawer = page.getByRole('dialog', { name: 'Delete screening data' });
  await expect(drawer.getByText('This cannot be undone.')).toBeVisible();
  const confirm = drawer.getByRole('button', { name: 'Delete for good' });
  await expect(confirm).toBeDisabled();
  await drawer.getByLabel('Type DELETE to confirm').fill('delete');
  await expect(confirm).toBeDisabled();
  await drawer.getByLabel('Type DELETE to confirm').fill('DELETE');
  await expect(confirm).toBeEnabled();
  await shot(page, '15-delete-confirm');
  await confirm.click();

  await expect(page.getByText(`Screening data for Ritu ${c.patientLast} has been deleted.`)).toBeVisible();
  await expect(page.getByText('There is no screening data to delete for this patient.')).toBeVisible();
  await shot(page, '16-deleted');

  // Really gone: both links are dead and the counts are zero.
  expect((await request.get(`${API}/screener/${token}`)).status()).toBe(404);
  expect((await request.get(`${API}/screener/${openToken}`)).status()).toBe(404);
  const after = await (
    await request.get(`${API}/patients/${c.patientId}/psychosocial/data`, {
      headers: { Authorization: `Bearer ${c.adminToken}` },
    })
  ).json();
  expect(after.data).toMatchObject({ links: 0, screeners: 0, referral_actions: 0, consent_records: 0 });
  expect(problems).toEqual([]);
});

test('physio sees the score trend and downloads the PDF summary', async ({ page, request }) => {
  const c = await makeClinic(request);
  await completeVia(request, await assignVia(request, c.therapistToken, c.patientId, ['phq9']), 'phq9', [2, 2, 2, 2, 2, 1, 1, 1, 0]);
  await completeVia(request, await assignVia(request, c.therapistToken, c.patientId, ['phq9']), 'phq9', [1, 1, 1, 1, 0, 0, 1, 0, 0]);
  const problems = watch(page);

  await signIn(page, c.therapistEmail, c.password);
  await page.goto(`/patients/${c.patientId}`);
  await expect(page.getByRole('heading', { name: 'Score trend' })).toBeVisible();
  await expect(page.getByRole('img', { name: 'PHQ-9: 2 results from 13 to 5, latest 5, Mild.' })).toBeVisible();
  // The chart may scroll inside its card on a phone, but the page must not.
  // Compare with the configured viewport: on a mobile viewport a too-wide page
  // zooms out, which widens window.innerWidth along with it.
  const pageWidth = await page.evaluate(() => document.documentElement.scrollWidth);
  expect(pageWidth).toBeLessThanOrEqual(page.viewportSize()!.width);
  await shot(page, '17-trend');

  const [download] = await Promise.all([
    page.waitForEvent('download'),
    page.getByRole('button', { name: 'PDF summary' }).click(),
  ]);
  expect(download.suggestedFilename()).toMatch(new RegExp(`^screening-summary-ritu-sharma${c.patientLast.slice(6).toLowerCase()}-\\d{4}-\\d{2}-\\d{2}\\.pdf$`));
  const bytes = readFileSync(await download.path());
  expect(bytes.subarray(0, 4).toString()).toBe('%PDF');
  expect(problems).toEqual([]);
});

test('physio repeats a screener, sees it due again and sends it from the Due list', async ({ page, request }) => {
  const c = await makeClinic(request);
  const problems = watch(page);
  await signIn(page, c.therapistEmail, c.password);
  await page.goto(`/patients/${c.patientId}`);

  // Send PHQ-9 set to repeat every 4 weeks.
  await page.getByRole('button', { name: 'Send screener' }).first().click();
  const drawer = page.getByRole('dialog', { name: 'Send a screener' });
  await drawer.getByText('PHQ-9').click();
  await drawer.getByLabel('Repeat').selectOption({ label: 'Every 4 weeks' });
  await shot(page, '18-repeat');
  await drawer.getByRole('button', { name: 'Create link' }).click();
  await page.getByRole('dialog', { name: 'Send the link' }).getByRole('button', { name: 'Close' }).click();
  const schedule = page.getByRole('listitem').filter({ hasText: 'every 4 weeks' });
  await expect(schedule).toContainText('Link sent, waiting for the patient');

  // The link is cancelled before the patient starts: the screener is due again.
  await page.getByRole('button', { name: 'Cancel screener' }).click();
  await expect(page.getByRole('status').filter({ hasText: 'PHQ-9 is due again' })).toBeVisible();
  await expect(schedule).toContainText('Due since');

  // It shows in the clinic's Due list.
  await page.goto('/sessions');
  await page.getByRole('button', { name: 'Due again' }).click();
  const row = page.getByRole('link', { name: new RegExp(`Ritu ${c.patientLast}`) });
  await expect(row).toContainText('PHQ-9 every 4 weeks');
  await shot(page, '19-due-list');
  await row.click();

  // One click sends the due screener, already ticked.
  await page.getByRole('button', { name: 'Send due screeners' }).click();
  const again = page.getByRole('dialog', { name: 'Send a screener' });
  await expect(again.getByRole('checkbox', { name: /PHQ-9/ })).toBeChecked();
  await expect(again.getByRole('checkbox', { name: /GAD-7/ })).not.toBeChecked();
  await again.getByRole('button', { name: 'Create link' }).click();
  await expect(page.getByRole('dialog', { name: 'Send the link' }).getByText('Link ready')).toBeVisible();
  await page.getByRole('dialog', { name: 'Send the link' }).getByRole('button', { name: 'Close' }).click();
  await expect(schedule).toContainText('Link sent, waiting for the patient');
  await expect(page.getByRole('status').filter({ hasText: 'due again' })).toHaveCount(0);

  // Stopping the repeat removes it.
  await page.getByRole('button', { name: 'Stop repeating PHQ-9' }).click();
  await expect(page.getByText('Repeat stopped.')).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Repeat schedule' })).toHaveCount(0);
  expect(problems).toEqual([]);
});

test('admin sets a default repeat that prefills the send form and never overrides a running repeat', async ({ page, browser, request }) => {
  const c = await makeClinic(request);
  const problems = watch(page, [403]);

  // --- admin: Settings page -------------------------------------------------
  await signIn(page, c.adminEmail, c.password);
  if (page.viewportSize()!.width < 600) await page.getByRole('button', { name: 'Open menu' }).click();
  await page.getByRole('link', { name: 'Settings' }).click();
  await expect(page.getByRole('heading', { name: 'Settings' })).toBeVisible();
  await expect(page.getByText('PHQ-9: referral from Moderate (10 or more, out of 27)')).toBeVisible();
  await expect(page.getByText('DASS-21 Anxiety: referral from Severe (15 or more, out of 42)')).toBeVisible();
  await expect(page.getByText(/Question 9:/)).toBeVisible();
  await expect(page.getByText('Fixed', { exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Save defaults' })).toBeDisabled();

  await page.getByLabel('PHQ-9', { exact: true }).selectOption({ label: 'Every 4 weeks' });
  await page.getByLabel('GAD-7', { exact: true }).selectOption({ label: 'Every 8 weeks' });
  await page.getByRole('button', { name: 'Save defaults' }).click();
  await expect(page.getByText('Default repeat saved.')).toBeVisible();
  await expect(page.getByText('by Neha Kapoor')).toHaveCount(2);
  await expect(page.getByLabel('PHQ-9', { exact: true })).toHaveValue('4');
  await shot(page, '20-settings');
  expect(problems.filter((x) => !x.includes('http 403'))).toEqual([]);

  // --- physio: the send form starts at the clinic default -------------------
  const ctx = await browser.newContext({
    viewport: page.viewportSize()!,
    baseURL: test.info().project.use.baseURL,
    timezoneId: test.info().project.use.timezoneId,
  });
  const physio = await ctx.newPage();
  const physioProblems = watch(physio);
  await signIn(physio, c.therapistEmail, c.password);
  await physio.goto(`/patients/${c.patientId}`);
  await physio.getByRole('button', { name: 'Send screener' }).first().click();
  const drawer = physio.getByRole('dialog', { name: 'Send a screener' });
  const repeat = drawer.getByLabel('Repeat');
  await expect(repeat).toHaveValue('');
  await drawer.locator('label').filter({ hasText: 'PHQ-9' }).click();
  await expect(repeat).toHaveValue('4');
  await expect(drawer.getByText('Clinic default for PHQ-9: every 4 weeks.')).toBeVisible();
  await drawer.locator('label').filter({ hasText: 'GAD-7' }).click();
  await expect(repeat).toHaveValue('');
  await expect(drawer.getByText(/Clinic defaults differ \(PHQ-9 every 4 weeks, GAD-7 every 8 weeks\)/)).toBeVisible();
  await drawer.locator('label').filter({ hasText: 'GAD-7' }).click();
  await expect(repeat).toHaveValue('4');
  await shot(physio, '21-default-prefill');
  await drawer.getByRole('button', { name: 'Create link' }).click();
  await physio.getByRole('dialog', { name: 'Send the link' }).getByRole('button', { name: 'Close' }).click();
  const schedule = physio.getByRole('listitem').filter({ hasText: 'every 4 weeks' });
  await expect(schedule).toContainText('Link sent, waiting for the patient');

  // The admin changes the default later. The running repeat must not follow it.
  const put = await request.put(`${API}/psychosocial/settings/phq9`, {
    headers: { Authorization: `Bearer ${c.adminToken}` },
    data: { default_repeat_weeks: 2 },
  });
  expect(put.status()).toBe(200);

  await physio.getByRole('button', { name: 'Cancel screener' }).click();
  await expect(physio.getByRole('status').filter({ hasText: 'PHQ-9 is due again' })).toBeVisible();
  await physio.reload();
  await physio.getByRole('button', { name: 'Send due screeners' }).click();
  const again = physio.getByRole('dialog', { name: 'Send a screener' });
  await expect(again.getByText('Already repeating for this patient: PHQ-9 every 4 weeks.', { exact: false })).toBeVisible();
  await expect(again.getByLabel('Repeat')).toHaveValue('');
  await shot(physio, '22-running-repeat');
  await again.getByRole('button', { name: 'Create link' }).click();
  await physio.getByRole('dialog', { name: 'Send the link' }).getByRole('button', { name: 'Close' }).click();
  await expect(schedule).toContainText('Link sent, waiting for the patient');
  await expect(physio.getByRole('listitem').filter({ hasText: 'every 2 weeks' })).toHaveCount(0);
  expect(physioProblems).toEqual([]);
  await ctx.close();
});

test('admin sees anonymised statistics with small groups hidden and exports CSV', async ({ page, request }) => {
  const c = await makeClinic(request);
  const admin = { Authorization: `Bearer ${c.adminToken}` };
  const problems = watch(page, [403]);

  // Five patients answer PHQ-9 with no symptoms.
  const ids: string[] = [];
  for (let n = 0; n < 6; n++) {
    const res = await request.post(`${API}/patients`, { headers: admin, data: { first_name: 'Stat', last_name: `Case${n}` } });
    expect(res.ok()).toBeTruthy();
    ids.push(((await res.json()) as { data: { id: string } }).data.id);
  }
  for (const id of ids.slice(0, 5)) {
    const path = await assignVia(request, c.therapistToken, id, ['phq9']);
    await completeVia(request, path, 'phq9', [0, 0, 0, 0, 0, 0, 0, 0, 0]);
  }

  await signIn(page, c.adminEmail, c.password);
  if (page.viewportSize()!.width < 600) await page.getByRole('button', { name: 'Open menu' }).click();
  await page.getByRole('link', { name: 'Reports' }).click();
  await expect(page.getByRole('heading', { name: 'Reports' })).toBeVisible();
  const phq = page.locator('div.rounded-2xl').filter({ has: page.getByRole('heading', { name: 'PHQ-9', exact: true }) });
  const band = (label: string) =>
    phq.getByRole('row').filter({ has: page.getByRole('rowheader', { name: label, exact: true }) });
  await expect(phq).toContainText('5 completed');
  await expect(phq).toContainText('Referral recommended: 0 of 5 (0%)');
  await expect(band('None-minimal')).toContainText('5');
  const gad = page.locator('div.rounded-2xl').filter({ has: page.getByRole('heading', { name: 'GAD-7', exact: true }) });
  await expect(gad).toContainText('None completed in this period.');

  // A sixth patient scores Moderate: one person would stand out, so it is hidden with its partner.
  const path = await assignVia(request, c.therapistToken, ids[5], ['phq9']);
  await completeVia(request, path, 'phq9', [2, 2, 2, 2, 2, 2, 0, 0, 0]);
  await page.reload();
  await expect(phq).toContainText('6 completed');
  await expect(phq).toContainText('Referral recommended: Hidden to protect a small group');
  await expect(band('None-minimal')).toContainText('Hidden');
  await expect(band('Moderate')).toContainText('Hidden');
  await expect(band('Moderately severe')).toContainText('0');
  await shot(page, '23-reports');

  // Filters: one screener, then a period with nothing in it.
  await page.getByLabel('Screener').selectOption({ label: 'PHQ-9' });
  await expect(page.getByRole('heading', { name: 'GAD-7', exact: true })).toHaveCount(0);
  await page.getByLabel('From').fill('2026-01-01');
  await page.getByLabel('To').fill('2026-01-31');
  await expect(phq).toContainText('0 completed');

  // CSV of the same period and screener.
  await page.getByLabel('To').fill(new Date().toLocaleDateString('en-CA', { timeZone: 'Asia/Kolkata' }));
  await expect(phq).toContainText('6 completed');
  const [download] = await Promise.all([page.waitForEvent('download'), page.getByRole('button', { name: 'Export CSV' }).click()]);
  expect(download.suggestedFilename()).toMatch(/^screening-statistics-2026-01-01-to-\d{4}-\d{2}-\d{2}\.csv$/);
  const csv = readFileSync((await download.path())!, 'utf8');
  expect(csv).toContain('PHQ-9,,Completed sessions,6');
  expect(csv).toContain('PHQ-9,PHQ-9,Band: Moderate,hidden');
  expect(csv).not.toContain('GAD-7');
  expect(csv).not.toContain('Stat');
  expect(problems.filter((x) => !x.includes('http 403'))).toEqual([]);

  // A physio has no Reports and no statistics.
  const res = await request.get(`${API}/psychosocial/aggregates`, { headers: { Authorization: `Bearer ${c.therapistToken}` } });
  expect(res.status()).toBe(403);
});
