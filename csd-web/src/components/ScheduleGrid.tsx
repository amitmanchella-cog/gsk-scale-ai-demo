import { useEffect, useState } from 'react'
import type { Operation, ScheduleGrid as Grid } from '../api/types'

interface Props {
  grid: Grid
  editable: boolean
  highlight: ReadonlySet<string>
  onOperation: (operation: Operation) => void
}

function DayInput(props: {
  visit: Grid['visits'][number]
  editable: boolean
  onCommit: (day: number) => void
}) {
  const { visit, editable, onCommit } = props
  const [text, setText] = useState(String(visit.day))
  useEffect(() => setText(String(visit.day)), [visit.day])

  const commit = () => {
    const day = Number(text)
    // Show the stored day again until the API accepts the move: a rejected day must not
    // linger in the field and be re-submitted by the next blur.
    setText(String(visit.day))
    if (text.trim() !== '' && Number.isInteger(day) && day !== visit.day) onCommit(day)
  }
  return (
    <label className="day-input">
      Day
      <input
        type="number"
        inputMode="numeric"
        aria-label={`Study day for ${visit.name}`}
        data-testid={`visit-day-${visit.id}`}
        value={text}
        disabled={!editable}
        onChange={(event) => setText(event.target.value)}
        onBlur={commit}
        onKeyDown={(event) => {
          if (event.key === 'Enter') commit()
          if (event.key === 'Escape') setText(String(visit.day))
        }}
      />
    </label>
  )
}

/** The schedule of activities: activities as rows, visits (by study day) as columns. */
export function ScheduleGrid({ grid, editable, highlight, onOperation }: Props) {
  return (
    <div className="grid-scroll">
      <table className="soa-grid" data-testid="soa-grid">
        <thead>
          <tr>
            <th scope="col" className="corner">
              Activity
            </th>
            {grid.visits.map((visit) => (
              <th
                key={visit.id}
                scope="col"
                data-testid={`visit-header-${visit.id}`}
                className={highlight.has(visit.id) ? 'highlighted' : undefined}
              >
                <span className="visit-name">{visit.name}</span>
                <DayInput
                  visit={visit}
                  editable={editable}
                  onCommit={(day) => onOperation({ type: 'MoveVisit', visit_id: visit.id, day })}
                />
                <span className="visit-meta">
                  ±{visit.window} d · {visit.on_site ? 'on site' : 'remote'}
                </span>
                <button
                  type="button"
                  className="remove-visit"
                  data-testid={`remove-visit-${visit.id}`}
                  aria-label={`Remove visit ${visit.name}`}
                  disabled={!editable}
                  onClick={() => onOperation({ type: 'RemoveVisit', visit_id: visit.id })}
                >
                  Remove
                </button>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {grid.rows.map((row) => (
            <tr
              key={row.activity_id}
              data-testid={`activity-row-${row.activity_id}`}
              className={highlight.has(row.activity_id) ? 'highlighted' : undefined}
            >
              <th scope="row">{row.activity_name}</th>
              {row.cells.map((scheduled, index) => {
                const visit = grid.visits[index]!
                const cellId = `${visit.id}:${row.activity_id}`
                return (
                  <td
                    key={visit.id}
                    data-testid={`cell-${row.activity_id}-${visit.id}`}
                    data-scheduled={scheduled}
                    className={
                      highlight.has(cellId) || highlight.has(visit.id) ? 'highlighted' : undefined
                    }
                  >
                    <button
                      type="button"
                      aria-pressed={scheduled}
                      aria-label={`${row.activity_name} at ${visit.name}`}
                      disabled={!editable}
                      onClick={() =>
                        onOperation({
                          type: scheduled ? 'UnscheduleActivity' : 'ScheduleActivity',
                          visit_id: visit.id,
                          activity_id: row.activity_id,
                        })
                      }
                    >
                      {scheduled ? 'X' : ''}
                    </button>
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
