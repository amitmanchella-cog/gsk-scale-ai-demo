import { useCallback, useEffect, useState } from 'react'
import {
  ApiError,
  addPlanVisit,
  clearPlan,
  fetchHealth,
  fetchPlan,
  fetchReps,
  removePlanVisit,
  type Day,
  type Health,
  type Plan,
  type Rep,
} from './api'
import HcpList from './components/HcpList'
import PlanBuilder from './components/PlanBuilder'
import RepSelector from './components/RepSelector'

export default function App() {
  const [health, setHealth] = useState<Health | null>(null)
  const [reps, setReps] = useState<Rep[]>([])
  const [error, setError] = useState<string | null>(null)
  const [repId, setRepId] = useState('')
  const [addDay, setAddDay] = useState<Day>('Mon')
  const [plan, setPlan] = useState<Plan | null>(null)
  const [planVersion, setPlanVersion] = useState(0)
  const [message, setMessage] = useState<string | null>(null)

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

  const applyPlan = useCallback((next: Plan) => {
    setPlan(next)
    setPlanVersion((v) => v + 1)
  }, [])

  useEffect(() => {
    setPlan(null)
    setMessage(null)
    if (!repId) return
    let cancelled = false
    fetchPlan(repId)
      .then((p) => {
        if (!cancelled) applyPlan(p)
      })
      .catch(() => {
        // plan endpoint lands with S3; until then the panel shows its placeholder
      })
    return () => {
      cancelled = true
    }
  }, [repId, applyPlan])

  const withMessage = useCallback(
    async (action: () => Promise<Plan>) => {
      try {
        applyPlan(await action())
        setMessage(null)
      } catch (err) {
        setMessage(err instanceof ApiError ? err.detail : err instanceof Error ? err.message : String(err))
      }
    },
    [applyPlan],
  )

  const onAdd = useCallback((hcpId: string) => withMessage(() => addPlanVisit(repId, hcpId, addDay)), [withMessage, repId, addDay])
  const onRemove = useCallback((visitId: number) => withMessage(() => removePlanVisit(repId, visitId)), [withMessage, repId])
  const onClear = useCallback(() => withMessage(() => clearPlan(repId)), [withMessage, repId])

  const selectedRep = reps.find((rep) => rep.rep_id === repId)

  return (
    <main>
      <header className="page-header">
        <div>
          <h1>Field Force Navigator</h1>
          <p className="subtitle">Territory call planner &mdash; UC1 curated tables, synthetic data only.</p>
        </div>
        <RepSelector reps={reps} value={repId} onChange={setRepId} />
      </header>

      <section className="status" aria-label="API status">
        {error ? (
          <span className="error">API unreachable: {error}</span>
        ) : health ? (
          <>
            <span className="ok">API {health.status}</span>
            <span>v{health.version}</span>
            <span>as of {health.as_of}</span>
            {selectedRep && (
              <span>
                {selectedRep.rep_name} &middot; territory {selectedRep.territory_id}
                {selectedRep.region ? ` (${selectedRep.region})` : ''}
              </span>
            )}
          </>
        ) : (
          <span>Loading&hellip;</span>
        )}
      </section>

      <div className="columns">
        <HcpList repId={repId} addDay={addDay} onAddDayChange={setAddDay} onAdd={onAdd} planVersion={planVersion} />
        <PlanBuilder repId={repId} plan={plan} message={message} onRemove={onRemove} onClear={onClear} />
      </div>
    </main>
  )
}
