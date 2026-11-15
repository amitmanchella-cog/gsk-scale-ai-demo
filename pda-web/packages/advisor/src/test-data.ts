import type { Assessment, CompetingTrials, Forecast, Protocol, SampleProtocol, Suggestions, WhatIf } from './types';

export const samples: SampleProtocol[] = [
  { key: 'asthma_phase3', filename: 'asthma_phase3.txt', title: 'Asthma study', indication: 'asthma', weak: false },
  {
    key: 't2d_phase3_weak',
    filename: 't2d_phase3_weak.txt',
    title: 'Diabetes study',
    indication: 'type_2_diabetes',
    weak: true,
  },
];

export const protocol: Protocol = {
  id: 'p-1',
  document: 'weak.txt',
  created_at: '2026-01-01T00:00:00Z',
  design: {
    title: 'Diabetes study',
    indication: 'type_2_diabetes',
    phase: 'PHASE3',
    phase_group: 3,
    population: { min_age: 40, max_age: 60, sex: 'ALL', healthy_volunteers: false, summary: 'Middle-aged adults.' },
    target_enrollment: 900,
    planned_countries: [
      { country: 'United States', sites: 5 },
      { country: 'China', sites: null },
    ],
    site_count: 8,
    criteria: [
      {
        id: 'I1',
        kind: 'inclusion',
        text: 'Aged 40 to 60 years',
        category: 'age',
        parameter: 'age',
        lower: 40,
        upper: 60,
      },
      {
        id: 'E1',
        kind: 'exclusion',
        text: 'Pregnant women',
        category: 'pregnancy',
        parameter: null,
        lower: null,
        upper: null,
      },
    ],
    warnings: [],
  },
};

export const assessment: Assessment = {
  protocol_id: 'p-1',
  overall_score: 61,
  red_flags: 1,
  summary: {
    n_similar: 40,
    median_enrollment: 512,
    median_site_count: 64,
    median_duration_months: 14.2,
    median_accrual_rate_per_site_month: 0.61,
    median_criteria_count: 18,
  },
  criteria: [
    {
      criterion_id: 'E1',
      kind: 'exclusion',
      text: 'Pregnant women',
      category: 'pregnancy',
      score: 10,
      level: 'low',
      basis: 'prevalence',
      rationale: '36 of 40 similar trials have a comparable criterion',
      n_compared: 40,
      driving_trials: [],
    },
    {
      criterion_id: 'I1',
      kind: 'inclusion',
      text: 'Aged 40 to 60 years',
      category: 'age',
      score: 100,
      level: 'high',
      basis: 'range',
      rationale: '40 of 40 similar trials accept a wider range',
      n_compared: 40,
      driving_trials: [{ nct_id: 'NCT00000001', title: 'Trial one', detail: '18 to 80 years' }],
    },
  ],
  similar_trials: [
    {
      nct_id: 'NCT00000001',
      title: 'Trial one',
      phase: 'PHASE3',
      overall_status: 'TERMINATED',
      stop_category: 'low_accrual',
      enrollment: 420,
      site_count: null,
      duration_months: 12.5,
      accrual_rate_per_site_month: null,
      similarity: 0.9,
    },
  ],
};

export const competing: CompetingTrials = {
  protocol_id: 'p-1',
  indication: 'type_2_diabetes',
  countries: [
    {
      country: 'United States',
      planned_sites: 5,
      competing_trials: 31,
      competing_sites: 1240,
      crowding: 'high',
      trials: [
        { nct_id: 'NCT00000009', title: 'Rival', phase: 'PHASE2/PHASE3', enrollment: 300, sites_in_country: 40 },
      ],
    },
    { country: 'Atlantis', planned_sites: null, competing_trials: 0, competing_sites: 0, crowding: 'low', trials: [] },
  ],
};

const cited = (start: number, count: number) =>
  Array.from({ length: count }, (_, index) => `NCT0000010${start + index}`);

export const forecast: Forecast = {
  p50_months: 186,
  p90_months: 1372.4,
  target_enrollment: 900,
  sites: 8,
  ramp_months: 6,
  rate_multiplier: 0.3,
  rate_source: 'similar_trials',
  n_rates: 40,
  median_benchmark_rate: 2.55,
  indication_phase_median_rate: 0.625,
  simulations: 2000,
  seed: 20260115,
  termination_risk: {
    risk: 0.0139,
    level: 'high',
    baseline_share: 0.0035,
    similar_low_accrual: 0,
    n_similar: 40,
    indication_phase_share: 0.0104,
    adjustment: 4,
    trial_ids: ['NCT00000201', 'NCT00000202'],
  },
};

export const suggestions: Suggestions = {
  protocol_id: 'p-1',
  baseline: forecast,
  rejected: 2,
  suggestions: [
    {
      id: 'S5',
      title: 'Add 5 sites in China',
      rationale: 'The draft plans 8 sites; similar trials used a median of 11.',
      change: { kind: 'add_sites', country: 'China', sites: 5 },
      evidence: [
        { metric: 'sites_added', label: 'Sites added', value: 5 },
        { metric: 'country_median_rate', label: 'Median patients per site per month', value: 0.7 },
      ],
      cited_trial_ids: cited(0, 6),
      p50_months_after: 115.7,
      months_saved: 70.3,
    },
    {
      id: 'S3',
      title: 'Relax I4 (BMI) to 18.5 to 40 kg/m2',
      rationale: 'The draft allows BMI 27 to 32 kg/m2 and scores 100 for restrictiveness.',
      change: { kind: 'relax_criterion', criterion_id: 'I4', lower: 18.5, upper: 40 },
      evidence: [{ metric: 'restrictiveness_score', label: 'Restrictiveness score', value: 100 }],
      cited_trial_ids: cited(10, 5),
      p50_months_after: 171,
      months_saved: 15,
    },
  ],
};

export const whatIf: WhatIf = {
  protocol_id: 'p-1',
  baseline: forecast,
  scenario: {
    ...forecast,
    p50_months: 105.9,
    p90_months: 760.2,
    sites: 13,
    termination_risk: { ...forecast.termination_risk, risk: 0.0121 },
  },
  applied: [
    { change: { kind: 'add_sites', country: 'China', sites: 5 }, summary: 'Add 5 sites in China' },
    {
      change: { kind: 'relax_criterion', criterion_id: 'I4', lower: 18.5, upper: 40 },
      summary: 'Relax I4 (BMI) to 18.5 to 40 kg/m2',
    },
  ],
  p50_months_saved: 80.1,
  p90_months_saved: 612.2,
  elapsed_ms: 31.5,
};

/** Stub `fetch` with a path-to-response table. A missing path answers 404. */
export function stubApi(routes: Record<string, { status?: number; body: unknown }>) {
  const calls: { path: string; init?: RequestInit }[] = [];
  const fetchStub = async (input: RequestInfo | URL, init?: RequestInit) => {
    const path = String(input);
    calls.push({ path, init });
    const route = routes[path] ?? { status: 404, body: { detail: 'Not found' } };
    const text = typeof route.body === 'string' ? route.body : JSON.stringify(route.body);
    return new Response(text, { status: route.status ?? 200 });
  };
  globalThis.fetch = fetchStub as typeof fetch;
  return calls;
}
