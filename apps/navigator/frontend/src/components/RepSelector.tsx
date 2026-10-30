import type { Rep } from '../api'

interface Props {
  reps: Rep[]
  value: string
  onChange: (repId: string) => void
}

export default function RepSelector({ reps, value, onChange }: Props) {
  return (
    <div className="field">
      <label htmlFor="rep-select">Rep</label>
      <select id="rep-select" value={value} onChange={(e) => onChange(e.target.value)}>
        <option value="">Select a rep…</option>
        {reps.map((rep) => (
          <option key={rep.rep_id} value={rep.rep_id}>
            {rep.rep_name} ({rep.rep_id}, {rep.territory_id})
          </option>
        ))}
      </select>
    </div>
  )
}
