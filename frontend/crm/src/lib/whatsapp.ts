/**
 * WhatsApp Click-to-Chat Link Utility Helper
 * Formats a phone number and message into a valid wa.me link that opens in a new tab.
 */

export function buildWhatsAppLink(phone: string, message: string): string {
  if (!phone) return '#';
  
  // Extract numeric digits
  let digits = phone.replace(/\D/g, '');
  
  // Enforce 91 country code prefix for 10-digit Indian mobile numbers
  if (digits.length === 10) {
    digits = `91${digits}`;
  } else if (digits.length > 10 && !digits.startsWith('91')) {
    digits = `91${digits}`;
  }

  const encodedMessage = encodeURIComponent(message);
  return `https://wa.me/${digits}?text=${encodedMessage}`;
}

export function openWhatsAppChat(phone: string, message: string): void {
  const url = buildWhatsAppLink(phone, message);
  if (typeof window !== 'undefined' && url !== '#') {
    window.open(url, '_blank', 'noopener,noreferrer');
  }
}
