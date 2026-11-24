import { describe, expect, it } from 'vitest';
import { groupSecret, secretFromOtpauth } from './EnrolmentQr';

describe('enrolment helpers', () => {
  it('reads the setup key from the otpauth link', () => {
    const uri = 'otpauth://totp/AV%20Platform:op%40av.in?secret=JBSWY3DPEHPK3PXP&issuer=AV+Platform&algorithm=SHA1&digits=6&period=30';
    expect(secretFromOtpauth(uri)).toBe('JBSWY3DPEHPK3PXP');
    expect(groupSecret('JBSWY3DPEHPK3PXP')).toBe('JBSW Y3DP EHPK 3PXP');
  });
  it('rejects anything that is not an otpauth link', () => {
    expect(secretFromOtpauth('https://x.in/?secret=ABC')).toBeNull();
    expect(secretFromOtpauth('not a url')).toBeNull();
  });
});
