import type { Finding } from '../api/types'

const TYPE_LABEL: Record<Finding['type'], string> = {
  untraced_activity: 'Untraced activity',
  unmet_endpoint_timepoint: 'Unmet endpoint timepoint',
  missing_operational_standard: 'Missing operational standard',
}

interface Props {
  findings: Finding[]
  onSelect: (finding: Finding) => void
}

export function FindingsPanel({ findings, onSelect }: Props) {
  return (
    <section className="panel" data-testid="findings-panel" aria-label="Findings">
      <h2>
        Findings{' '}
        <span
          className={findings.length ? 'badge warning' : 'badge ok'}
          data-testid="findings-count"
        >
          {findings.length}
        </span>
      </h2>
      {findings.length === 0 ? (
        <p className="empty" data-testid="findings-empty">
          No findings. Intent and plan are consistent.
        </p>
      ) : (
        <ul className="findings">
          {findings.map((finding) => (
            <li key={finding.id} data-testid="finding" data-finding-id={finding.id}>
              <button type="button" onClick={() => onSelect(finding)}>
                <span className="finding-type">
                  {finding.severity === 'warning' ? 'Warning' : finding.severity}:{' '}
                  {TYPE_LABEL[finding.type]}
                </span>
                <span className="finding-message">{finding.message}</span>
                <span className="finding-ids">{finding.element_ids.join(' · ')}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
