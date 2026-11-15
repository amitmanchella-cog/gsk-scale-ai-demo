import type { Assessment, CompetingTrials, Protocol, SampleProtocol } from './types';

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
