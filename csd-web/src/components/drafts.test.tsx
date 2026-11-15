import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { Draft } from '../api/types'
import { draft } from '../fixtures'
import { DraftPanel } from './DraftPanel'

const NONE = new Set<string>()
const api = (result: Draft = draft) => ({
  drafts: vi.fn().mockResolvedValue(result),
})

describe('DraftPanel', () => {
  it('shows the requested section with its sentences and element IDs', async () => {
    const drafts = api()
    render(
      <DraftPanel
        versionId="v-0"
        section="8"
        highlight={NONE}
        onSection={vi.fn()}
        onHighlight={vi.fn()}
        api={drafts}
      />,
    )

    expect(await screen.findByTestId('draft-title')).toHaveTextContent(
      '8 Trial Assessments and Procedures',
    )
    expect(drafts.drafts).toHaveBeenCalledWith('v-0')
    expect(screen.getByTestId('draft-provider')).toHaveTextContent('template provider, offline')
    const sentences = screen.getAllByTestId('draft-sentence')
    expect(sentences).toHaveLength(2)
    expect(sentences[0]).toHaveAttribute('data-element-ids', 'V-W12 V-W12:A-SPIRO')
    expect(screen.getByTestId('draft-section-8')).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByTestId('draft-section-3')).toHaveAttribute('aria-pressed', 'false')
  })

  it('highlights every element of a clicked sentence, or one element from its ID', async () => {
    const onHighlight = vi.fn()
    render(
      <DraftPanel
        versionId="v-0"
        section="8"
        highlight={NONE}
        onSection={vi.fn()}
        onHighlight={onHighlight}
        api={api()}
      />,
    )

    await userEvent.click(await screen.findByRole('button', { name: /^Week 12 takes place/ }))
    expect(onHighlight).toHaveBeenLastCalledWith(['V-W12', 'V-W12:A-SPIRO'])
    await userEvent.click(screen.getByRole('button', { name: 'Highlight A-VITALS' }))
    expect(onHighlight).toHaveBeenLastCalledWith(['A-VITALS'])
  })

  it('marks the sentence whose elements are highlighted', async () => {
    render(
      <DraftPanel
        versionId="v-0"
        section="8"
        highlight={new Set(['V-W12', 'V-W12:A-SPIRO'])}
        onSection={vi.fn()}
        onHighlight={vi.fn()}
        api={api()}
      />,
    )

    const [first, second] = await screen.findAllByTestId('draft-sentence')
    expect(first).toHaveAttribute('aria-pressed', 'true')
    expect(second).toHaveAttribute('aria-pressed', 'false')
  })

  it('switches section', async () => {
    const onSection = vi.fn()
    render(
      <DraftPanel
        versionId="v-0"
        section="3"
        highlight={NONE}
        onSection={onSection}
        onHighlight={vi.fn()}
        api={api()}
      />,
    )

    expect(await screen.findByTestId('draft-title')).toHaveTextContent('3 Trial Objectives')
    await userEvent.click(screen.getByTestId('draft-section-5'))
    expect(onSection).toHaveBeenCalledWith('5')
  })

  it('drafts again when the version changes and never shows the old text meanwhile', async () => {
    const drafts = api()
    const props = {
      section: '8' as const,
      highlight: NONE,
      onSection: vi.fn(),
      onHighlight: vi.fn(),
      api: drafts,
    }
    const { rerender } = render(<DraftPanel versionId="v-0" {...props} />)
    await screen.findByTestId('draft-title')

    drafts.drafts.mockReturnValue(new Promise(() => {}))
    rerender(<DraftPanel versionId="v-1" {...props} />)

    expect(drafts.drafts).toHaveBeenLastCalledWith('v-1')
    expect(screen.queryByTestId('draft-title')).not.toBeInTheDocument()
    expect(screen.getByText('Drafting…')).toBeVisible()
  })

  it('says why a draft could not be made', async () => {
    const failing = {
      drafts: vi.fn().mockRejectedValue(new Error('version not found')),
    }
    render(
      <DraftPanel
        versionId="v-x"
        section="8"
        highlight={NONE}
        onSection={vi.fn()}
        onHighlight={vi.fn()}
        api={failing}
      />,
    )

    expect(await screen.findByTestId('draft-error')).toHaveTextContent('version not found')
  })
})
