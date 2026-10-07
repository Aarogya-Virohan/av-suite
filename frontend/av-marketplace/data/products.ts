import {
  Activity,
  BrainCircuit,
  ChartNoAxesCombined,
  ClipboardCheck,
  Dumbbell,
  HeartPulse,
  ScanFace,
  Stethoscope,
  type LucideIcon,
} from 'lucide-react';

export const marketplaceCategories = [
  'All',
  'Clinical',
  'Patient Management',
  'Operations',
  'Finance',
  'Analytics',
  'AI & Automation',
  'Communication',
] as const;

export type MarketplaceCategory = (typeof marketplaceCategories)[number];
export type ProductStatus = 'installed' | 'available';

export type PlatformProduct = {
  id: string;
  slug: string;
  name: string;
  description: string;
  launcherDescription?: string;
  overview: string;
  category: Exclude<MarketplaceCategory, 'All'>;
  icon: LucideIcon;
  tone: 'forest' | 'blue' | 'coral' | 'gold' | 'plum' | 'sage';
  status: ProductStatus;
  metadata: string;
  availability?: string;
  capabilities: string[];
  worksWith: string[];
  featured?: boolean;
};

export const platformProducts: PlatformProduct[] = [
  {
    id: 'crm',
    slug: 'crm',
    name: 'CRM',
    description: 'Patient management, scheduling and clinic operations.',
    overview: 'Coordinate each patient relationship, from the first enquiry to follow-up care. CRM brings schedules, notes, and day-to-day clinic work into the shared workspace.',
    category: 'Patient Management',
    icon: Stethoscope,
    tone: 'forest',
    status: 'installed',
    metadata: 'Patient management',
    availability: 'Available in your workspace',
    capabilities: ['Patient directory', 'Appointments and follow-ups', 'Clinical notes', 'Clinic team coordination'],
    worksWith: ['exercise-library', 'exercise-prescription', 'analytics'],
  },
  {
    id: 'exercise-library',
    slug: 'exercise-library',
    name: 'Exercise Library',
    description: 'Clinical exercise resources and structured exercise programs.',
    launcherDescription: 'Clinical exercise resources and programmes for every stage of care.',
    overview: 'A considered library of movement resources for rehabilitation teams. Find exercises by clinical intent and bring relevant options into a patient’s plan.',
    category: 'Clinical',
    icon: Dumbbell,
    tone: 'blue',
    status: 'installed',
    metadata: '420+ guided movements',
    availability: 'Available in your workspace',
    capabilities: ['Exercise Search', 'Program Builder', 'Patient Assignment', 'Exercise Tracking'],
    worksWith: ['crm', 'posture-tool', 'analytics', 'exercise-prescription'],
  },
  {
    id: 'exercise-prescription',
    slug: 'exercise-prescription',
    name: 'Exercise Prescription',
    description: 'Build and manage personalized exercise programs.',
    overview: 'Shape a progressive home program around a patient’s goals, current ability, and clinical plan. Keep the next movement clear between visits.',
    category: 'Clinical',
    launcherDescription: 'Posture assessment and analysis, brought into the care picture.',
    icon: ClipboardCheck,
    tone: 'forest',
    status: 'available',
    metadata: 'Personalized care programs',
    capabilities: ['Program Builder', 'Patient Assignment', 'Progression Planning', 'Exercise Tracking'],
    worksWith: ['crm', 'exercise-library', 'posture-tool', 'analytics'],
    featured: true,
  },
  {
    id: 'posture-tool',
    slug: 'posture-tool',
    name: 'Posture Tool',
    description: 'Posture assessment and movement analysis.',
    overview: 'Capture posture observations and movement changes over time, then bring those findings into the broader patient care context.',
    category: 'Clinical',
    icon: Activity,
    tone: 'coral',
    status: 'available',
    metadata: 'Assessment & monitoring',
    availability: 'Available in your workspace',
    capabilities: ['Guided posture capture', 'Movement analysis', 'Progress comparison', 'Clinical review notes'],
    worksWith: ['crm', 'exercise-library', 'exercise-prescription', 'analytics'],
  },
  {
    id: 'clinical-decision-support',
    slug: 'clinical-decision-support',
    name: 'Clinical Decision Support',
    description: 'Structured clinical insights for better decision-making.',
    overview: 'Add structured clinical prompts and reference points to assessment workflows while keeping clinician judgement at the centre.',
    category: 'Clinical',
    icon: BrainCircuit,
    tone: 'plum',
    status: 'available',
    metadata: 'Clinical workflow support',
    capabilities: ['Structured assessment prompts', 'Decision pathways', 'Clinical reference points', 'Care-plan context'],
    worksWith: ['crm', 'exercise-prescription', 'analytics'],
  },
  {
    id: 'psycho-social-screening',
    slug: 'psycho-social-screening',
    name: 'Psycho-social Screening',
    description: 'Screening and tracking for psycho-social factors.',
    overview: 'Include the wider factors that can influence recovery, confidence, and adherence as part of a thoughtful patient-centred plan.',
    category: 'Clinical',
    icon: HeartPulse,
    tone: 'sage',
    status: 'available',
    metadata: 'Patient context',
    capabilities: ['Guided screening', 'Context tracking', 'Review prompts', 'Care-team visibility'],
    worksWith: ['crm', 'clinical-decision-support', 'analytics'],
  },
  {
    id: 'analytics',
    slug: 'analytics',
    name: 'Analytics',
    description: 'Clinical and operational insights for your workspace.',
    overview: 'Bring operational measures and clinical activity into useful views that help teams understand access, follow-through, and progress.',
    category: 'Analytics',
    icon: ChartNoAxesCombined,
    tone: 'gold',
    status: 'installed',
    metadata: 'Workspace insights',
    launcherDescription: 'Performance and clinical insights for your team.',
    availability: 'Available in your workspace',
    capabilities: ['Clinic activity', 'Follow-up overview', 'Care-plan signals', 'Team performance'],
    worksWith: ['crm', 'exercise-prescription', 'posture-tool'],
  },
];

export function getProductBySlug(slug: string) {
  return platformProducts.find((product) => product.slug === slug);
}

export function getProductNameById(id: string) {
  return platformProducts.find((product) => product.id === id)?.name ?? id;
}