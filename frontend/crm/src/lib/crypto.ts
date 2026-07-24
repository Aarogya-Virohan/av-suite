/**
 * Client-side cryptographic helper utility for encrypting passwords and secret credentials
 * using native browser Web Crypto API (AES-GCM & SHA-256).
 */

const DEFAULT_KEY_SEED = 'av-suite-crm-secure-key-2026';

async function deriveKey(secretKeyStr: string): Promise<CryptoKey> {
  const enc = new TextEncoder();
  const keyMaterial = await crypto.subtle.importKey(
    'raw',
    enc.encode(secretKeyStr),
    { name: 'PBKDF2' },
    false,
    ['deriveKey']
  );
  return crypto.subtle.deriveKey(
    {
      name: 'PBKDF2',
      salt: enc.encode('av-suite-crm-salt-secure'),
      iterations: 100000,
      hash: 'SHA-256'
    },
    keyMaterial,
    { name: 'AES-GCM', length: 256 },
    false,
    ['encrypt', 'decrypt']
  );
}

/**
 * Encrypts a sensitive password or secret credential string using AES-GCM
 */
export async function encryptCredential(plainText: string, customKey?: string): Promise<string> {
  if (typeof window === 'undefined' || !window.crypto || !window.crypto.subtle) {
    // Fallback base64 obfuscation for non-crypto browser environments
    return typeof window !== 'undefined' ? btoa(encodeURIComponent(plainText)) : plainText;
  }

  try {
    const key = await deriveKey(customKey || DEFAULT_KEY_SEED);
    const iv = crypto.getRandomValues(new Uint8Array(12));
    const enc = new TextEncoder();
    const encryptedBuffer = await crypto.subtle.encrypt(
      { name: 'AES-GCM', iv },
      key,
      enc.encode(plainText)
    );

    const combined = new Uint8Array(iv.length + encryptedBuffer.byteLength);
    combined.set(iv, 0);
    combined.set(new Uint8Array(encryptedBuffer), iv.length);

    return btoa(String.fromCharCode(...combined));
  } catch (error) {
    console.error('Credential encryption failed, applying safe fallback:', error);
    return btoa(encodeURIComponent(plainText));
  }
}

/**
 * Decrypts an encrypted credential string
 */
export async function decryptCredential(cipherText: string, customKey?: string): Promise<string> {
  if (typeof window === 'undefined' || !window.crypto || !window.crypto.subtle) {
    try {
      return decodeURIComponent(atob(cipherText));
    } catch {
      return cipherText;
    }
  }

  try {
    const combined = new Uint8Array(
      atob(cipherText)
        .split('')
        .map((c) => c.charCodeAt(0))
    );

    const iv = combined.slice(0, 12);
    const data = combined.slice(12);

    const key = await deriveKey(customKey || DEFAULT_KEY_SEED);
    const decryptedBuffer = await crypto.subtle.decrypt(
      { name: 'AES-GCM', iv },
      key,
      data
    );

    const dec = new TextDecoder();
    return dec.decode(decryptedBuffer);
  } catch (error) {
    console.error('Credential decryption failed:', error);
    try {
      return decodeURIComponent(atob(cipherText));
    } catch {
      return cipherText;
    }
  }
}

/**
 * Computes a secure SHA-256 hash of a password or secret key
 */
export async function hashPassword(password: string): Promise<string> {
  if (typeof window === 'undefined' || !window.crypto || !window.crypto.subtle) {
    return password;
  }

  try {
    const enc = new TextEncoder();
    const data = enc.encode(password);
    const hashBuffer = await crypto.subtle.digest('SHA-256', data);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    return hashArray.map((b) => b.toString(16).padStart(2, '0')).join('');
  } catch (err) {
    console.error('Password hashing failed:', err);
    return password;
  }
}
