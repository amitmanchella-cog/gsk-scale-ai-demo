import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import App from './App'

const health = {
  status: 'ok',
  version: '0.1.0',
  data_dir: '/repo/data',
  as_of: '2025-09-29',
  row_counts: { reps: 2, territories: 1 },
}
const reps = [
  { rep_id: 'R001', rep_name: 'Dev Okafor', territory_id: 'T001', region: 'South', hire_date: '2022-03-03' },
  { rep_id: 'R002', rep_name: 'Hugo Rossi', territory_id: 'T002', region: 'East', hire_date: '2023-09-09' },
]

function jsonResponse(body: unknown, status = 200) {
  return { ok: status < 400, status, json: async () => body } as Response
}

export function mockApi(routes: Record<string, unknown>) {
  return vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
    const url = String(input)
    const pathname = new URL(url, 'http://localhost').pathname
    for (const [suffix, body] of Object.entries(routes)) {
      if (pathname.endsWith(suffix)) return jsonResponse(body)
    }
    return jsonResponse({ detail: `unexpected fetch ${url}` }, 404)
  })
}

afterEach(() => {
  vi.restoreAllMocks()
})

describe('App', () => {
  it('renders the title, the as-of date and the rep selector', async () => {
    mockApi({ '/health': health, '/reps': reps })

    render(<App />)

    expect(screen.getByRole('heading', { level: 1, name: 'Field Force Navigator' })).toBeInTheDocument()
    expect(await screen.findByText('API ok')).toBeInTheDocument()
    expect(screen.getByText('as of 2025-09-29')).toBeInTheDocument()
    const select = screen.getByLabelText('Rep') as HTMLSelectElement
    expect(select.options).toHaveLength(3)
    expect(select.value).toBe('')
    expect(screen.getByRole('option', { name: 'Dev Okafor (R001, T001)' })).toBeInTheDocument()
  })

  it('shows the selected rep and territory in the status bar', async () => {
    mockApi({ '/health': health, '/reps': reps })
    render(<App />)
    await screen.findByText('API ok')

    await userEvent.selectOptions(screen.getByLabelText('Rep'), 'R002')

    expect(screen.getByText(/Hugo Rossi · territory T002 \(East\)/)).toBeInTheDocument()
  })

  it('reports when the API is unreachable', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new Error('boom'))
    render(<App />)
    expect(await screen.findByText('API unreachable: boom')).toBeInTheDocument()
  })
})
