import { expect, test } from '@playwright/test';
import { API, assignVia, makeClinic, shot, signIn, watch } from './support';

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
