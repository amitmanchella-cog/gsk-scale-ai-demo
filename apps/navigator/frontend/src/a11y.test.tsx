/**
 * S5.4 / NFR-4 — keyboard accessibility of the whole page: every control is a native element reachable with Tab in
 * DOM order, operable with Enter, has an accessible name; warnings are live regions and errors are alerts.
 */
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import App from './App'
import type { HcpListResponse, Plan } from './api'

const health = { status: 'ok', version: '0.1.0', data_dir: '/repo/data', as_of: '2025-09-29', row_counts: { reps: 1 } }
const reps = [{ rep_id: 'R001', rep_name: 'Dev Okafor', territory_id: 'T001', region: 'South', hire_date: '2022-03-03' }]

const hcpList: HcpListResponse = {
  rep: { rep_id: 'R001', rep_name: 'Dev Okafor', territory_id: 'T001' },
  territory: { territory_id: 'T001', territory_name: 'South-01', region: 'South' },
  as_of: '2025-09-29',
  count: 2,
  hcps: [
    {
      hcp_id: 'H00733',
      hcp_name: 'Dr Isla Xu',
      specialty: 'GP',
      segment: 'A',
      territory_id: 'T001',
      last_visit_date: '2025-08-09',
      days_since_last_visit: 51,
      open_follow_ups: 1,
      score: 100,
      reason: 'Segment A (+40), 51 days since last visit (+40, capped), 1 open follow-up (+20)',
      factors: [],
    },
    {
      hcp_id: 'H00101',
      hcp_name: 'Dr Finn Singh',
      specialty: 'Cardiology',
      segment: 'B',
      territory_id: 'T001',
      last_visit_date: null,
      days_since_last_visit: null,
      open_follow_ups: 0,
      score: 65,
      reason: 'Segment B (+25), never visited (+40, capped)',
      factors: [],
    },
  ],
}

const dates = ['2025-09-29', '2025-09-30', '2025-10-01', '2025-10-02', '2025-10-03']
const plan: Plan = {
  rep_id: 'R001',
  territory_id: 'T001',
  week_start: '2025-09-29',
  as_of: '2025-09-29',
  max_visits_per_day: 6,
  total_visits: 1,
  days: (['Mon', 'Tue', 'Wed', 'Thu', 'Fri'] as const).map((day, i) => ({
    day,
    date: dates[i],
    count: day === 'Tue' ? 1 : 0,
    capacity: 6,
    visits:
      day === 'Tue'
        ? [{ visit_id: 1, hcp_id: 'H00101', hcp_name: 'Dr Finn Singh', specialty: 'Cardiology', segment: 'B', score: 65, reason: 'never visited' }]
        : [],
  })),
  warnings: [
    {
      type: 'overdue_segment_a',
      hcp_id: 'H00733',
      hcp_name: 'Dr Isla Xu',
      days: [],
      message: 'Dr Isla Xu (Segment A) is 51 days overdue and not planned',
    },
  ],
}

function jsonResponse(body: unknown, status = 200) {
  return { ok: status < 400, status, json: async () => body } as Response
}

/** GET routes by path; POST /reps/R001/plan/visits always answers 409 so the error path can be exercised. */
function mockApi() {
  return vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
    const path = new URL(String(input), 'http://localhost').pathname.replace(/^\/api/, '')
    const method = init?.method ?? 'GET'
    if (method === 'POST' && path === '/reps/R001/plan/visits') {
      return jsonResponse({ detail: 'Monday already has 6 visits (max 6)' }, 409)
    }
    const routes: Record<string, unknown> = {
      '/health': health,
      '/reps': reps,
      '/reps/R001/hcps': hcpList,
      '/reps/R001/plan': plan,
    }
    if (method === 'GET' && path in routes) return jsonResponse(routes[path])
    return jsonResponse({ detail: `unexpected ${method} ${path}` }, 404)
  })
}

afterEach(() => {
  vi.restoreAllMocks()
})

async function renderWithRep() {
  mockApi()
  const user = userEvent.setup()
  render(<App />)
  await screen.findByText('API ok')
  await user.selectOptions(screen.getByLabelText('Rep'), 'R001')
  await screen.findByRole('button', { name: 'Add Dr Isla Xu to Monday' })
  await screen.findByRole('button', { name: 'Remove Dr Finn Singh from Tuesday' })
  return user
}

function inDomOrder(elements: HTMLElement[]) {
  return elements.every(
    (el, i) => i === 0 || Boolean(elements[i - 1].compareDocumentPosition(el) & Node.DOCUMENT_POSITION_FOLLOWING),
  )
}

describe('keyboard accessibility (S5.4)', () => {
  it('tabs through every control in DOM order', async () => {
    const user = await renderWithRep()

    const expected: HTMLElement[] = [
      screen.getByLabelText('Rep'),
      screen.getByLabelText('Specialty'),
      screen.getByLabelText('Segment'),
      screen.getByLabelText('Days since last visit ≥'),
      screen.getByLabelText('Search by name'),
      screen.getByLabelText('Add to'),
      ...screen.getAllByRole('button', { name: /^Add .+ to .+$/ }),
      ...screen.getAllByRole('button', { name: /^Remove .+ from .+$/ }),
      screen.getByRole('button', { name: 'Clear plan' }),
      ...screen.queryAllByRole('link', { name: 'Export CSV' }),
    ]
    expect(screen.getAllByRole('button', { name: /^Add .+ to .+$/ })).toHaveLength(2)
    expect(screen.getAllByRole('button', { name: /^Remove .+ from .+$/ })).toHaveLength(1)
    expect(inDomOrder(expected)).toBe(true)

    ;(document.activeElement as HTMLElement | null)?.blur()
    expect(document.activeElement).toBe(document.body)
    const visited: Element[] = []
    for (let i = 0; i < expected.length; i++) {
      await user.tab()
      visited.push(document.activeElement as Element)
    }
    expect(visited).toEqual(expected)

    await user.tab()
    expect(document.activeElement).toBe(document.body)
  })

  it('gives every button and link a non-empty accessible name', async () => {
    await renderWithRep()
    const buttons = screen.getAllByRole('button')
    expect(buttons.length).toBeGreaterThanOrEqual(4)
    expect(screen.getAllByRole('button', { name: /\S/ })).toHaveLength(buttons.length)
    const links = screen.queryAllByRole('link')
    expect(screen.queryAllByRole('link', { name: /\S/ })).toHaveLength(links.length)
    for (const control of screen.getAllByRole('combobox')) {
      expect(control).toHaveAccessibleName()
    }
    for (const control of [...screen.getAllByRole('spinbutton'), ...screen.getAllByRole('searchbox')]) {
      expect(control).toHaveAccessibleName()
    }
  })

  it('announces warnings via aria-live and errors via role="alert"', async () => {
    const user = await renderWithRep()

    const warnings = screen.getByRole('list', { name: 'Plan warnings' })
    expect(warnings).toHaveAttribute('aria-live', 'polite')
    expect(within(warnings).getByText('Dr Isla Xu (Segment A) is 51 days overdue and not planned')).toBeInTheDocument()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()

    const add = screen.getByRole('button', { name: 'Add Dr Isla Xu to Monday' })
    add.focus()
    await user.keyboard('{Enter}')

    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent('Monday already has 6 visits (max 6)')
  })

  it('operates the day picker and Add with the keyboard only', async () => {
    const user = await renderWithRep()
    const fetchMock = globalThis.fetch as unknown as ReturnType<typeof vi.fn>

    await user.selectOptions(screen.getByLabelText('Add to'), 'Wed')
    const add = screen.getByRole('button', { name: 'Add Dr Finn Singh to Wednesday' })
    add.focus()
    await user.keyboard(' ')

    const post = fetchMock.mock.calls.find(([, init]) => (init as RequestInit | undefined)?.method === 'POST')
    expect(post).toBeDefined()
    expect(String(post?.[0])).toMatch(/\/reps\/R001\/plan\/visits$/)
    expect(JSON.parse(String((post?.[1] as RequestInit).body))).toEqual({ hcp_id: 'H00101', day: 'Wed' })
  })
})
