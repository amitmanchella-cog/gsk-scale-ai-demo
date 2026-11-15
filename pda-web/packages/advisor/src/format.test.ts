import { describe, expect, it } from 'vitest';
import { ageRange, categoryLabel, indicationLabel, number, phaseLabel } from './format';

const population = { sex: 'ALL' as const, healthy_volunteers: false, summary: null };

describe('format', () => {
  it('labels indications and phases', () => {
    expect(indicationLabel('type_2_diabetes')).toBe('Type 2 diabetes');
    expect(indicationLabel('copd')).toBe('COPD');
    expect(indicationLabel('gout')).toBe('gout');
    expect(indicationLabel(null)).toBe('Not found');
    expect(phaseLabel('PHASE3')).toBe('Phase 3');
    expect(phaseLabel('PHASE2/PHASE3')).toBe('Phase 2 / Phase 3');
    expect(phaseLabel(null)).toBe('Not found');
  });

  it('describes age ranges with open ends', () => {
    expect(ageRange({ ...population, min_age: 18, max_age: 65 })).toBe('18 to 65 years');
    expect(ageRange({ ...population, min_age: 12, max_age: null })).toBe('12 years and older');
    expect(ageRange({ ...population, min_age: null, max_age: 75 })).toBe('Up to 75 years');
    expect(ageRange({ ...population, min_age: null, max_age: null })).toBe('No age limit found');
  });

  it('labels categories and numbers', () => {
    expect(categoryLabel('hba1c')).toBe('HbA1c');
    expect(categoryLabel('prior_therapy')).toBe('Prior therapy');
    expect(number(1234.5)).toBe('1,235');
    expect(number(0.614, 2)).toBe('0.61');
    expect(number(null)).toBe('n/a');
  });
});
