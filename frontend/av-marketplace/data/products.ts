import {
  Activity,
  BrainCircuit,
  ChartNoAxesCombined,
  ClipboardCheck,
  Dumbbell,
  HeartPulse,
  Stethoscope,
  type LucideIcon,
} from 'lucide-react';

import type {
  ActiveProduct,
  InstalledProduct,
  MarketplaceProduct,
} from '../lib/api-types';

export const marketplaceCategories = [
  'All',
  'Clinical',
  'Patient Management',
  'Operations',
  'Finance',
  'AI & Automation',
  'Communication',
  'Other',
] as const;

export type MarketplaceCategory = (typeof marketplaceCategories)[number];
export type ProductTone = 'forest' | 'blue' | 'coral' | 'gold' | 'plum' | 'sage';

interface ProductPresentation {
  category: Exclude<MarketplaceCategory, 'All'>;
  icon: LucideIcon;
  tone: ProductTone;
  metadata: string;
  worksWith: string[];
  featured?: boolean;
}

export interface PlatformProduct {
  key: string;
  name: string;
  description: string;
  category: Exclude<MarketplaceCategory, 'All'>;
  icon: LucideIcon;
  tone: ProductTone;
  metadata: string;
  worksWith: string[];
  installed: boolean;
  enabled: boolean;
  eligible: boolean;
  featured?: boolean;
}

const presentationByKey: Record<string, ProductPresentation> = {
  crm: {
    category: 'Patient Management',
    icon: Stethoscope,
    tone: 'forest',
    metadata: 'Patient management',
    worksWith: ['exercise-library', 'exercise-prescription'],
  },
  'exercise-library': {
    category: 'Clinical',
    icon: Dumbbell,
    tone: 'blue',
    metadata: 'Clinical exercise resources',
    worksWith: ['crm', 'posture-tool', 'exercise-prescription'],
  },
  'exercise-prescription': {
    category: 'Clinical',
    icon: ClipboardCheck,
    tone: 'forest',
    metadata: 'Personalized care programs',
    worksWith: ['crm', 'exercise-library', 'posture-tool'],
    featured: true,
  },
  'posture-tool': {
    category: 'Clinical',
    icon: Activity,
    tone: 'coral',
    metadata: 'Assessment and monitoring',
    worksWith: ['crm', 'exercise-library', 'exercise-prescription'],
  },
  'clinical-decision-support': {
    category: 'Clinical',
    icon: BrainCircuit,
    tone: 'plum',
    metadata: 'Clinical workflow support',
    worksWith: ['crm', 'exercise-prescription'],
  },
  'psycho-social-screening': {
    category: 'Clinical',
    icon: HeartPulse,
    tone: 'sage',
    metadata: 'Patient context',
    worksWith: ['crm', 'clinical-decision-support'],
  },
};

function keyOf(product: MarketplaceProduct | ActiveProduct): string {
  return 'product_key' in product ? product.product_key : product.key;
}

function mapProduct(
  product: MarketplaceProduct | ActiveProduct,
  installedProduct?: InstalledProduct,
): PlatformProduct {
  const key = keyOf(product);
  const presentation = presentationByKey[key];
  const isCatalogProduct = 'product_key' in product;
  const installed = installedProduct !== undefined
    || (isCatalogProduct ? product.installed : true);
  const enabled = installedProduct
    ? installedProduct.status === 'enabled'
    : isCatalogProduct
      ? product.enabled
      : product.status === 'enabled';

  return {
    key,
    name: product.name,
    description: product.description ?? '',
    category: presentation?.category ?? 'Other',
    icon: presentation?.icon ?? Activity,
    tone: presentation?.tone ?? 'forest',
    metadata: presentation?.metadata ?? 'Workspace product',
    worksWith: presentation?.worksWith ?? [],
    installed,
    enabled,
    eligible: isCatalogProduct ? product.workspace_eligible : true,
    featured: presentation?.featured,
  };
}

export function presentMarketplaceProduct(
  product: MarketplaceProduct,
  installedProduct?: InstalledProduct,
): PlatformProduct {
  return mapProduct(product, installedProduct);
}

export function presentActiveProduct(product: ActiveProduct): PlatformProduct {
  return mapProduct(product);
}

export function getProductWorksWith(productKey: string): string[] {
  return presentationByKey[productKey]?.worksWith ?? [];
}

export function getProductIcon(productKey: string): LucideIcon | undefined {
  return presentationByKey[productKey]?.icon;
}