import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import type { Plan, PlanVisit } from './api'
import PlanBuilder from './components/PlanBuilder'

const islaXu: PlanVisit = {
  visit_id: 1,
  hcp_id: 'H00733',
  hcp_name: 'Dr Isla Xu',
  specialty: 'GP',
  segment: 'A',
  score: 100,
  reason: 'Segment A (+40), 51 days since last visit (+40, capped), 1 open follow-up (+20)',
}

function makePlan(overrides: Partial<Plan> = {}): Plan {
  const dates = ['2025-09-29', '2025-09-30', '2025-10-01', '2025-10-02', '2025-10-03']
  return {
    rep_id: 'R001',
    territory_id: 'T001',
    week_start: '2025-09-29',
    as_of: '2025-09-29',
    max_visits_per_day: 6,
    total_visits: 0,
    days: (['Mon', 'Tue', 'Wed', 'Thu', 'Fri'] as const).map((day, i) => ({
      day,
      date: dates[i],
      count: 0,
      capacity: 6,
      visits: [],
    })),
    warnings: [],
    ...overrides,
  }
}

function renderPlan(plan: Plan | null, props: Partial<Parameters<typeof PlanBuilder>[0]> = {}) {
  const onRemove = vi.fn(async () => {})
  const onClear = vi.fn(async () => {})
  render(<PlanBuilder repId="R001" plan={plan} message={null} onRemove={onRemove} onClear={onClear} {...props} />)
  return { onRemove, onClear }
}

describe('PlanBuilder', () => {
  it('asks for a rep when none is selected', () => {
    renderPlan(null, { repId: '' })
    expect(screen.getByRole('heading', { level: 2, name: 'Weekly plan' })).toBeInTheDocument()
    expect(screen.getByText('Select a rep to start a plan.')).toBeInTheDocument()
  })

  it('blocks the 7th visit with a message', () => {
    const tueVisits = Array.from({ length: 6 }, (_, i) => ({ ...islaXu, visit_id: i + 1, hcp_id: `H0000${i}`, hcp_name: `Dr ${i}` }))
    const plan = makePlan({ total_visits: 6 })
    plan.days[1] = { ...plan.days[1], count: 6, visits: tueVisits }
    renderPlan(plan, { message: 'Tuesday already has 6 visits (max 6)' })

    expect(screen.getByRole('alert')).toHaveTextContent('Tuesday already has 6 visits (max 6)')
    expect(screen.getByRole('heading', { level: 3, name: 'Tuesday 6/6' })).toBeInTheDocument()
    expect(within(screen.getByRole('region', { name: 'Tuesday 6/6' })).getAllByRole('listitem')).toHaveLength(6)
  })

  it('does not render an alert without a message', () => {
    renderPlan(makePlan())
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('warns about unplanned overdue Segment A', () => {
    renderPlan(
      makePlan({
        warnings: [
          {
            type: 'overdue_segment_a',
            hcp_id: 'H00733',
            hcp_name: 'Dr Isla Xu',
            days: [],
            message: 'Dr Isla Xu (Segment A) is 51 days overdue and not planned',
          },
        ],
      }),
    )

    const warnings = screen.getByRole('list', { name: 'Plan warnings' })
    expect(warnings).toHaveAttribute('aria-live', 'polite')
    const item = within(warnings).getByText('Dr Isla Xu (Segment A) is 51 days overdue and not planned')
    expect(item).toBeVisible()
    expect(item).toHaveClass('warning')
  })

  it('shows duplicate warnings alongside overdue ones', () => {
    renderPlan(
      makePlan({
        warnings: [
          { type: 'duplicate', hcp_id: 'H00733', hcp_name: 'Dr Isla Xu', days: ['Mon', 'Tue'], message: 'Dr Isla Xu is planned twice (Mon, Tue)' },
          { type: 'overdue_segment_a', hcp_id: 'H00066', hcp_name: 'Dr Finn Singh', days: [], message: 'Dr Finn Singh (Segment A) is 57 days overdue and not planned' },
        ],
      }),
    )
    const items = within(screen.getByRole('list', { name: 'Plan warnings' })).getAllByRole('listitem')
    expect(items.map((li) => li.textContent)).toEqual([
      'Dr Isla Xu is planned twice (Mon, Tue)',
      'Dr Finn Singh (Segment A) is 57 days overdue and not planned',
    ])
  })

  it('renders five day columns with the week dates and n/6 counts', () => {
    const plan = makePlan({ total_visits: 1 })
    plan.days[0] = { ...plan.days[0], count: 1, visits: [islaXu] }
    renderPlan(plan)

    expect(screen.getByText('Week of 2025-09-29 · 1 visit')).toBeInTheDocument()
    const headings = screen.getAllByRole('heading', { level: 3 }).map((h) => h.textContent)
    expect(headings).toEqual(['Monday 1/6', 'Tuesday 0/6', 'Wednesday 0/6', 'Thursday 0/6', 'Friday 0/6'])
    const monday = screen.getByRole('region', { name: 'Monday 1/6' })
    expect(within(monday).getByText('2025-09-29')).toBeInTheDocument()
    expect(within(monday).getByText('Dr Isla Xu')).toBeInTheDocument()
    expect(within(monday).getByText('GP · Segment A · score 100')).toBeInTheDocument()
    expect(within(screen.getByRole('region', { name: 'Friday 0/6' })).getByText('No visits')).toBeInTheDocument()
  })

  it('names the remove button after the HCP and day and calls onRemove with the visit id', async () => {
    const plan = makePlan({ total_visits: 2 })
    plan.days[0] = { ...plan.days[0], count: 1, visits: [islaXu] }
    plan.days[3] = { ...plan.days[3], count: 1, visits: [{ ...islaXu, visit_id: 7 }] }
    const { onRemove } = renderPlan(plan)

    await userEvent.click(screen.getByRole('button', { name: 'Remove Dr Isla Xu from Thursday' }))

    expect(onRemove).toHaveBeenCalledTimes(1)
    expect(onRemove).toHaveBeenCalledWith(7)
    expect(screen.getByRole('button', { name: 'Remove Dr Isla Xu from Monday' })).toBeInTheDocument()
  })

  it('clears the plan and disables the button when the plan is empty', async () => {
    const { onClear } = renderPlan(makePlan())
    expect(screen.getByRole('button', { name: 'Clear plan' })).toBeDisabled()
    expect(onClear).not.toHaveBeenCalled()

    const plan = makePlan({ total_visits: 1 })
    plan.days[0] = { ...plan.days[0], count: 1, visits: [islaXu] }
    const second = renderPlan(plan)
    const buttons = screen.getAllByRole('button', { name: 'Clear plan' })
    const enabled = buttons.find((b) => !(b as HTMLButtonElement).disabled)!
    await userEvent.click(enabled)
    expect(second.onClear).toHaveBeenCalledTimes(1)
  })

  it('export downloads a CSV', () => {
    const plan = makePlan({ total_visits: 1 })
    plan.days[0] = { ...plan.days[0], count: 1, visits: [islaXu] }
    renderPlan(plan)

    const link = screen.getByRole('link', { name: 'Export CSV' })
    expect(link).toHaveAttribute('href', '/api/reps/R001/plan/export.csv')
    expect(link).toHaveAttribute('download')
    expect(link).not.toHaveAttribute('aria-disabled')
    expect(link).toHaveClass('button')
  })

  it('disables export for an empty plan', () => {
    renderPlan(makePlan())
    const link = screen.getByRole('link', { name: 'Export CSV' })
    expect(link).toHaveAttribute('aria-disabled', 'true')
    expect(link).not.toHaveAttribute('href')
    expect(link).toHaveAttribute('tabindex', '-1')
  })

  it('renders the export slot next to the actions', () => {
    renderPlan(makePlan(), { exportSlot: <button type="button">Extra</button> })
    expect(screen.getByRole('button', { name: 'Extra' })).toBeInTheDocument()
  })
})
