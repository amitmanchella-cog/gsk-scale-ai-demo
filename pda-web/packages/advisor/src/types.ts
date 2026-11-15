/** Mirrors the response models of pda-api (src/pda_api/schemas.py). */

export type Level = 'low' | 'moderate' | 'high';

export interface Criterion {
  id: string;
  kind: 'inclusion' | 'exclusion';
  text: string;
  category: string;
  parameter: string | null;
  lower: number | null;
  upper: number | null;
}

export interface PlannedCountry {
  country: string;
  sites: number | null;
}

export interface ProtocolDesign {
  title: string | null;
  indication: string | null;
  phase: string | null;
  phase_group: number | null;
  population: {
    min_age: number | null;
    max_age: number | null;
    sex: 'ALL' | 'FEMALE' | 'MALE';
    healthy_volunteers: boolean;
    summary: string | null;
  };
  target_enrollment: number | null;
  planned_countries: PlannedCountry[];
  site_count: number | null;
  criteria: Criterion[];
  warnings: string[];
}

export interface Protocol {
  id: string;
  document: string;
  created_at: string;
  design: ProtocolDesign;
}

export interface SampleProtocol {
  key: string;
  filename: string;
  title: string;
  indication: string | null;
  weak: boolean;
}

export interface DrivingTrial {
  nct_id: string;
  title: string | null;
  detail: string;
}

export interface CriterionScore {
  criterion_id: string;
  kind: 'inclusion' | 'exclusion';
  text: string;
  category: string;
  score: number;
  level: Level;
  basis: 'range' | 'prevalence' | 'burden';
  rationale: string;
  n_compared: number;
  driving_trials: DrivingTrial[];
}

export interface SimilarTrial {
  nct_id: string;
  title: string | null;
  phase: string;
  overall_status: string;
  stop_category: string;
  enrollment: number;
  site_count: number | null;
  duration_months: number;
  accrual_rate_per_site_month: number | null;
  similarity: number;
}

export interface Assessment {
  protocol_id: string;
  overall_score: number;
  red_flags: number;
  summary: {
    n_similar: number;
    median_enrollment: number;
    median_site_count: number | null;
    median_duration_months: number;
    median_accrual_rate_per_site_month: number | null;
    median_criteria_count: number;
  };
  criteria: CriterionScore[];
  similar_trials: SimilarTrial[];
}

export interface CompetingTrial {
  nct_id: string;
  title: string | null;
  phase: string;
  enrollment: number | null;
  sites_in_country: number;
}

export interface CountryCompetition {
  country: string;
  planned_sites: number | null;
  competing_trials: number;
  competing_sites: number;
  crowding: Level;
  trials: CompetingTrial[];
}

export interface CompetingTrials {
  protocol_id: string;
  indication: string;
  countries: CountryCompetition[];
}
