import type { ReactNode } from 'react'
import { DAY_NAMES, type Plan, type PlanDay } from '../api'

export interface PlanBuilderProps {
  repId: string
  plan: Plan | null
  message: string | null
  onRemove: (visitId: number) => Promise<void>
  onClear: () => Promise<void>
  /** S4 (MBA-3662) renders the Export CSV link here, next to "Clear plan". */
  exportSlot?: ReactNode
}

function DayColumn({ day, onRemove }: { day: PlanDay; onRemove: (visitId: number) => Promise<void> }) {
  const name = DAY_NAMES[day.day]
  const headingId = `plan-day-${day.day}`
  return (
    <section className="plan-day" aria-labelledby={headingId}>
      <h3 id={headingId}>
        {name} {day.count}/{day.capacity}
      </h3>
      <p className="plan-date">{day.date}</p>
      {day.visits.length === 0 ? (
        <p className="muted">No visits</p>
      ) : (
        <ul className="plan-visits">
          {day.visits.map((visit) => (
            <li key={visit.visit_id} className="plan-visit">
              <div className="plan-visit-body">
                <strong>{visit.hcp_name}</strong>
                <span className="muted">
                  {visit.specialty} · Segment {visit.segment} · score {visit.score}
                </span>
              </div>
              <button type="button" onClick={() => void onRemove(visit.visit_id)} aria-label={`Remove ${visit.hcp_name} from ${name}`}>
                Remove
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}

export default function PlanBuilder({ repId, plan, message, onRemove, onClear, exportSlot }: PlanBuilderProps) {
  return (
    <section className="panel" aria-labelledby="plan-heading">
      <div className="panel-header">
        <h2 id="plan-heading">Weekly plan</h2>
        {plan && (
          <p className="muted">
            Week of {plan.week_start} · {plan.total_visits} {plan.total_visits === 1 ? 'visit' : 'visits'}
          </p>
        )}
      </div>

      {message && (
        <div role="alert" className="alert">
          {message}
        </div>
      )}

      {!repId ? (
        <p>Select a rep to start a plan.</p>
      ) : !plan ? (
        <p>Loading plan…</p>
      ) : (
        <>
          <ul className="warnings" aria-live="polite" aria-label="Plan warnings">
            {plan.warnings.map((warning) => (
              <li key={`${warning.type}-${warning.hcp_id}`} className="warning">
                {warning.message}
              </li>
            ))}
          </ul>

          <div className="plan-days">
            {plan.days.map((day) => (
              <DayColumn key={day.day} day={day} onRemove={onRemove} />
            ))}
          </div>

          <div className="plan-actions">
            <button type="button" onClick={() => void onClear()} disabled={plan.total_visits === 0}>
              Clear plan
            </button>
            {exportSlot}
          </div>
        </>
      )}
    </section>
  )
}
