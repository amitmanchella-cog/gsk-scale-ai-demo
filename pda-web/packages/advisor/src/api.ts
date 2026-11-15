import type {
  Assessment,
  Change,
  CompetingTrials,
  Forecast,
  Protocol,
  SampleProtocol,
  Suggestions,
  WhatIf,
} from './types';

export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
    readonly warnings: string[] = [],
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

/** FastAPI puts the reason in `detail`, either as text or as `{message, warnings}`. */
export function toApiError(status: number, body: unknown): ApiError {
  const detail = (body as { detail?: unknown } | null)?.detail;
  if (typeof detail === 'string') return new ApiError(status, detail);
  if (detail && typeof detail === 'object' && !Array.isArray(detail)) {
    const { message, warnings } = detail as { message?: string; warnings?: string[] };
    return new ApiError(status, message ?? `Request failed (${status})`, warnings ?? []);
  }
  return new ApiError(status, `Request failed (${status})`);
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`/api${path}`, init);
  } catch {
    throw new ApiError(0, 'The Advisor API cannot be reached. Check that pda-api is running.');
  }
  if (!response.ok) {
    throw toApiError(response.status, await response.json().catch(() => null));
  }
  return (await response.json()) as T;
}

export const api = {
  samples: () => request<SampleProtocol[]>('/samples'),
  async sampleFile(sample: SampleProtocol): Promise<File> {
    const response = await fetch(`/api/samples/${sample.key}`);
    if (!response.ok) throw new ApiError(response.status, 'Could not load the sample protocol.');
    return new File([await response.text()], sample.filename, { type: 'text/plain' });
  },
  upload(file: File) {
    const body = new FormData();
    body.append('file', file);
    return request<Protocol>('/protocols', { method: 'POST', body });
  },
  protocol: (id: string) => request<Protocol>(`/protocols/${id}`),
  assessment: (id: string) => request<Assessment>(`/protocols/${id}/assessment`),
  competing: (id: string) => request<CompetingTrials>(`/protocols/${id}/competing-trials`),
  forecast: (id: string) => request<Forecast>(`/protocols/${id}/forecast`),
  suggestions: (id: string) => request<Suggestions>(`/protocols/${id}/suggestions`),
  whatIf: (id: string, changes: Change[]) =>
    request<WhatIf>(`/protocols/${id}/what-if`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ changes }),
    }),
};
