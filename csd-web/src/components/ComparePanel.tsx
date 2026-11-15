import { useEffect, useState } from 'react'
import { api as defaultApi } from '../api/client'
import type { Api } from '../api/client'
import type { Branch, ComparedVersion, Comparison } from '../api/types'
import { SCORE_ROWS, formatDelta } from '../lib/format'

interface Props {
  branches: Branch[]
  /** The branch shown on the right to start with; the left starts on main. */
  initialRight: string
  api?: Pick<Api, 'compare'>
}

function Side({ side, version }: { side: 'left' | 'right'; version: ComparedVersion }) {
  return (
    <div className="compare-findings" data-testid={`compare-findings-${side}`}>
      <h3>
        {version.branch} · v{version.seq}{' '}
        <span className={version.findings.length ? 'badge warning' : 'badge ok'}>
          {version.findings.length} {version.findings.length === 1 ? 'finding' : 'findings'}
        </span>
      </h3>
      <ul>
        {version.findings.map((finding) => (
          <li key={finding.id}>{finding.message}</li>
        ))}
      </ul>
    </div>
  )
}

/** Two branch heads side by side: scores, findings and what differs between them. */
export function ComparePanel({ branches, initialRight, api = defaultApi }: Props) {
  const names = branches.map((branch) => branch.name)
  const [left, setLeft] = useState('main')
  const [right, setRight] = useState(
    initialRight !== 'main' ? initialRight : (names.find((name) => name !== 'main') ?? 'main'),
  )
  const [comparison, setComparison] = useState<Comparison | null>(null)
  const [error, setError] = useState<string | null>(null)

  const leftHead = branches.find((branch) => branch.name === left)?.head_version_id
  const rightHead = branches.find((branch) => branch.name === right)?.head_version_id

  useEffect(() => {
    if (!leftHead || !rightHead) return
    let cancelled = false
    api
      .compare(leftHead, rightHead)
      .then((next) => {
        if (cancelled) return
        setComparison(next)
        setError(null)
      })
      .catch((caught: unknown) => {
        if (!cancelled) setError(caught instanceof Error ? caught.message : String(caught))
      })
    return () => {
      cancelled = true
    }
  }, [api, leftHead, rightHead])

  const picker = (side: 'left' | 'right', value: string, onChange: (name: string) => void) => (
    <label>
      {side === 'left' ? 'Left' : 'Right'}
      <select
        data-testid={`compare-${side}`}
        value={value}
        onChange={(event) => onChange(event.target.value)}
      >
        {names.map((name) => (
          <option key={name}>{name}</option>
        ))}
      </select>
    </label>
  )

  return (
    <section className="panel compare" data-testid="compare-panel" aria-label="Compare branches">
      <div className="compare-pickers">
        {picker('left', left, setLeft)}
        {picker('right', right, setRight)}
      </div>
      {error && <p role="alert">{error}</p>}
      {comparison && (
        <>
          <div className="grid-scroll">
            <table className="compare-table" data-testid="compare-table">
              <thead>
                <tr>
                  <th scope="col">Score (lower is better)</th>
                  <th scope="col" data-testid="compare-head-left">
                    {comparison.left.branch}
                  </th>
                  <th scope="col" data-testid="compare-head-right">
                    {comparison.right.branch}
                  </th>
                  <th scope="col">Difference</th>
                </tr>
              </thead>
              <tbody>
                {SCORE_ROWS.map(({ key, label, format }) => {
                  const delta = comparison.delta[key]
                  return (
                    <tr key={key} data-testid={`compare-row-${key}`}>
                      <th scope="row">{label}</th>
                      <td data-testid={`compare-left-${key}`}>{format(comparison.left.score[key])}</td>
                      <td data-testid={`compare-right-${key}`}>
                        {format(comparison.right.score[key])}
                      </td>
                      <td
                        data-testid={`compare-delta-${key}`}
                        className={delta < 0 ? 'better' : delta > 0 ? 'worse' : undefined}
                      >
                        {formatDelta(delta, format)}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
          <div className="compare-sides">
            <Side side="left" version={comparison.left} />
            <Side side="right" version={comparison.right} />
          </div>
          <h3>
            Differences, left to right <span className="badge">{comparison.changes.length}</span>
          </h3>
          {comparison.changes.length === 0 ? (
            <p className="empty" data-testid="compare-no-changes">
              The two versions hold the same graph.
            </p>
          ) : (
            <ul className="changes" data-testid="compare-changes">
              {comparison.changes.map((change) => (
                <li
                  key={change.element_id}
                  data-testid="compare-change"
                  data-element-id={change.element_id}
                  data-change={change.change}
                >
                  <span className={`badge ${change.change}`}>{change.change}</span>{' '}
                  {change.element_type}: {change.label}{' '}
                  <span className="finding-ids">{change.element_id}</span>
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </section>
  )
}
