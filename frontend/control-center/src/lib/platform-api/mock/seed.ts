/*
 * Seed data for the mock adapter. Every customer name here is invented.
 * Nothing in this file may hold a patient name, phone or clinical value (P-5).
 *
 * The data is generated from a fixed seed, so every reload and every test
 * sees the same organizations.
 */
import type {
  AccountStatus,
  ClinicType,
  EntitlementStatus,
  Operator,
  OrganizationType,
  ProductCatalogItem,
} from '../types';

/**
 * Mirror of CANONICAL_PRODUCTS in backend core/products.py (key = id, same
 * name, description and category) for the products the console offers.
 * clinical-decision-support is left out on purpose (Onkar, 19 Nov): screens
 * render whatever this list holds, so adding it later is a data change.
 */
export const SEED_CATALOG: ProductCatalogItem[] = [
  {
    key: 'crm',
    name: 'CRM',
    description: 'Patient management, scheduling and clinic operations.',
    category: 'Patient Management',
  },
  {
    key: 'exercise-library',
    name: 'Exercise Library',
    description: 'Clinical exercise resources and structured exercise programs.',
    category: 'Clinical',
  },
  {
    key: 'exercise-prescription',
    name: 'Exercise Prescription',
    description: 'Build and manage personalized exercise programs.',
    category: 'Clinical',
  },
  { key: 'posture-tool', name: 'Posture Tool', description: 'Posture assessment and movement analysis.', category: 'Clinical' },
  {
    key: 'psycho-social-screening',
    name: 'Psycho-social Screening',
    description: 'Screening and tracking for psycho-social factors.',
    category: 'Clinical',
  },
];

export interface SeedOperator extends Operator {
  /** Mock only: whether this operator still has to enrol MFA. */
  readonly mockNeedsEnrolment: boolean;
}

export interface SeedOrganization {
  id: string;
  name: string;
  slug: string;
  type: OrganizationType;
  status: AccountStatus;
  contact_email: string | null;
  contact_phone: string | null;
  created_at: string;
  updated_at: string;
}

export interface SeedClinic {
  id: string;
  organization_id: string;
  name: string;
  slug: string;
  type: ClinicType;
  status: AccountStatus;
  staff_count: number;
  last_activity_at: string | null;
  created_at: string;
}

export interface SeedEntitlement {
  clinic_id: string;
  product_key: string;
  status: EntitlementStatus;
  valid_from: string | null;
  valid_until: string | null;
  updated_at: string;
}

export interface SeedData {
  operators: SeedOperator[];
  organizations: SeedOrganization[];
  clinics: SeedClinic[];
  entitlements: SeedEntitlement[];
}

/** Small deterministic PRNG (mulberry32). */
export function createRng(seed: number): () => number {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/** Deterministic UUID-shaped id from a label, so links stay stable across reloads. */
export function mockId(label: string): string {
  let h1 = 0x811c9dc5;
  let h2 = 0x01000193;
  for (let i = 0; i < label.length; i += 1) {
    const c = label.charCodeAt(i);
    h1 = Math.imul(h1 ^ c, 16777619) >>> 0;
    h2 = Math.imul(h2 ^ c, 2246822519) >>> 0;
  }
  const hex = (n: number) => n.toString(16).padStart(8, '0');
  const a = hex(h1);
  const b = hex(h2);
  const c = hex(Math.imul(h1 ^ h2, 3266489917) >>> 0);
  const d = hex(Math.imul(h2 + h1, 668265263) >>> 0);
  return `${a}-${b.slice(0, 4)}-4${b.slice(5, 8)}-a${c.slice(1, 4)}-${c.slice(4)}${d}`;
}

export function slugify(value: string): string {
  return value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 120);
}

const DAY = 24 * 60 * 60 * 1000;

const NAME_PREFIXES = [
  'Aarohan', 'Sahaj', 'Prana', 'Kinetic', 'Sukoon', 'Nirvaan', 'Chetna', 'Udaan', 'Saarthi', 'Gati',
  'Sanjeevani', 'Arogyam', 'Moksha', 'Tarang', 'Vikas', 'Aashray', 'Pragati', 'Spandan', 'Navya', 'Prerna',
  'Shakti', 'Utkarsh', 'Samarth', 'Dhyan', 'Ojas', 'Sthiti', 'Lakshya', 'Anvaya', 'Sanchar', 'Vega',
];
const CITIES = ['Noida', 'Gurugram', 'Delhi', 'Pune', 'Jaipur', 'Lucknow', 'Indore', 'Chandigarh', 'Dehradun', 'Bhopal'];
const SUFFIX_BY_TYPE: Record<OrganizationType, string> = {
  individual: 'Physio',
  clinic: 'Physiotherapy Clinic',
  chain: 'Rehab Centres',
  franchise: 'Physio Franchise',
  hospital: 'Hospital',
  government: 'District Health Mission',
  partner_platform: 'Health Platform',
};

/** Type mix of the seeded organizations, roughly the expected customer mix. */
const TYPE_PLAN: OrganizationType[] = [
  'clinic', 'individual', 'clinic', 'chain', 'individual', 'clinic', 'franchise', 'clinic', 'hospital', 'individual',
  'clinic', 'chain', 'clinic', 'individual', 'partner_platform', 'clinic', 'government', 'clinic', 'individual', 'chain',
  'clinic', 'franchise', 'individual', 'clinic', 'hospital', 'clinic', 'individual', 'clinic', 'chain', 'clinic',
];

function branchCount(type: OrganizationType, rnd: () => number): number {
  switch (type) {
    case 'individual':
    case 'clinic':
      return 1;
    case 'chain':
      return 2 + Math.floor(rnd() * 4);
    case 'franchise':
      return 4 + Math.floor(rnd() * 5);
    case 'government':
      return 3 + Math.floor(rnd() * 3);
    default:
      return 1 + Math.floor(rnd() * 2);
  }
}

/**
 * Build the seed relative to `now`, so validity windows (expired, future,
 * open-ended) stay meaningful whatever day the console is opened.
 */
export function buildSeed(now: Date = new Date()): SeedData {
  const rnd = createRng(20261119);
  const nowMs = now.getTime();
  const iso = (ms: number) => new Date(ms).toISOString();
  const pick = <T,>(items: readonly T[]) => items[Math.floor(rnd() * items.length)];
  /** 00:00 IST of the day `days` from today, the bound the console itself sends. */
  const istMidnight = (days: number) => {
    const day = new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Kolkata', year: 'numeric', month: '2-digit', day: '2-digit' }).format(now);
    return new Date(Date.parse(`${day}T00:00:00+05:30`) + days * DAY).toISOString();
  };

  const operators: SeedOperator[] = [
    { name: 'Shivank Khare', email: 'shivank@av-console.mock', role: 'owner', mfa: true },
    { name: 'Daman', email: 'daman@av-console.mock', role: 'owner', mfa: true },
    { name: 'Onkar Dureja', email: 'onkar@av-console.mock', role: 'owner', mfa: true },
    { name: 'Support Operator', email: 'support@av-console.mock', role: 'support', mfa: true },
    { name: 'New Support Operator', email: 'new.support@av-console.mock', role: 'support', mfa: false },
  ].map((o, i) => ({
    id: mockId(`operator:${o.email}`),
    email: o.email,
    name: o.name,
    role: o.role as SeedOperator['role'],
    is_active: true,
    mfa_enabled: o.mfa,
    mockNeedsEnrolment: !o.mfa,
    last_login_at: o.mfa ? iso(nowMs - (i + 1) * 3600_000) : null,
    created_at: iso(nowMs - 40 * DAY),
    updated_at: iso(nowMs - 40 * DAY),
  }));

  const organizations: SeedOrganization[] = [];
  const clinics: SeedClinic[] = [];
  const entitlements: SeedEntitlement[] = [];
  const usedSlugs = new Set<string>();

  TYPE_PLAN.forEach((type, index) => {
    const prefix = NAME_PREFIXES[index % NAME_PREFIXES.length];
    const city = pick(CITIES);
    const name = `${prefix} ${SUFFIX_BY_TYPE[type]}`;
    let slug = slugify(name);
    if (usedSlugs.has(slug)) slug = slugify(`${name} ${city}`);
    usedSlugs.add(slug);
    const createdMs = nowMs - Math.floor(10 + rnd() * 120) * DAY;
    const orgStatus: AccountStatus = index === 7 || index === 23 ? 'suspended' : 'active';
    const org: SeedOrganization = {
      id: mockId(`org:${slug}`),
      name,
      slug,
      type,
      status: orgStatus,
      contact_email: rnd() > 0.2 ? `accounts@${slug}.example` : null,
      contact_phone: rnd() > 0.3 ? `+91 9${String(Math.floor(rnd() * 1e9)).padStart(9, '0')}` : null,
      created_at: iso(createdMs),
      updated_at: iso(createdMs + DAY),
    };
    organizations.push(org);

    const count = branchCount(type, rnd);
    for (let b = 0; b < count; b += 1) {
      const branchCity = count === 1 ? city : CITIES[(index + b) % CITIES.length];
      const clinicName = count === 1 ? name : `${prefix} ${branchCity}`;
      const clinicSlug = count === 1 ? slug : slugify(`${slug} ${branchCity} ${b + 1}`);
      const clinicStatus: AccountStatus = orgStatus === 'active' && b === 2 && index % 2 === 1 ? 'suspended' : 'active';
      const clinic: SeedClinic = {
        id: mockId(`clinic:${clinicSlug}`),
        organization_id: org.id,
        name: clinicName,
        slug: clinicSlug,
        type: type === 'individual' ? (rnd() > 0.5 ? 'solo' : 'personal') : 'clinic',
        status: clinicStatus,
        staff_count: type === 'individual' ? 1 : 2 + Math.floor(rnd() * 14),
        last_activity_at: iso(nowMs - Math.floor(rnd() * 9 * DAY)),
        created_at: iso(createdMs + b * 3 * DAY),
      };
      clinics.push(clinic);

      SEED_CATALOG.forEach((product, p) => {
        // CRM for nearly everyone, clinical tools for some. Same tools for
        // every branch of one organization (P-6).
        const roll = createRng(index * 31 + p)();
        if (p > 0 && roll < 0.45) return;
        let validFrom: string | null = iso(createdMs);
        let validUntil: string | null = null;
        let status: EntitlementStatus = 'enabled';
        if (roll > 0.92) validUntil = istMidnight(-5); // expired
        else if (roll > 0.86) validFrom = istMidnight(7); // starts later
        else if (roll > 0.7) validUntil = istMidnight(61); // last day with access: today + 60
        if (roll < 0.05 && p > 0) status = 'disabled';
        entitlements.push({
          clinic_id: clinic.id,
          product_key: product.key,
          status,
          valid_from: validFrom,
          valid_until: validUntil,
          updated_at: iso(createdMs),
        });
      });
    }
  });

  return { operators, organizations, clinics, entitlements };
}
