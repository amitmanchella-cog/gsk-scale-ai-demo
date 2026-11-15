import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { finding, graph, grid, summaries } from '../fixtures'
import { EndpointsPanel } from './EndpointsPanel'
import { FindingsPanel } from './FindingsPanel'
import { OperationForm } from './OperationForm'
import { ScheduleGrid } from './ScheduleGrid'
import { VersionTimeline } from './VersionTimeline'

const NONE = new Set<string>()

describe('ScheduleGrid', () => {
  it('renders the visit by activity matrix', () => {
    render(<ScheduleGrid grid={grid} editable highlight={NONE} onOperation={vi.fn()} />)
    expect(screen.getByTestId('cell-A-SPIRO-V-W12')).toHaveAttribute('data-scheduled', 'true')
    expect(screen.getByTestId('cell-A-VITALS-V-W12')).toHaveAttribute('data-scheduled', 'false')
    expect(screen.getByLabelText('Study day for Week 12')).toHaveValue(85)
    expect(within(screen.getByTestId('visit-header-V-W12')).getByText('Week 12')).toBeVisible()
  })

  it('moves a visit when its day is edited and confirmed with Enter', async () => {
    const onOperation = vi.fn()
    render(<ScheduleGrid grid={grid} editable highlight={NONE} onOperation={onOperation} />)
    const day = screen.getByLabelText('Study day for Week 12')
    await userEvent.clear(day)
    await userEvent.type(day, '99{Enter}')
    expect(onOperation).toHaveBeenCalledWith({ type: 'MoveVisit', visit_id: 'V-W12', day: 99 })
  })

  it('does nothing when the day is unchanged, and restores an empty or cancelled edit', async () => {
    const onOperation = vi.fn()
    render(<ScheduleGrid grid={grid} editable highlight={NONE} onOperation={onOperation} />)
    const day = screen.getByLabelText('Study day for Week 12')
    await userEvent.click(day)
    await userEvent.tab()
    await userEvent.clear(day)
    await userEvent.tab()
    expect(day).toHaveValue(85)
    await userEvent.clear(day)
    await userEvent.type(day, '120{Escape}')
    expect(day).toHaveValue(85)
    expect(onOperation).not.toHaveBeenCalled()
  })

  it('schedules and unschedules by clicking a cell', async () => {
    const onOperation = vi.fn()
    render(<ScheduleGrid grid={grid} editable highlight={NONE} onOperation={onOperation} />)
    await userEvent.click(screen.getByRole('button', { name: 'Vital signs at Week 12' }))
    await userEvent.click(screen.getByRole('button', { name: 'Spirometry at Week 12' }))
    expect(onOperation.mock.calls).toEqual([
      [{ type: 'ScheduleActivity', visit_id: 'V-W12', activity_id: 'A-VITALS' }],
      [{ type: 'UnscheduleActivity', visit_id: 'V-W12', activity_id: 'A-SPIRO' }],
    ])
  })

  it('is read only when not editable and highlights linked elements', () => {
    render(
      <ScheduleGrid grid={grid} editable={false} highlight={new Set(['V-W12', 'A-SPIRO'])} onOperation={vi.fn()} />,
    )
    expect(screen.getByLabelText('Study day for Week 12')).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Spirometry at Week 12' })).toBeDisabled()
    expect(screen.getByTestId('visit-header-V-W12')).toHaveClass('highlighted')
    expect(screen.getByTestId('activity-row-A-SPIRO')).toHaveClass('highlighted')
  })
})

describe('FindingsPanel', () => {
  it('shows the empty state for a consistent version', () => {
    render(<FindingsPanel findings={[]} onSelect={vi.fn()} />)
    expect(screen.getByTestId('findings-count')).toHaveTextContent('0')
    expect(screen.getByTestId('findings-empty')).toBeVisible()
  })

  it('lists warnings and reports the clicked finding', async () => {
    const onSelect = vi.fn()
    render(<FindingsPanel findings={[finding]} onSelect={onSelect} />)
    expect(screen.getByTestId('findings-count')).toHaveTextContent('1')
    const item = screen.getByTestId('finding')
    expect(item).toHaveAttribute('data-finding-id', 'unmet_endpoint_timepoint:EP-FEV1')
    expect(item).toHaveTextContent('Warning: Unmet endpoint timepoint')
    await userEvent.click(within(item).getByRole('button'))
    expect(onSelect).toHaveBeenCalledWith(finding)
  })
})

describe('EndpointsPanel', () => {
  it('changes an endpoint timing only when the week changed', async () => {
    const onOperation = vi.fn()
    render(
      <EndpointsPanel endpoints={graph.intent.endpoints} editable highlight={NONE} onOperation={onOperation} />,
    )
    const button = screen.getByTestId('retime-EP-FEV1')
    expect(button).toBeDisabled()
    const week = screen.getByLabelText('Timepoint week for Change from baseline in trough FEV1')
    await userEvent.clear(week)
    await userEvent.type(week, '14')
    await userEvent.click(button)
    expect(onOperation).toHaveBeenCalledWith({
      type: 'ChangeEndpointTiming',
      endpoint_id: 'EP-FEV1',
      week: 14,
    })
  })
})

describe('VersionTimeline', () => {
  it('lists versions with labels, finding counts and the head marker', async () => {
    const onSelect = vi.fn()
    render(
      <VersionTimeline versions={summaries} selectedId="v-1" headId="v-1" graph={graph} onSelect={onSelect} />,
    )
    const items = screen.getAllByTestId('timeline-version')
    expect(items).toHaveLength(2)
    expect(items[0]).toHaveTextContent('Reference study loaded')
    expect(items[0]).toHaveTextContent('0 findings')
    expect(items[1]).toHaveTextContent('v1 · head')
    expect(items[1]).toHaveTextContent('Move visit Week 12 to Day 99')
    expect(items[1]).toHaveTextContent('1 finding')
    expect(items[1]).toHaveClass('selected')
    await userEvent.click(within(items[0]!).getByRole('button'))
    expect(onSelect).toHaveBeenCalledWith('v-0')
  })
})

describe('OperationForm', () => {
  it('applies the JSON body of the chosen operation type', async () => {
    const onOperation = vi.fn()
    render(<OperationForm types={['MoveVisit', 'RemoveVisit']} editable onOperation={onOperation} />)
    await userEvent.selectOptions(screen.getByLabelText('Operation type'), 'RemoveVisit')
    await userEvent.click(screen.getByRole('button', { name: 'Apply operation' }))
    expect(onOperation).toHaveBeenCalledWith({ type: 'RemoveVisit', visit_id: 'V-W4' })
  })

  it('reports invalid JSON instead of calling the API', async () => {
    const onOperation = vi.fn()
    render(<OperationForm types={['MoveVisit']} editable onOperation={onOperation} />)
    await userEvent.clear(screen.getByLabelText('Body'))
    await userEvent.type(screen.getByLabelText('Body'), 'not json')
    await userEvent.click(screen.getByRole('button', { name: 'Apply operation' }))
    expect(screen.getByRole('alert')).toHaveTextContent('not valid JSON')
    expect(onOperation).not.toHaveBeenCalled()
  })
})
