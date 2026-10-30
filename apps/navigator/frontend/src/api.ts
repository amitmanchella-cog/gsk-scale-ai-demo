export const API_BASE = '/api'

export interface Health {
  status: string
  version: string
  data_dir: string
  row_counts: Record<string, number>
}

export interface Rep {
  rep_id: string
  rep_name: string
  territory_id: string
  region: string | null
  hire_date: string | null
}

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`)
  if (!response.ok) {
    throw new Error(`${path} failed with HTTP ${response.status}`)
  }
  return (await response.json()) as T
}

export const fetchHealth = () => getJson<Health>('/health')
export const fetchReps = () => getJson<Rep[]>('/reps')
