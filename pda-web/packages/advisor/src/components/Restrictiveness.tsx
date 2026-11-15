import { useState } from 'react';
import { categoryLabel, LEVEL_LABEL, number, TRIAL_URL } from '../format';
import type { Assessment, CriterionScore } from '../types';

export function Restrictiveness({ assessment }: { assessment: Assessment }) {
  const [onlyFlags, setOnlyFlags] = useState(false);
  const ordered = [...assessment.criteria].sort((a, b) => b.score - a.score);
  const shown = onlyFlags ? ordered.filter((score) => score.level === 'high') : ordered;
  const { summary } = assessment;

  return (
    <section className="pda-card" aria-labelledby="scores-heading" data-testid="restrictiveness">
      <h2 id="scores-heading">Eligibility restrictiveness</h2>
      <p className="pda-muted">
        Scored 0 to 100 against the {summary.n_similar} most similar benchmark trials. Higher means stricter than those
        trials.
      </p>

      <div className="pda-stats">
        <Stat label="Red flags" value={String(assessment.red_flags)} testId="red-flag-count" tone="high" />
        <Stat label="Overall score" value={String(assessment.overall_score)} testId="overall-score" />
        <Stat label="Benchmark median enrollment" value={number(summary.median_enrollment)} />
        <Stat label="Benchmark median sites" value={number(summary.median_site_count)} />
        <Stat label="Benchmark median criteria" value={number(summary.median_criteria_count)} />
      </div>

      <label className="pda-check">
        <input
          type="checkbox"
          checked={onlyFlags}
          data-testid="only-red-flags"
          onChange={(event) => setOnlyFlags(event.target.checked)}
        />
        Show red flags only
      </label>

      <ul className="pda-scores">
        {shown.map((score) => (
          <ScoreRow key={score.criterion_id} score={score} />
        ))}
      </ul>
    </section>
  );
}

function ScoreRow({ score }: { score: CriterionScore }) {
  return (
    <li className={`pda-score pda-score--${score.level}`} data-testid="criterion-score" data-level={score.level}>
      <div className="pda-score__head">
        <span className="pda-score__value" data-testid="score-value">
          {score.score}
        </span>
        <div className="pda-score__text">
          <span className={`pda-tag pda-tag--${score.level}`}>{LEVEL_LABEL[score.level]}</span>
          <span className="pda-tag">{categoryLabel(score.category)}</span>
          <span className="pda-tag">{score.kind}</span>
          <p>{score.text}</p>
        </div>
      </div>
      <div className="pda-meter" aria-hidden="true">
        <span style={{ width: `${score.score}%` }} />
      </div>
      <details className="pda-details">
        <summary>
          Why: {score.rationale} ({score.driving_trials.length} trials shown)
        </summary>
        <ul className="pda-trials" data-testid="driving-trials">
          {score.driving_trials.map((trial) => (
            <li key={trial.nct_id}>
              <a href={`${TRIAL_URL}${trial.nct_id}`} target="_blank" rel="noreferrer">
                {trial.nct_id}
              </a>{' '}
              {trial.detail}
            </li>
          ))}
        </ul>
      </details>
    </li>
  );
}

function Stat(props: { label: string; value: string; testId?: string; tone?: 'high' }) {
  return (
    <div className={`pda-stat${props.tone ? ` pda-stat--${props.tone}` : ''}`}>
      <span className="pda-stat__value" data-testid={props.testId}>
        {props.value}
      </span>
      <span className="pda-stat__label">{props.label}</span>
    </div>
  );
}
