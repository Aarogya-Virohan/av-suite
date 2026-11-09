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
    `The link works until ${opts.expires}. Your answers are seen only by your healthcare provider.`,
  ].join('\n\n');
}

export function reconsentMessage(opts: { firstName: string; clinicName: string; url: string; expires: string }): string {
  return [
    `Hi ${opts.firstName},`,
    `Earlier you chose not to answer ${opts.clinicName}'s short wellbeing questions. If you would like to take part again, you can say so here. If not, you can say no, or simply ignore this message.`,
    `Please open this link: ${opts.url}`,
    `The link works until ${opts.expires}.`,
  ].join('\n\n');
}

// Founders' wording (7 Nov): no scores or condition in the chat bubble.
export function reportMessage(opts: {
  firstName: string;
  clinicName: string;
  url: string;
  expires: string;
  birthYear: boolean;
}): string {
  return [
    `Hi ${opts.firstName},`,
    `Your healthcare provider at ${opts.clinicName} has shared your recent wellness screening report and care notes. Please click here to view it: ${opts.url}`,
    opts.birthYear ? 'For your privacy, the page will ask for your year of birth.' : null,
    `The link works until ${opts.expires}.`,
  ]
    .filter(Boolean)
    .join('\n\n');
}
