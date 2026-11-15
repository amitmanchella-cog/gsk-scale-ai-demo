// Shapes returned by csd-api (which serialises the csd-core Pydantic models).

export type Level = 'primary' | 'secondary'

export interface Objective { id: string; level: Level; text: string }
export interface Endpoint {
  id: string
  name: string
  level: Level
  objective_id: string
  timepoint: { week: number }
  design_activity_id: string
}
export interface Estimand {
  id: string
  endpoint_id: string
  population: string
  intercurrent_event_strategy: string
  summary_measure: string
}
export interface DesignActivity { id: string; name: string; purpose: string }
export interface Arm { id: string; name: string; intervention: string; ratio: number }
export interface Visit {
  id: string
  name: string
  day: number
  window: number
  kind: string
  on_site: boolean
}
export interface Activity {
  id: string
  name: string
  unit_cost: number
  duration_minutes: number
  design_activity_id: string | null
}
export interface OperationalStandard {
  id: string
  name: string
  activity_id: string
  applies_to: string
}
export interface StudyGraph {
  title: string
  phase: string
  indication: string
  duration_weeks: number
  intent: {
    objectives: Objective[]
    estimands: Estimand[]
    endpoints: Endpoint[]
    design_activities: DesignActivity[]
    arms: Arm[]
    assignment: { method: string; blinding: string; control: string }
  }
  plan: {
    visits: Visit[]
    activities: Activity[]
    standards: OperationalStandard[]
    schedule: { visit_id: string; activity_id: string }[]
  }
}

export type Operation = { type: string } & Record<string, unknown>

export interface Finding {
  id: string
  type: 'untraced_activity' | 'unmet_endpoint_timepoint' | 'missing_operational_standard'
  severity: 'warning'
  subject_id: string
  message: string
  element_ids: string[]
}

export interface Version {
  id: string
  study_id: string
  parent_id: string | null
  branch: string
  seq: number
  operation: Operation | null
  graph: StudyGraph
  findings: Finding[]
}

export interface VersionSummary {
  id: string
  study_id: string
  parent_id: string | null
  branch: string
  seq: number
  operation: Operation | null
  finding_count: number
}

export interface Branch {
  study_id: string
  name: string
  base_version_id: string | null
  head_version_id: string
}

export interface StudySummary {
  id: string
  title: string
  root_version_id: string
  head_version_id: string
  version_count: number
}

export interface ScheduleGrid {
  visits: { id: string; name: string; day: number; window: number; on_site: boolean }[]
  rows: { activity_id: string; activity_name: string; cells: boolean[] }[]
}
