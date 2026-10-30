export const API_BASE = '/api'

// ---- Types mirror docs/uc4/design.md §3–4 (keep in sync with backend app/models.py) ----

export interface Health {
  status: string
  version: string
  data_dir: string
  as_of: string
  row_counts: Record<string, number>
}

export interface Rep {
  rep_id: string
  rep_name: string
  territory_id: string
  region: string | null
  hire_date: string | null
}

export interface Territory {
  territory_id: string
  territory_name: string
  region: string
}

export type Segment = 'A' | 'B' | 'C'
export type Day = 'Mon' | 'Tue' | 'Wed' | 'Thu' | 'Fri'
export const DAYS: Day[] = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri']
export const DAY_NAMES: Record<Day, string> = {
  Mon: 'Monday',
  Tue: 'Tuesday',
  Wed: 'Wednesday',
  Thu: 'Thursday',
  Fri: 'Friday',
}

export interface ScoreFactor {
  name: string
  points: number
  detail: string
}

export interface ScoringRules {
  segment_weights: Record<Segment, number>
  points_per_day: number
  days_cap: number
  open_follow_up_bonus: number
  recent_visit_days: number
  max_score: number
}

export interface HcpView {
  hcp_id: string
  hcp_name: string
  specialty: string
  segment: Segment
  territory_id: string
  last_visit_date: string | null
  days_since_last_visit: number | null
  open_follow_ups: number
  score: number
  reason: string
  factors: ScoreFactor[]
}

export interface HcpFilters {
  specialty?: string
  segment?: Segment | ''
  min_days_since_last_visit?: number | ''
  q?: string
}

export interface HcpListResponse {
  rep: Pick<Rep, 'rep_id' | 'rep_name' | 'territory_id'>
  territory: Territory
  as_of: string
  count: number
  hcps: HcpView[]
}

export interface PlanVisit {
  visit_id: number
  hcp_id: string
  hcp_name: string
  specialty: string
  segment: Segment
  score: number
  reason: string
}

export interface PlanDay {
  day: Day
  date: string
  count: number
  capacity: number
  visits: PlanVisit[]
}

export interface PlanWarning {
  type: 'overdue_segment_a' | 'duplicate'
  hcp_id: string
  hcp_name: string
  days: Day[]
  message: string
}

export interface Plan {
  rep_id: string
  territory_id: string
  week_start: string
  as_of: string
  max_visits_per_day: number
  total_visits: number
  days: PlanDay[]
  warnings: PlanWarning[]
}

export class ApiError extends Error {
  status: number
  detail: string
  constructor(status: number, detail: string) {
    super(detail)
    this.status = status
    this.detail = detail
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, init)
  if (!response.ok) {
    let detail = `${path} failed with HTTP ${response.status}`
    try {
      const body = (await response.json()) as { detail?: unknown }
      if (typeof body.detail === 'string') detail = body.detail
    } catch {
      // keep the generic message
    }
    throw new ApiError(response.status, detail)
  }
  return (await response.json()) as T
}

function query(params: Record<string, string | number | undefined | ''>): string {
  const search = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== '') search.set(key, String(value))
  }
  const s = search.toString()
  return s ? `?${s}` : ''
}

export const fetchHealth = () => request<Health>('/health')
export const fetchReps = () => request<Rep[]>('/reps')
export const fetchScoringRules = () => request<ScoringRules>('/scoring/rules')
export const fetchHcps = (repId: string, filters: HcpFilters = {}) =>
  request<HcpListResponse>(`/reps/${encodeURIComponent(repId)}/hcps${query({ ...filters })}`)
export const fetchPlan = (repId: string) => request<Plan>(`/reps/${encodeURIComponent(repId)}/plan`)
export const addPlanVisit = (repId: string, hcpId: string, day: Day) =>
  request<Plan>(`/reps/${encodeURIComponent(repId)}/plan/visits`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ hcp_id: hcpId, day }),
  })
export const removePlanVisit = (repId: string, visitId: number) =>
  request<Plan>(`/reps/${encodeURIComponent(repId)}/plan/visits/${visitId}`, { method: 'DELETE' })
export const clearPlan = (repId: string) => request<Plan>(`/reps/${encodeURIComponent(repId)}/plan`, { method: 'DELETE' })
export const planExportUrl = (repId: string) => `${API_BASE}/reps/${encodeURIComponent(repId)}/plan/export.csv`
