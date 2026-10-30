import { useEffect, useState } from 'react'
import { fetchHealth, fetchReps, type Health, type Rep } from './api'

export default function App() {
  const [health, setHealth] = useState<Health | null>(null)
  const [reps, setReps] = useState<Rep[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    Promise.all([fetchHealth(), fetchReps()])
      .then(([healthResponse, repsResponse]) => {
        if (cancelled) return
        setHealth(healthResponse)
        setReps(repsResponse)
      })
      .catch((err: unknown) => {
        if (cancelled) return
        setError(err instanceof Error ? err.message : String(err))
      })
    return () => {
      cancelled = true
    }
  }, [])

  return (
    <main>
      <h1>Field Force Navigator</h1>
      <p className="subtitle">UC4 scaffold &mdash; reps and territories from the UC1 curated tables (synthetic data).</p>

      <section className="status" aria-label="API status">
        {error ? (
          <span className="error">API unreachable: {error}</span>
        ) : health ? (
          <>
            <span className="ok">API {health.status}</span>
            <span>v{health.version}</span>
            {Object.entries(health.row_counts).map(([table, count]) => (
              <span key={table}>
                {table}: {count.toLocaleString()}
              </span>
            ))}
          </>
        ) : (
          <span>Loading&hellip;</span>
        )}
      </section>

      <h2>Reps ({reps.length})</h2>
      <table>
        <thead>
          <tr>
            <th>Rep</th>
            <th>Name</th>
            <th>Territory</th>
            <th>Region</th>
          </tr>
        </thead>
        <tbody>
          {reps.map((rep) => (
            <tr key={rep.rep_id}>
              <td>{rep.rep_id}</td>
              <td>{rep.rep_name}</td>
              <td>{rep.territory_id}</td>
              <td>{rep.region ?? '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </main>
  )
}
