import type {
  Branch,
  Comparison,
  Operation,
  ScheduleGrid,
  Score,
  StudySummary,
  Version,
  VersionSummary,
} from './types'

export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message)
  }
}

const BASE = '/api'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(BASE + path, {
    ...init,
    headers: init?.body ? { 'content-type': 'application/json' } : undefined,
  })
  if (!response.ok) {
    let detail = response.statusText
    try {
      const body: { detail?: unknown } = await response.json()
      detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail)
    } catch {
      // keep the status text
    }
    throw new ApiError(response.status, detail)
  }
  return (await response.json()) as T
}

export const api = {
  study: (studyId: string) => request<StudySummary>(`/studies/${studyId}`),
  versions: (studyId: string) => request<VersionSummary[]>(`/studies/${studyId}/versions`),
  branches: (studyId: string) => request<Branch[]>(`/studies/${studyId}/branches`),
  version: (versionId: string) => request<Version>(`/versions/${versionId}`),
  schedule: (versionId: string) => request<ScheduleGrid>(`/versions/${versionId}/schedule`),
  operationTypes: () => request<string[]>('/operation-types'),
  score: (versionId: string) => request<Score>(`/versions/${versionId}/score`),
  /** ``branch`` names the branch to extend; the API defaults to the version's own branch. */
  applyOperation: (versionId: string, operation: Operation, branch?: string) =>
    request<Version>(
      `/versions/${versionId}/operations` +
        (branch ? `?branch=${encodeURIComponent(branch)}` : ''),
      { method: 'POST', body: JSON.stringify(operation) },
    ),
  createBranch: (versionId: string, name: string) =>
    request<Branch>(`/versions/${versionId}/branches`, {
      method: 'POST',
      body: JSON.stringify({ name }),
    }),
  compare: (left: string, right: string) =>
    request<Comparison>(
      `/compare?left=${encodeURIComponent(left)}&right=${encodeURIComponent(right)}`,
    ),
}

export type Api = typeof api
