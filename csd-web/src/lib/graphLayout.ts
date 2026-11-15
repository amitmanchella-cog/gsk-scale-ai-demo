import type { StudyGraph } from '../api/types'

export type NodeKind =
  | 'objective'
  | 'endpoint'
  | 'design'
  | 'activity'
  | 'visit'
  | 'standard'
  | 'arm'

export type GraphNode = {
  id: string
  kind: NodeKind
  layer: 'intent' | 'plan'
  title: string
  subtitle: string
  x: number
  y: number
}

export interface GraphEdge {
  id: string
  source: string
  target: string
  /** Element ID that also highlights this edge (a schedule cell), if any. */
  elementId?: string
}

const COLUMN: Record<NodeKind, number> = {
  arm: 0,
  objective: 0,
  endpoint: 1,
  design: 2,
  activity: 3,
  standard: 4,
  visit: 4,
}
const COLUMN_WIDTH = 250
const ROW_HEIGHT = 74

/** Lay the intent graph (left) and the plan graph (right) out in columns. */
export function buildGraph(graph: StudyGraph): { nodes: GraphNode[]; edges: GraphEdge[] } {
  const rows: Record<number, number> = {}
  const nodes: GraphNode[] = []
  const add = (id: string, kind: NodeKind, title: string, subtitle: string) => {
    const column = COLUMN[kind]
    const row = rows[column] ?? 0
    rows[column] = row + 1
    nodes.push({
      id,
      kind,
      layer: kind === 'activity' || kind === 'visit' || kind === 'standard' ? 'plan' : 'intent',
      title,
      subtitle,
      x: column * COLUMN_WIDTH,
      y: row * ROW_HEIGHT,
    })
  }
  const { intent, plan } = graph
  intent.objectives.forEach((o) => add(o.id, 'objective', `${o.level} objective`, o.text))
  intent.arms.forEach((a) => add(a.id, 'arm', 'Arm', `${a.name} (ratio ${a.ratio})`))
  intent.endpoints.forEach((e) =>
    add(e.id, 'endpoint', `${e.level} endpoint`, `${e.name} at Week ${e.timepoint.week}`),
  )
  intent.design_activities.forEach((d) => add(d.id, 'design', 'Design activity', d.name))
  plan.activities.forEach((a) => add(a.id, 'activity', 'Activity', a.name))
  ;[...plan.visits]
    .sort((a, b) => a.day - b.day)
    .forEach((v) => add(v.id, 'visit', 'Visit', `${v.name} (Day ${v.day} ±${v.window})`))
  plan.standards.forEach((s) => add(s.id, 'standard', 'Operational standard', s.name))

  const edges: GraphEdge[] = [
    ...intent.endpoints.map((e) => ({
      id: `${e.objective_id}>${e.id}`,
      source: e.objective_id,
      target: e.id,
    })),
    ...intent.endpoints.map((e) => ({
      id: `${e.id}>${e.design_activity_id}`,
      source: e.id,
      target: e.design_activity_id,
    })),
    ...plan.activities
      .filter((a) => a.design_activity_id)
      .map((a) => ({
        id: `${a.design_activity_id}>${a.id}`,
        source: a.design_activity_id!,
        target: a.id,
      })),
    ...plan.schedule.map((c) => ({
      id: `${c.activity_id}>${c.visit_id}`,
      source: c.activity_id,
      target: c.visit_id,
      elementId: `${c.visit_id}:${c.activity_id}`,
    })),
    ...plan.standards.map((s) => ({
      id: `${s.activity_id}>${s.id}`,
      source: s.activity_id,
      target: s.id,
    })),
  ]
  return { nodes, edges }
}
