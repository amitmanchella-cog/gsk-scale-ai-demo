import type { Day } from '../api'

export interface HcpListProps {
  repId: string
  addDay: Day
  onAddDayChange: (day: Day) => void
  onAdd: (hcpId: string) => Promise<void>
  /** bumps whenever the plan changes so the list can refresh derived state if it wants to */
  planVersion: number
}

/** Placeholder — replaced by story S1 (MBA-3659). */
export default function HcpList({ repId }: HcpListProps) {
  return (
    <section className="panel" aria-labelledby="hcp-list-heading">
      <h2 id="hcp-list-heading">Territory HCPs</h2>
      <p>{repId ? `HCP list for ${repId} coming in S1.` : 'Select a rep to see their territory.'}</p>
    </section>
  )
}
