import type { StudyGraph, VersionSummary } from '../api/types'
import type { Names } from '../lib/operations'
import { describeOperation } from '../lib/operations'

interface Props {
  versions: VersionSummary[]
  selectedId: string
  headId: string
  graph?: StudyGraph
  /** Names of elements seen in other versions, for operations on elements now gone. */
  names?: Names
  onSelect: (versionId: string) => void
}

export function VersionTimeline({ versions, selectedId, headId, graph, names, onSelect }: Props) {
  return (
    <section className="panel timeline-panel" aria-label="Version timeline">
      <h2>
        Versions <span className="badge">{versions.length}</span>
      </h2>
      <ol className="timeline" data-testid="version-timeline">
        {versions.map((version) => (
          <li
            key={version.id}
            data-testid="timeline-version"
            data-version-id={version.id}
            className={version.id === selectedId ? 'selected' : undefined}
          >
            <button
              type="button"
              aria-current={version.id === selectedId}
              onClick={() => onSelect(version.id)}
            >
              <span className="seq">
                v{version.seq}
                {version.id === headId ? ' · head' : ''}
              </span>
              <span className="label">{describeOperation(version.operation, graph, names)}</span>
              <span className={version.finding_count ? 'badge warning' : 'badge ok'}>
                {version.finding_count} {version.finding_count === 1 ? 'finding' : 'findings'}
              </span>
            </button>
          </li>
        ))}
      </ol>
    </section>
  )
}
