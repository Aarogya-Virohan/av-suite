#!/usr/bin/env node
/*
 * U7 gate. Run after `next build`:
 *   node scripts/check-bundle.mjs http   -> no mock code or demo data anywhere in the build
 *   node scripts/check-bundle.mjs mock   -> the mock IS there (sanity check of the gate itself)
 * Both modes also fail on anything that looks like a secret.
 */
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join } from 'node:path';

const mode = process.argv[2];
if (mode !== 'http' && mode !== 'mock') {
  console.error('usage: check-bundle.mjs http|mock');
  process.exit(2);
}

// Strings that exist only in the mock adapter / seed data.
const MOCK_MARKERS = ['@av-console.mock', 'mockNeedsEnrolment', 'av-control-center.mock-state'];
// Things that must never reach a browser bundle.
const SECRET_PATTERNS = [
  /PLATFORM_MFA_KEY/,
  /JWT_SECRET/,
  /SUPABASE_(SECRET|SERVICE)/i,
  /-----BEGIN [A-Z ]*PRIVATE KEY-----/,
  /\bsk_(live|test)_[A-Za-z0-9]{10,}/,
  /\bAKIA[0-9A-Z]{16}\b/,
  /postgres(ql)?(\+asyncpg)?:\/\/[^\s"'`]+:[^\s"'`@]+@/,
];

function* files(dir) {
  for (const name of readdirSync(dir)) {
    const path = join(dir, name);
    const info = statSync(path);
    if (info.isDirectory()) yield* files(path);
    else if (/\.(js|mjs|cjs|html|json|txt|css)$/.test(name) && !/\.map$/.test(name)) yield path;
  }
}

const roots = ['.next/static', '.next/server'].filter((dir) => {
  try {
    return statSync(dir).isDirectory();
  } catch {
    return false;
  }
});
if (roots.length === 0) {
  console.error('No .next build found. Run `next build` first.');
  process.exit(2);
}

const mockHits = new Set();
const secretHits = [];
let scanned = 0;
for (const root of roots) {
  for (const file of files(root)) {
    // The server build also holds Next's own config (build manifests): skip env echo files.
    const text = readFileSync(file, 'utf8');
    scanned += 1;
    for (const marker of MOCK_MARKERS) if (text.includes(marker)) mockHits.add(`${marker} in ${file}`);
    for (const pattern of SECRET_PATTERNS) if (pattern.test(text)) secretHits.push(`${pattern} in ${file}`);
  }
}

let failed = false;
if (secretHits.length > 0) {
  failed = true;
  console.error('FAIL: secret-like text in the build:\n  ' + secretHits.join('\n  '));
}
if (mode === 'http' && mockHits.size > 0) {
  failed = true;
  console.error('FAIL: mock code or demo data is in an http build:\n  ' + [...mockHits].slice(0, 10).join('\n  '));
}
if (mode === 'mock' && mockHits.size === 0) {
  failed = true;
  console.error('FAIL: mock build does not contain the mock (gate check is not testing anything)');
}
if (failed) process.exit(1);
console.log(`OK (${mode}): ${scanned} files scanned, ${mode === 'http' ? 'no mock code' : 'mock present as expected'}, no secret-like text.`);
