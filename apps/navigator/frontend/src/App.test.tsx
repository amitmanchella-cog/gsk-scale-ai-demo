import { render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import App from './App'

const health = {
  status: 'ok',
  version: '0.1.0',
  data_dir: '/repo/data',
  row_counts: { reps: 2, territories: 1 },
}
const reps = [
  { rep_id: 'R001', rep_name: 'Dev Okafor', territory_id: 'T001', region: 'South', hire_date: '2022-03-03' },
  { rep_id: 'R002', rep_name: 'Hugo Rossi', territory_id: 'T002', region: 'East', hire_date: '2023-09-09' },
]

function jsonResponse(body: unknown) {
  return { ok: true, status: 200, json: async () => body } as Response
}

afterEach(() => {
  vi.restoreAllMocks()
})

describe('App', () => {
  it('renders the title and lists reps from the API', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = String(input)
      if (url.endsWith('/health')) return jsonResponse(health)
      if (url.endsWith('/reps')) return jsonResponse(reps)
      throw new Error(`unexpected fetch ${url}`)
    })

    render(<App />)

    expect(screen.getByRole('heading', { level: 1, name: 'Field Force Navigator' })).toBeInTheDocument()
    expect(await screen.findByText('Dev Okafor')).toBeInTheDocument()
    expect(screen.getByText('Hugo Rossi')).toBeInTheDocument()
    expect(screen.getByText('API ok')).toBeInTheDocument()
    expect(screen.getByRole('heading', { level: 2, name: 'Reps (2)' })).toBeInTheDocument()
  })

  it('shows an error when the API is unreachable', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({ ok: false, status: 503, json: async () => ({}) } as Response)

    render(<App />)

    expect(await screen.findByText(/API unreachable/)).toBeInTheDocument()
  })
})
