import { Background, Controls, Handle, Position, ReactFlow } from '@xyflow/react'
import type { Edge, Node, NodeProps } from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import { useMemo } from 'react'
import type { StudyGraph } from '../api/types'
import { buildGraph } from '../lib/graphLayout'
import type { GraphNode } from '../lib/graphLayout'

type ElementNode = Node<GraphNode & { highlighted: boolean }, 'element'>

function ElementNodeView({ data }: NodeProps<ElementNode>) {
  return (
    <div
      className={`graph-node ${data.kind} ${data.layer}${data.highlighted ? ' highlighted' : ''}`}
      data-testid={`graph-node-${data.id}`}
      data-highlighted={data.highlighted}
    >
      <Handle type="target" position={Position.Left} isConnectable={false} />
      <span className="graph-node-kind">
        {data.title} · {data.id}
      </span>
      <span className="graph-node-name">{data.subtitle}</span>
      <Handle type="source" position={Position.Right} isConnectable={false} />
    </div>
  )
}

const nodeTypes = { element: ElementNodeView }

interface Props {
  graph: StudyGraph
  highlight: ReadonlySet<string>
  onSelect?: (elementId: string) => void
}

/** Intent graph (objectives, endpoints, design activities) linked to the plan graph. */
export function GraphView({ graph, highlight, onSelect }: Props) {
  const { nodes, edges } = useMemo(() => {
    const built = buildGraph(graph)
    const nodes: ElementNode[] = built.nodes.map((node) => ({
      id: node.id,
      type: 'element',
      position: { x: node.x, y: node.y },
      data: { ...node, highlighted: highlight.has(node.id) },
      draggable: false,
      connectable: false,
    }))
    const edges: Edge[] = built.edges.map((edge) => {
      const lit =
        (edge.elementId !== undefined && highlight.has(edge.elementId)) ||
        (highlight.has(edge.source) && highlight.has(edge.target))
      return {
        id: edge.id,
        source: edge.source,
        target: edge.target,
        className: lit ? 'highlighted' : undefined,
        animated: lit,
      }
    })
    return { nodes, edges }
  }, [graph, highlight])

  return (
    <div className="graph-view" data-testid="graph-view">
      <div className="graph-legend">
        <span className="legend intent">Intent graph</span>
        <span className="legend plan">Plan graph</span>
        <span className="legend lit">Highlighted</span>
      </div>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        fitView
        minZoom={0.2}
        nodesConnectable={false}
        nodesDraggable={false}
        onNodeClick={(_, node) => onSelect?.(node.id)}
        proOptions={{ hideAttribution: true }}
      >
        <Background />
        <Controls showInteractive={false} />
      </ReactFlow>
    </div>
  )
}
