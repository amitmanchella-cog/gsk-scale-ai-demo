import type { Plan } from '../api'

export interface PlanBuilderProps {
  repId: string
  plan: Plan | null
  message: string | null
  onRemove: (visitId: number) => Promise<void>
  onClear: () => Promise<void>
}

/** Placeholder — replaced by story S3 (MBA-3661); S4 (MBA-3662) adds the Export CSV link. */
export default function PlanBuilder({ repId }: PlanBuilderProps) {
  return (
    <section className="panel" aria-labelledby="plan-heading">
      <h2 id="plan-heading">Weekly plan</h2>
      <p>{repId ? `Plan builder for ${repId} coming in S3.` : 'Select a rep to start a plan.'}</p>
    </section>
  )
}
