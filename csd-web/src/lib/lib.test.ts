import { graph, summaries } from '../fixtures'
import { buildGraph } from './graphLayout'
import { OPERATION_TEMPLATES, describeOperation, lineage, rememberNames } from './operations'

describe('describeOperation', () => {
  it('labels the root version', () => {
    expect(describeOperation(null)).toBe('Reference study loaded')
  })

  it('uses element names when the graph is known and IDs otherwise', () => {
    const move = { type: 'MoveVisit', visit_id: 'V-W12', day: 99 }
    expect(describeOperation(move, graph)).toBe('Move visit Week 12 to Day 99')
    expect(describeOperation(move)).toBe('Move visit V-W12 to Day 99')
    expect(
      describeOperation({ type: 'ChangeEndpointTiming', endpoint_id: 'EP-FEV1', week: 14 }, graph),
    ).toBe('Change timing of Change from baseline in trough FEV1 to Week 14')
  })

  it('has a label and a template for every operation type', () => {
    for (const [type, template] of Object.entries(OPERATION_TEMPLATES)) {
      expect(template.type).toBe(type)
      const label = describeOperation(template, graph)
      expect(label).not.toBe(type)
      expect(label).not.toContain('undefined')
      expect(label).not.toContain('?')
    }
    expect(Object.keys(OPERATION_TEMPLATES).length).toBeGreaterThanOrEqual(10)
    expect(describeOperation({ type: 'SomethingNew' })).toBe('SomethingNew')
  })
})

describe('lineage', () => {
  it('follows parent links from the head back to the root', () => {
    expect(lineage(summaries, 'v-1').map((v) => v.id)).toEqual(['v-0', 'v-1'])
    expect(lineage(summaries, 'v-0').map((v) => v.id)).toEqual(['v-0'])
    expect(lineage(summaries, 'missing')).toEqual([])
  })
})

describe('buildGraph', () => {
  const { nodes, edges } = buildGraph(graph)

  it('creates one node per graph element, split into intent and plan', () => {
    expect(nodes.map((n) => n.id).sort()).toEqual(
      ['A-SPIRO', 'A-VITALS', 'ARM-DRUG', 'DA-SPIRO', 'EP-FEV1', 'OBJ-PRIM', 'STD-VITALS', 'V-RAND', 'V-W12'].sort(),
    )
    expect(nodes.find((n) => n.id === 'EP-FEV1')?.layer).toBe('intent')
    expect(nodes.find((n) => n.id === 'V-W12')?.layer).toBe('plan')
    expect(new Set(nodes.map((n) => `${n.x}:${n.y}`)).size).toBe(nodes.length)
  })

  it('orders visits by study day', () => {
    const visits = nodes.filter((n) => n.kind === 'visit')
    expect(visits.map((n) => n.id)).toEqual(['V-RAND', 'V-W12'])
  })

  it('links intent to plan and only references existing nodes', () => {
    const ids = new Set(nodes.map((n) => n.id))
    for (const edge of edges) {
      expect(ids.has(edge.source)).toBe(true)
      expect(ids.has(edge.target)).toBe(true)
    }
    expect(edges.map((e) => e.id)).toEqual(
      expect.arrayContaining(['OBJ-PRIM>EP-FEV1', 'EP-FEV1>DA-SPIRO', 'DA-SPIRO>A-SPIRO', 'A-SPIRO>V-W12']),
    )
    expect(edges.find((e) => e.id === 'A-SPIRO>V-W12')?.elementId).toBe('V-W12:A-SPIRO')
  })
})

describe('names of removed elements', () => {
  it('labels an operation on an element the current graph no longer has', () => {
    const names = new Map<string, string>()
    rememberNames(names, graph)
    const without = { ...graph, plan: { ...graph.plan, visits: [] } }
    const removal = { type: 'RemoveVisit', visit_id: 'V-W12' }
    expect(describeOperation(removal, without)).toBe('Remove visit V-W12')
    expect(describeOperation(removal, without, names)).toBe('Remove visit Week 12')
    expect(describeOperation(removal, undefined, names)).toBe('Remove visit Week 12')
  })
})
