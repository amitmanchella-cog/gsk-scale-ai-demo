import { useEffect, useState } from 'react'
import { api as defaultApi } from '../api/client'
import type { Api } from '../api/client'
import type { Draft, SectionNumber } from '../api/types'

interface Props {
  versionId: string
  section: SectionNumber
  highlight: ReadonlySet<string>
  onSection: (section: SectionNumber) => void
  /** Highlight the graph elements a sentence was written from. */
  onHighlight: (elementIds: string[]) => void
  api?: Pick<Api, 'drafts'>
}

const sameIds = (ids: string[], highlight: ReadonlySet<string>) =>
  ids.length === highlight.size && ids.every((id) => highlight.has(id))

/** ICH M11 sections drafted from the version on screen. Each sentence links to its elements. */
export function DraftPanel({
  versionId,
  section,
  highlight,
  onSection,
  onHighlight,
  api = defaultApi,
}: Props) {
  const [draft, setDraft] = useState<{
    versionId: string
    draft: Draft
  } | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    setError(null)
    api
      .drafts(versionId)
      .then((next) => {
        if (!cancelled) setDraft({ versionId, draft: next })
      })
      .catch((caught: unknown) => {
        if (!cancelled) setError(caught instanceof Error ? caught.message : String(caught))
      })
    return () => {
      cancelled = true
    }
  }, [api, versionId])

  if (error)
    return (
      <p className="error" role="alert" data-testid="draft-error">
        Could not draft this version: {error}
      </p>
    )
  // Never show the text of another version under this version's header.
  if (!draft || draft.versionId !== versionId) return <p className="muted">Drafting…</p>
  const current = draft.draft.sections.find((candidate) => candidate.number === section)

  return (
    <section className="panel draft" data-testid="draft-panel">
      <div className="draft-sections" role="group" aria-label="M11 section">
        {draft.draft.sections.map(({ number, title }) => (
          <button
            key={number}
            type="button"
            aria-pressed={number === section}
            data-testid={`draft-section-${number}`}
            onClick={() => onSection(number)}
          >
            {number} {title}
          </button>
        ))}
      </div>
      <p className="muted" data-testid="draft-provider">
        Drafted from this version's graph by the {draft.draft.provider} provider, offline. Select a
        sentence to highlight the graph elements it was written from.
      </p>
      {current && (
        <>
          <h2 data-testid="draft-title">
            {current.number} {current.title}
          </h2>
          <ol className="draft-sentences">
            {current.sentences.map((sentence, index) => {
              const selected = sameIds(sentence.element_ids, highlight)
              return (
                <li key={index}>
                  <button
                    type="button"
                    className="sentence"
                    aria-pressed={selected}
                    data-testid="draft-sentence"
                    data-element-ids={sentence.element_ids.join(' ')}
                    onClick={() => onHighlight(sentence.element_ids)}
                  >
                    {sentence.text}
                  </button>
                  <span className="element-ids">
                    {sentence.element_ids.map((id) => (
                      <button
                        key={id}
                        type="button"
                        className="element-id"
                        aria-label={`Highlight ${id}`}
                        aria-pressed={highlight.size === 1 && highlight.has(id)}
                        onClick={() => onHighlight([id])}
                      >
                        {id}
                      </button>
                    ))}
                  </span>
                </li>
              )
            })}
          </ol>
        </>
      )}
    </section>
  )
}
