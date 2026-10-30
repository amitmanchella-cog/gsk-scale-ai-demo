import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { HcpListResponse, HcpView } from './api'
import HcpList from './components/HcpList'

const hcps: HcpView[] = [
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
  {
    hcp_id: 'H00011',
    hcp_name: 'Dr Rhea Okafor',
    specialty: 'GP',
    segment: 'C',
    territory_id: 'T001',
    last_visit_date: '2025-09-24',
    days_since_last_visit: 5,
    open_follow_ups: 0,
    score: 0,
    reason: 'Visited 5 days ago (within 7 days)',
    factors: [],
  },
]

/** fetch mock that applies the query string like the backend does and records every requested URL */
function mockHcpApi() {
  const urls: string[] = []
  vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
    const url = String(input)
    urls.push(url)
    const { pathname, searchParams } = new URL(url, 'http://localhost')
    if (!/^\/api\/reps\/[^/]+\/hcps$/.test(pathname)) {
      return { ok: false, status: 404, json: async () => ({ detail: `unexpected fetch ${url}` }) } as Response
    }
    if (pathname.includes('/R999/')) {
      return { ok: false, status: 404, json: async () => ({ detail: "unknown rep 'R999'" }) } as Response
    }
    const specialty = searchParams.get('specialty')
    const segment = searchParams.get('segment')
    const minDays = searchParams.get('min_days_since_last_visit')
    const q = searchParams.get('q')?.toLowerCase()
    const rows = hcps.filter(
      (h) =>
        (!specialty || h.specialty === specialty) &&
        (!segment || h.segment === segment) &&
        (!minDays || h.days_since_last_visit === null || h.days_since_last_visit >= Number(minDays)) &&
        (!q || h.hcp_name.toLowerCase().includes(q)),
    )
    const body: HcpListResponse = {
      rep: { rep_id: 'R001', rep_name: 'Dev Okafor', territory_id: 'T001' },
      territory: { territory_id: 'T001', territory_name: 'South-01', region: 'South' },
      as_of: '2025-09-29',
      count: rows.length,
      hcps: rows,
    }
    return { ok: true, status: 200, json: async () => body } as Response
  })
  return urls
}

function renderList(props: Partial<React.ComponentProps<typeof HcpList>> = {}) {
  const onAdd = vi.fn(async () => {})
  const onAddDayChange = vi.fn()
  const utils = render(
    <HcpList repId="R001" addDay="Mon" onAddDayChange={onAddDayChange} onAdd={onAdd} planVersion={0} {...props} />,
  )
  return { ...utils, onAdd, onAddDayChange }
}

function rowNames(): string[] {
  const body = screen.getByRole('table').querySelector('tbody')!
  return within(body)
    .getAllByRole('row')
    .map((row) => within(row).getAllByRole('cell')[0].textContent ?? '')
}

function lastQuery(urls: string[]): URLSearchParams {
  return new URL(urls[urls.length - 1], 'http://localhost').searchParams
}

afterEach(() => {
  vi.restoreAllMocks()
})

describe('HcpList', () => {
  it('prompts for a rep and fetches nothing until one is selected', () => {
    const urls = mockHcpApi()
    renderList({ repId: '' })
    expect(screen.getByText('Select a rep to see their territory.')).toBeInTheDocument()
    expect(urls).toHaveLength(0)
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
  })

  it('renders the count line and every column for the selected rep', async () => {
    mockHcpApi()
    renderList()

    expect(await screen.findByText('3 HCPs in T001 South-01, as of 2025-09-29')).toBeInTheDocument()
    expect(screen.getAllByRole('columnheader').map((th) => th.textContent)).toEqual([
      'HCP',
      'Specialty',
      'Segment',
      'Last visit',
      'Open follow-ups',
      'Score',
      'Reason',
      'Add',
    ])
    expect(rowNames()).toEqual(['H00733 Dr Isla Xu', 'H00101 Dr Finn Singh', 'H00011 Dr Rhea Okafor'])
    const isla = screen.getByRole('row', { name: /Dr Isla Xu/ })
    expect(within(isla).getAllByRole('cell').map((td) => td.textContent)).toEqual([
      'H00733 Dr Isla Xu',
      'GP',
      'A',
      '51 days (2025-08-09)',
      '1',
      '100',
      'Segment A (+40), 51 days since last visit (+40, capped), 1 open follow-up (+20)',
      'Add',
    ])
    expect(screen.getByText('never visited')).toBeInTheDocument()
  })

  it('filters and search narrow the list', async () => {
    const urls = mockHcpApi()
    renderList()
    await screen.findByText('3 HCPs in T001 South-01, as of 2025-09-29')
    expect(lastQuery(urls).toString()).toBe('')

    await userEvent.selectOptions(screen.getByLabelText('Specialty'), 'GP')
    await waitFor(() => expect(lastQuery(urls).get('specialty')).toBe('GP'))
    await screen.findByText('2 HCPs in T001 South-01, as of 2025-09-29')
    expect(rowNames()).toEqual(['H00733 Dr Isla Xu', 'H00011 Dr Rhea Okafor'])

    await userEvent.selectOptions(screen.getByLabelText('Segment'), 'A')
    await waitFor(() => expect(lastQuery(urls).get('segment')).toBe('A'))
    expect(lastQuery(urls).get('specialty')).toBe('GP')
    await screen.findByText('1 HCPs in T001 South-01, as of 2025-09-29')
    expect(rowNames()).toEqual(['H00733 Dr Isla Xu'])

    await userEvent.selectOptions(screen.getByLabelText('Specialty'), '')
    await userEvent.selectOptions(screen.getByLabelText('Segment'), '')
    await screen.findByText('3 HCPs in T001 South-01, as of 2025-09-29')

    await userEvent.type(screen.getByLabelText('Days since last visit ≥'), '30')
    await waitFor(() => expect(lastQuery(urls).get('min_days_since_last_visit')).toBe('30'))
    await screen.findByText('2 HCPs in T001 South-01, as of 2025-09-29')
    expect(rowNames()).toEqual(['H00733 Dr Isla Xu', 'H00101 Dr Finn Singh'])

    const requestsBeforeSearch = urls.length
    await userEvent.type(screen.getByLabelText('Search by name'), 'xu')
    await waitFor(() => expect(lastQuery(urls).get('q')).toBe('xu'))
    expect(urls.length).toBe(requestsBeforeSearch + 1)
    expect(lastQuery(urls).get('min_days_since_last_visit')).toBe('30')
    await screen.findByText('1 HCPs in T001 South-01, as of 2025-09-29')
    expect(rowNames()).toEqual(['H00733 Dr Isla Xu'])

    await userEvent.clear(screen.getByLabelText('Search by name'))
    await userEvent.type(screen.getByLabelText('Search by name'), 'nobody')
    await waitFor(() => expect(lastQuery(urls).get('q')).toBe('nobody'))
    expect(await screen.findByText('No HCPs match the current filters.')).toBeInTheDocument()
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
  })

  it('Add buttons are named after the HCP and the selected day and call onAdd', async () => {
    mockHcpApi()
    const { onAdd, onAddDayChange, rerender } = renderList()
    await screen.findByText('3 HCPs in T001 South-01, as of 2025-09-29')

    const addIsla = screen.getByRole('button', { name: 'Add Dr Isla Xu to Monday' })
    await userEvent.click(addIsla)
    expect(onAdd).toHaveBeenCalledWith('H00733')
    expect(screen.getAllByRole('button', { name: /^Add .* to Monday$/ })).toHaveLength(3)

    await userEvent.selectOptions(screen.getByLabelText('Add to'), 'Tue')
    expect(onAddDayChange).toHaveBeenCalledWith('Tue')

    rerender(<HcpList repId="R001" addDay="Tue" onAddDayChange={onAddDayChange} onAdd={onAdd} planVersion={0} />)
    expect(screen.getByRole('button', { name: 'Add Dr Finn Singh to Tuesday' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Add Dr Isla Xu to Monday' })).not.toBeInTheDocument()
  })

  it('shows API errors inline', async () => {
    mockHcpApi()
    renderList({ repId: 'R999' })
    expect(await screen.findByRole('alert')).toHaveTextContent("Could not load HCPs: unknown rep 'R999'")
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
  })
})
