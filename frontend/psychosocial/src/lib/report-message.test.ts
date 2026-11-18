import { describe, expect, it } from 'vitest';
import { reportMessage } from './whatsapp';

// Founders: no score, band or condition in the chat bubble (S-D-039).
describe('reportMessage', () => {
  const base = { firstName: 'Ritu', clinicName: 'Sunrise Physio', url: 'https://x.test/report/abc', expires: '9 Dec 2026' };

  it('carries only the link and practical notes', () => {
    const text = reportMessage({ ...base, birthYear: true });
    expect(text).toContain('Hi Ritu,');
    expect(text).toContain('https://x.test/report/abc');
    expect(text).toContain('year of birth');
    expect(text).toContain('9 Dec 2026');
    expect(text).not.toMatch(/phq|gad|score|depress|anxi|severe|mood|risk/i);
  });

  it('leaves out the year line when the page will not ask for it', () => {
    expect(reportMessage({ ...base, birthYear: false })).not.toContain('year of birth');
  });
});
