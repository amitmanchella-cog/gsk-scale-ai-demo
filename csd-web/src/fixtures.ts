// A small synthetic graph for unit tests (the e2e tests use the real API).
import type { Comparison, Draft, Finding, ScheduleGrid, StudyGraph, Version, VersionSummary } from './api/types'

export const graph: StudyGraph = {
  title: 'Synthetic asthma study',
  phase: 'Phase 3',
  indication: 'Asthma',
  duration_weeks: 52,
  intent: {
    objectives: [{ id: 'OBJ-PRIM', level: 'primary', text: 'Lung function' }],
    estimands: [],
    endpoints: [
      {
        id: 'EP-FEV1',
        name: 'Change from baseline in trough FEV1',
        level: 'primary',
        objective_id: 'OBJ-PRIM',
        timepoint: { week: 12 },
        design_activity_id: 'DA-SPIRO',
      },
    ],
    design_activities: [{ id: 'DA-SPIRO', name: 'Spirometry', purpose: 'Trough FEV1' }],
    arms: [{ id: 'ARM-DRUG', name: 'Drug 100 mg', intervention: 'Drug 100 mg', ratio: 1 }],
    assignment: { method: 'randomised', blinding: 'double-blind', control: 'placebo' },
  },
  plan: {
    visits: [
      { id: 'V-W12', name: 'Week 12', day: 85, window: 3, kind: 'treatment', on_site: true },
      { id: 'V-RAND', name: 'Randomisation', day: 1, window: 0, kind: 'randomisation', on_site: true },
    ],
    activities: [
      { id: 'A-SPIRO', name: 'Spirometry', unit_cost: 120, duration_minutes: 45, design_activity_id: 'DA-SPIRO' },
      { id: 'A-VITALS', name: 'Vital signs', unit_cost: 20, duration_minutes: 10, design_activity_id: null },
    ],
    standards: [
      { id: 'STD-VITALS', name: 'Vital signs at every on-site visit', activity_id: 'A-VITALS', applies_to: 'on_site' },
    ],
    schedule: [
      { visit_id: 'V-RAND', activity_id: 'A-SPIRO' },
      { visit_id: 'V-W12', activity_id: 'A-SPIRO' },
      { visit_id: 'V-RAND', activity_id: 'A-VITALS' },
    ],
  },
}

export const grid: ScheduleGrid = {
  visits: [
    { id: 'V-RAND', name: 'Randomisation', day: 1, window: 0, on_site: true },
    { id: 'V-W12', name: 'Week 12', day: 85, window: 3, on_site: true },
  ],
  rows: [
    { activity_id: 'A-SPIRO', activity_name: 'Spirometry', cells: [true, true] },
    { activity_id: 'A-VITALS', activity_name: 'Vital signs', cells: [true, false] },
  ],
}

export const finding: Finding = {
  id: 'unmet_endpoint_timepoint:EP-FEV1',
  type: 'unmet_endpoint_timepoint',
  severity: 'warning',
  subject_id: 'EP-FEV1',
  message: 'Primary endpoint "Change from baseline in trough FEV1" is timed at Week 12 (Day 85).',
  element_ids: ['EP-FEV1', 'DA-SPIRO'],
}

export const summaries: VersionSummary[] = [
  { id: 'v-0', study_id: 's', parent_id: null, branch: 'main', seq: 0, operation: null, finding_count: 0 },
  {
    id: 'v-1',
    study_id: 's',
    parent_id: 'v-0',
    branch: 'main',
    seq: 1,
    operation: { type: 'MoveVisit', visit_id: 'V-W12', day: 99 },
    finding_count: 1,
  },
]

export const version = (id: 'v-0' | 'v-1'): Version => {
  const summary = summaries.find((candidate) => candidate.id === id)!
  return {
    id: summary.id,
    study_id: summary.study_id,
    parent_id: summary.parent_id,
    branch: summary.branch,
    seq: summary.seq,
    operation: summary.operation,
    graph,
    findings: id === 'v-1' ? [finding] : [],
  }
}

export const comparison: Comparison = {
  left: {
    version_id: 'v-0',
    branch: 'main',
    seq: 0,
    score: { visit_count: 7, patient_time_minutes: 640, cost_proxy: 2160 },
    findings: [],
  },
  right: {
    version_id: 'v-b',
    branch: 'fewer-visits',
    seq: 1,
    score: { visit_count: 6, patient_time_minutes: 550, cost_proxy: 1940 },
    findings: [finding],
  },
  delta: { visit_count: -1, patient_time_minutes: -90, cost_proxy: -220 },
  changes: [
    { element_id: 'V-W4', element_type: 'visit', change: 'removed', label: 'Week 4' },
    { element_id: 'EP-ACQ5', element_type: 'endpoint', change: 'changed', label: 'ACQ-5' },
  ],
}

export const draft: Draft = {
  provider: 'template',
  sections: [
    {
      number: '3',
      title: 'Trial Objectives and Associated Estimands',
      sentences: [
        {
          text: 'The primary objective is lung function.',
          element_ids: ['OBJ-PRIM'],
        },
      ],
    },
    {
      number: '5',
      title: 'Trial Design',
      sentences: [
        {
          text: 'This is a Phase 3 study with 2 arms.',
          element_ids: ['ARM-DRUG', 'ARM-PBO'],
        },
      ],
    },
    {
      number: '8',
      title: 'Trial Assessments and Procedures',
      sentences: [
        {
          text: 'Week 12 takes place on site on Day 85 and includes spirometry.',
          element_ids: ['V-W12', 'V-W12:A-SPIRO'],
        },
        {
          text: 'Vital signs is performed at 1 visit: Randomisation.',
          element_ids: ['A-VITALS', 'V-RAND:A-VITALS'],
        },
      ],
    },
  ],
}
