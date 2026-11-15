import { useMemo, useState } from 'react'
import { EndpointsPanel } from './components/EndpointsPanel'
import { FindingsPanel } from './components/FindingsPanel'
import { GraphView } from './components/GraphView'
import { OperationForm } from './components/OperationForm'
import { ScheduleGrid } from './components/ScheduleGrid'
import { VersionTimeline } from './components/VersionTimeline'
import { lineage } from './lib/operations'
import { useStudy } from './useStudy'

type Tab = 'schedule' | 'graph'
const TABS: { id: Tab; label: string }[] = [
  { id: 'schedule', label: 'Schedule of activities' },
  { id: 'graph', label: 'Graph' },
]

const NONE: ReadonlySet<string> = new Set()

export function studyIdFromLocation(search: string): string {
  return new URLSearchParams(search).get('study') ?? 'asthma-ref'
}

export function App() {
  const studyId = studyIdFromLocation(window.location.search)
  const study = useStudy(studyId)
  const [tab, setTab] = useState<Tab>('schedule')
  const [highlight, setHighlight] = useState<ReadonlySet<string>>(NONE)
  const { version, grid, branches, versions } = study

  const branch = branches.find((candidate) => candidate.name === 'main')
  const headId = branch?.head_version_id ?? ''
  const timeline = useMemo(() => lineage(versions, headId), [versions, headId])
  const editable = version !== null && version.id === headId && !study.busy

  return (
    <div className="app">
      <header className="app-header">
        <div>
          <h1>Computable study design</h1>
          <p className="study-title" data-testid="study-title">
            {version ? version.graph.title : 'Loading the study…'}
          </p>
        </div>
        <dl className="study-meta">
          <div>
            <dt>Study</dt>
            <dd data-testid="study-id">{studyId}</dd>
          </div>
          <div>
            <dt>Version</dt>
            <dd data-testid="current-version">
              {version ? `v${version.seq} (${version.id})` : '…'}
            </dd>
          </div>
          <div>
            <dt>Mode</dt>
            <dd data-testid="mode">{editable ? 'Editing head' : 'Read only'}</dd>
          </div>
        </dl>
      </header>

      {study.error && (
        <div className="error" role="alert" data-testid="error">
          <span>{study.error}</span>
          <button type="button" onClick={study.dismissError}>
            Dismiss
          </button>
        </div>
      )}

      <div className="layout">
        <aside className="sidebar">
          <VersionTimeline
            versions={timeline}
            selectedId={version?.id ?? ''}
            headId={headId}
            graph={version?.graph}
            onSelect={(versionId) => {
              setHighlight(NONE)
              study.select(versionId)
            }}
          />
        </aside>

        <main className="main">
          <nav className="tabs" role="tablist" aria-label="Views">
            {TABS.map(({ id, label }) => (
              <button
                key={id}
                type="button"
                role="tab"
                aria-selected={tab === id}
                data-testid={`tab-${id}`}
                onClick={() => setTab(id)}
              >
                {label}
              </button>
            ))}
            {highlight.size > 0 && (
              <button type="button" className="clear" onClick={() => setHighlight(NONE)}>
                Clear highlight
              </button>
            )}
          </nav>

          {version && grid && tab === 'schedule' && (
            <ScheduleGrid
              grid={grid}
              editable={editable}
              highlight={highlight}
              onOperation={study.apply}
            />
          )}
          {version && tab === 'graph' && (
            <GraphView
              graph={version.graph}
              highlight={highlight}
              onSelect={(id) => setHighlight(new Set([id]))}
            />
          )}
        </main>

        <aside className="side-panels">
          {version && (
            <>
              <FindingsPanel
                findings={version.findings}
                onSelect={(finding) => setHighlight(new Set(finding.element_ids))}
              />
              <EndpointsPanel
                endpoints={version.graph.intent.endpoints}
                editable={editable}
                highlight={highlight}
                onOperation={study.apply}
              />
              <OperationForm
                types={study.operationTypes}
                editable={editable}
                onOperation={study.apply}
              />
            </>
          )}
        </aside>
      </div>
    </div>
  )
}
