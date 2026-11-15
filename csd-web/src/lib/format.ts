import type { Score } from '../api/types'

export const SCORE_ROWS: { key: keyof Score; label: string; format: (value: number) => string }[] = [
  { key: 'visit_count', label: 'Visits', format: (value) => String(value) },
  { key: 'patient_time_minutes', label: 'Patient time', format: (value) => `${value} min` },
  { key: 'cost_proxy', label: 'Cost proxy', format: (value) => String(value) },
]

/** A signed difference: "+90 min", "-1", or "0". */
export function formatDelta(value: number, format: (value: number) => string): string {
  return value > 0 ? `+${format(value)}` : format(value)
}
