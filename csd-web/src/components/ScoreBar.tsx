import type { Score } from '../api/types'
import { SCORE_ROWS } from '../lib/format'

/** The scores of the version on screen. Lower is better on all three. */
export function ScoreBar({ score }: { score: Score }) {
  return (
    <dl className="score-bar" data-testid="score-bar" aria-label="Scores of this version">
      {SCORE_ROWS.map(({ key, label, format }) => (
        <div key={key}>
          <dt>{label}</dt>
          <dd data-testid={`score-${key}`}>{format(score[key])}</dd>
        </div>
      ))}
    </dl>
  )
}
