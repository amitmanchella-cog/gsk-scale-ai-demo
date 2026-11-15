import type { Operation, StudyGraph, VersionSummary } from '../api/types'

/** Names by element ID, for elements a later version no longer has (a removed visit). */
export type Names = ReadonlyMap<string, string>

/** Add the names of a graph's visits, activities and endpoints to ``names``. */
export function rememberNames(names: Map<string, string>, graph: StudyGraph): void {
  for (const node of [...graph.plan.visits, ...graph.plan.activities, ...graph.intent.endpoints])
    names.set(node.id, node.name)
}

function lookUp(graph: StudyGraph | undefined, id: unknown, names?: Names): string {
  if (typeof id !== 'string') return String(id)
  const node =
    graph?.plan.visits.find((v) => v.id === id) ??
    graph?.plan.activities.find((a) => a.id === id) ??
    graph?.intent.endpoints.find((e) => e.id === id)
  return node ? node.name : (names?.get(id) ?? id)
}

function nested(operation: Operation, key: string): string {
  const value = operation[key] as { name?: string; id?: string; text?: string } | undefined
  return value?.name ?? value?.id ?? '?'
}

/** A one-line, human-readable label for an operation in the version timeline. */
export function describeOperation(
  operation: Operation | null,
  graph?: StudyGraph,
  names?: Names,
): string {
  if (!operation) return 'Reference study loaded'
  const o = operation
  const nameOf = (g: StudyGraph | undefined, id: unknown) => lookUp(g, id, names)
  switch (o.type) {
    case 'MoveVisit':
      return `Move visit ${nameOf(graph, o.visit_id)} to Day ${o.day}`
    case 'SetVisitWindow':
      return `Set window of ${nameOf(graph, o.visit_id)} to ±${o.window} days`
    case 'RemoveVisit':
      return `Remove visit ${nameOf(graph, o.visit_id)}`
    case 'AddVisit':
      return `Add visit ${nested(o, 'visit')}`
    case 'AddActivity':
      return `Add activity ${nested(o, 'activity')}`
    case 'ScheduleActivity':
      return `Schedule ${nameOf(graph, o.activity_id)} at ${nameOf(graph, o.visit_id)}`
    case 'UnscheduleActivity':
      return `Unschedule ${nameOf(graph, o.activity_id)} at ${nameOf(graph, o.visit_id)}`
    case 'AddEndpoint':
      return `Add endpoint ${nested(o, 'endpoint')}`
    case 'ChangeEndpointTiming':
      return `Change timing of ${nameOf(graph, o.endpoint_id)} to Week ${o.week}`
    case 'ChangePrimaryEndpoint':
      return `Make ${nameOf(graph, o.endpoint_id)} the primary endpoint`
    case 'AddArm':
      return `Add arm ${nested(o, 'arm')}`
    case 'AddObjective':
      return `Add objective ${nested(o, 'objective')}`
    case 'AddDesignActivity':
      return `Add design activity ${nested(o, 'design_activity')}`
    default:
      return o.type
  }
}

/** The chain of versions from the root to ``headId``, following parent links. */
export function lineage(versions: VersionSummary[], headId: string): VersionSummary[] {
  const byId = new Map(versions.map((v) => [v.id, v]))
  const chain: VersionSummary[] = []
  let current = byId.get(headId)
  while (current) {
    chain.unshift(current)
    current = current.parent_id ? byId.get(current.parent_id) : undefined
  }
  return chain
}

/** A starting JSON body for the "apply any operation" form. */
export const OPERATION_TEMPLATES: Record<string, Operation> = {
  AddVisit: {
    type: 'AddVisit',
    visit: { id: 'V-W36', name: 'Week 36', day: 253, window: 7, kind: 'treatment', on_site: true },
  },
  MoveVisit: { type: 'MoveVisit', visit_id: 'V-W12', day: 99 },
  SetVisitWindow: { type: 'SetVisitWindow', visit_id: 'V-W12', window: 14 },
  RemoveVisit: { type: 'RemoveVisit', visit_id: 'V-W4' },
  AddActivity: {
    type: 'AddActivity',
    activity: { id: 'A-ECG', name: 'ECG', unit_cost: 60, duration_minutes: 20 },
  },
  ScheduleActivity: { type: 'ScheduleActivity', visit_id: 'V-W12', activity_id: 'A-ECG' },
  UnscheduleActivity: { type: 'UnscheduleActivity', visit_id: 'V-W4', activity_id: 'A-VITALS' },
  AddObjective: {
    type: 'AddObjective',
    objective: { id: 'OBJ-SEC-QOL', level: 'secondary', text: 'To evaluate quality of life' },
  },
  AddDesignActivity: {
    type: 'AddDesignActivity',
    design_activity: { id: 'DA-ECG', name: 'ECG', purpose: 'Cardiac safety' },
  },
  AddEndpoint: {
    type: 'AddEndpoint',
    endpoint: {
      id: 'EP-FEV1-W24',
      name: 'Change from baseline in trough FEV1',
      level: 'secondary',
      objective_id: 'OBJ-PRIM',
      timepoint: { week: 24 },
      design_activity_id: 'DA-SPIRO',
    },
  },
  ChangeEndpointTiming: { type: 'ChangeEndpointTiming', endpoint_id: 'EP-FEV1', week: 14 },
  ChangePrimaryEndpoint: { type: 'ChangePrimaryEndpoint', endpoint_id: 'EP-ACQ5' },
  AddArm: {
    type: 'AddArm',
    arm: { id: 'ARM-DRUG-200', name: 'Drug 200 mg', intervention: 'Drug 200 mg', ratio: 1 },
  },
}
