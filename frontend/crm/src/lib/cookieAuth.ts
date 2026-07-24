// Client-side secure cookies utility helper for CRM authentication

export function setCookie(name: string, value: string, days = 365, sameSite: 'Strict' | 'Lax' | 'None' = 'Strict') {
  if (typeof window === 'undefined') return;
  let expires = '';
  if (days) {
    const date = new Date();
    date.setTime(date.getTime() + days * 24 * 60 * 60 * 1000);
    expires = '; expires=' + date.toUTCString();
  }
  // Secure default flags: SameSite=Strict, Secure (on HTTPS), Path=/
  const secure = window.location.protocol === 'https:' ? '; Secure' : '';
  document.cookie = `${name}=${encodeURIComponent(value)}${expires}; path=/; SameSite=${sameSite}${secure}`;
}

export function getCookie(name: string): string | null {
  if (typeof window === 'undefined') return null;
  const nameEQ = name + '=';
  const ca = document.cookie.split(';');
  for (let i = 0; i < ca.length; i++) {
    let c = ca[i];
    while (c.charAt(0) === ' ') c = c.substring(1, c.length);
    if (c.indexOf(nameEQ) === 0) return decodeURIComponent(c.substring(nameEQ.length, c.length));
  }
  return null;
}

export function deleteCookie(name: string) {
  setCookie(name, '', -1);
}

// -------------------------------------------------------------
// Authentication Token Secure Cookie Storage
// -------------------------------------------------------------

export function setAuthToken(token: string, days = 7) {
  setCookie('crm_auth_token', token, days, 'Strict');
}

export function getAuthToken(): string | null {
  return getCookie('crm_auth_token');
}

export function removeAuthToken() {
  deleteCookie('crm_auth_token');
}
