import { useEffect, useState } from 'react'
import {
  ApiError,
  DAYS,
  DAY_NAMES,
  fetchHcps,
  type Day,
  type HcpFilters,
  type HcpListResponse,
  type HcpView,
  type Segment,
} from '../api'

export interface HcpListProps {
  repId: string
  addDay: Day
  onAddDayChange: (day: Day) => void
  onAdd: (hcpId: string) => Promise<void>
  /** bumps whenever the plan changes so the list can refresh derived state if it wants to */
  planVersion: number
}

const SPECIALTIES = ['Cardiology', 'Endocrinology', 'Pulmonology', 'Oncology', 'GP', 'Neurology']
const SEGMENTS: Segment[] = ['A', 'B', 'C']
const SEARCH_DEBOUNCE_MS = 200

function lastVisit(hcp: HcpView): string {
  if (hcp.days_since_last_visit === null) return 'never visited'
  const days = `${hcp.days_since_last_visit} day${hcp.days_since_last_visit === 1 ? '' : 's'}`
  return hcp.last_visit_date ? `${days} (${hcp.last_visit_date})` : days
}

export default function HcpList({ repId, addDay, onAddDayChange, onAdd }: HcpListProps) {
  const [specialty, setSpecialty] = useState('')
  const [segment, setSegment] = useState<Segment | ''>('')
  const [minDays, setMinDays] = useState('')
  const [search, setSearch] = useState('')
  const [q, setQ] = useState('')
  const [data, setData] = useState<HcpListResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    const timer = setTimeout(() => setQ(search.trim()), SEARCH_DEBOUNCE_MS)
    return () => clearTimeout(timer)
  }, [search])

  useEffect(() => {
    setError(null)
    if (!repId) {
      setData(null)
      return
    }
    let cancelled = false
    setLoading(true)
    const filters: HcpFilters = {
      specialty,
      segment,
      min_days_since_last_visit: minDays === '' ? '' : Number(minDays),
      q,
    }
    fetchHcps(repId, filters)
      .then((response) => {
        if (cancelled) return
        setData(response)
      })
      .catch((err: unknown) => {
        if (cancelled) return
        setError(err instanceof ApiError ? err.detail : err instanceof Error ? err.message : String(err))
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [repId, specialty, segment, minDays, q])

  const dayName = DAY_NAMES[addDay]

  return (
    <section className="panel" aria-labelledby="hcp-list-heading">
      <h2 id="hcp-list-heading">Territory HCPs</h2>

      <div className="filters">
        <div className="field">
          <label htmlFor="hcp-specialty">Specialty</label>
          <select id="hcp-specialty" value={specialty} onChange={(e) => setSpecialty(e.target.value)}>
            <option value="">All</option>
            {SPECIALTIES.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </div>
        <div className="field">
          <label htmlFor="hcp-segment">Segment</label>
          <select id="hcp-segment" value={segment} onChange={(e) => setSegment(e.target.value as Segment | '')}>
            <option value="">All</option>
            {SEGMENTS.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </div>
        <div className="field">
          <label htmlFor="hcp-min-days">Days since last visit ≥</label>
          <input
            id="hcp-min-days"
            type="number"
            min={0}
            step={1}
            inputMode="numeric"
            value={minDays}
            onChange={(e) => setMinDays(e.target.value)}
          />
        </div>
        <div className="field">
          <label htmlFor="hcp-search">Search by name</label>
          <input id="hcp-search" type="search" value={search} onChange={(e) => setSearch(e.target.value)} />
        </div>
        <div className="field">
          <label htmlFor="hcp-add-day">Add to</label>
          <select id="hcp-add-day" value={addDay} onChange={(e) => onAddDayChange(e.target.value as Day)}>
            {DAYS.map((day) => (
              <option key={day} value={day}>
                {DAY_NAMES[day]}
              </option>
            ))}
          </select>
        </div>
      </div>

      {!repId ? (
        <p>Select a rep to see their territory.</p>
      ) : (
        <>
          {error && (
            <p className="alert" role="alert">
              Could not load HCPs: {error}
            </p>
          )}
          {data && (
            <p className="count" aria-live="polite">
              {data.count} HCPs in {data.territory.territory_id} {data.territory.territory_name}, as of {data.as_of}
              {loading ? ' (updating…)' : ''}
            </p>
          )}
          {data && data.hcps.length === 0 && !error && <p>No HCPs match the current filters.</p>}
          {data && data.hcps.length > 0 && (
            <table aria-busy={loading}>
              <thead>
                <tr>
                  <th scope="col">HCP</th>
                  <th scope="col">Specialty</th>
                  <th scope="col">Segment</th>
                  <th scope="col">Last visit</th>
                  <th scope="col">Open follow-ups</th>
                  <th scope="col">Score</th>
                  <th scope="col">Reason</th>
                  <th scope="col">Add</th>
                </tr>
              </thead>
              <tbody>
                {data.hcps.map((hcp) => (
                  <tr key={hcp.hcp_id}>
                    <td>
                      <span className="hcp-id">{hcp.hcp_id}</span> {hcp.hcp_name}
                    </td>
                    <td>{hcp.specialty}</td>
                    <td>{hcp.segment}</td>
                    <td>{lastVisit(hcp)}</td>
                    <td>{hcp.open_follow_ups}</td>
                    <td className="score">{hcp.score}</td>
                    <td className="reason">{hcp.reason}</td>
                    <td>
                      <button
                        type="button"
                        aria-label={`Add ${hcp.hcp_name} to ${dayName}`}
                        onClick={() => void onAdd(hcp.hcp_id)}
                      >
                        Add
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </>
      )}
    </section>
  )
}
