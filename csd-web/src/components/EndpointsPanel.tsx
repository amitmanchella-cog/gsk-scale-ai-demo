import { useEffect, useState } from 'react'
import type { Endpoint, Operation } from '../api/types'

interface Props {
  endpoints: Endpoint[]
  editable: boolean
  highlight: ReadonlySet<string>
  onOperation: (operation: Operation) => void
}

function EndpointRow(props: Omit<Props, 'endpoints'> & { endpoint: Endpoint }) {
  const { endpoint, editable, highlight, onOperation } = props
  const [week, setWeek] = useState(String(endpoint.timepoint.week))
  useEffect(() => setWeek(String(endpoint.timepoint.week)), [endpoint.timepoint.week])
  const parsed = Number(week)
  const changed = week.trim() !== '' && Number.isInteger(parsed) && parsed !== endpoint.timepoint.week

  return (
    <li
      data-testid={`endpoint-${endpoint.id}`}
      className={highlight.has(endpoint.id) ? 'highlighted' : undefined}
    >
      <div>
        <span className={`badge ${endpoint.level}`}>{endpoint.level}</span> {endpoint.name}
      </div>
      <form
        onSubmit={(event) => {
          event.preventDefault()
          if (changed)
            onOperation({ type: 'ChangeEndpointTiming', endpoint_id: endpoint.id, week: parsed })
        }}
      >
        <label>
          Week
          <input
            type="number"
            inputMode="numeric"
            min={0}
            aria-label={`Timepoint week for ${endpoint.name}`}
            data-testid={`endpoint-week-${endpoint.id}`}
            value={week}
            disabled={!editable}
            onChange={(event) => setWeek(event.target.value)}
          />
        </label>
        <button
          type="submit"
          data-testid={`retime-${endpoint.id}`}
          disabled={!editable || !changed}
        >
          Change timing
        </button>
      </form>
    </li>
  )
}

export function EndpointsPanel({ endpoints, ...rest }: Props) {
  return (
    <section className="panel" data-testid="endpoints-panel" aria-label="Endpoints">
      <h2>Endpoints</h2>
      <ul className="endpoints">
        {endpoints.map((endpoint) => (
          <EndpointRow key={endpoint.id} endpoint={endpoint} {...rest} />
        ))}
      </ul>
    </section>
  )
}
