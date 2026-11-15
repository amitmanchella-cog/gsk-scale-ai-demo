import type { Level, ProtocolDesign } from './types';

const INDICATIONS: Record<string, string> = {
  asthma: 'Asthma',
  copd: 'COPD',
  type_2_diabetes: 'Type 2 diabetes',
};

export function indicationLabel(indication: string | null): string {
  if (!indication) return 'Not found';
  return INDICATIONS[indication] ?? indication;
}

export function phaseLabel(phase: string | null): string {
  if (!phase) return 'Not found';
  return phase
    .split('/')
    .map((part) => part.replace('PHASE', 'Phase '))
    .join(' / ');
}

export function ageRange(population: ProtocolDesign['population']): string {
  const { min_age: min, max_age: max } = population;
  if (min !== null && max !== null) return `${min} to ${max} years`;
  if (min !== null) return `${min} years and older`;
  if (max !== null) return `Up to ${max} years`;
  return 'No age limit found';
}

export function categoryLabel(category: string): string {
  const special: Record<string, string> = { hba1c: 'HbA1c', bmi: 'BMI', egfr: 'eGFR', fev1_pct: 'FEV1', fev1: 'FEV1' };
  if (special[category]) return special[category];
  const text = category.replaceAll('_', ' ');
  return text.charAt(0).toUpperCase() + text.slice(1);
}

export const LEVEL_LABEL: Record<Level, string> = {
  high: 'Red flag',
  moderate: 'Watch',
  low: 'In line',
};

export function number(value: number | null | undefined, digits = 0): string {
  if (value === null || value === undefined) return 'n/a';
  return value.toLocaleString('en-US', { maximumFractionDigits: digits, minimumFractionDigits: digits });
}

export const TRIAL_URL = 'https://clinicaltrials.gov/study/';
