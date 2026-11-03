/**
 * WhatsApp click-to-chat link (manual send, per the agreed flow). Phone
 * handling matches the CRM's openWhatsApp: digits only, India code added
 * when missing.
 */
export function whatsappLink(phone: string | null | undefined, text: string): string | null {
  if (!phone) return null;
  const digits = phone.replace(/\D/g, '');
  if (digits.length < 10) return null;
  const withCode = digits.startsWith('91') && digits.length > 10 ? digits : `91${digits.slice(-10)}`;
  return `https://wa.me/${withCode}?text=${encodeURIComponent(text)}`;
}

export function screenerMessage(opts: {
  firstName: string;
  clinicName: string;
  url: string;
  minutes: number;
  expires: string;
}): string {
  return [
    `Hi ${opts.firstName},`,
    `${opts.clinicName} has shared a few short questions about how you have been feeling lately. It takes about ${opts.minutes} minutes and helps us plan your care.`,
    `Please open this link: ${opts.url}`,
    `The link works until ${opts.expires}. Your answers are seen only by your physiotherapist.`,
  ].join('\n\n');
}
