import { LEVEL_LABEL, number, percent, TRIAL_URL } from '../format';
import type { Forecast } from '../types';

export function ForecastCard({ forecast }: { forecast: Forecast }) {
  const risk = forecast.termination_risk;
  return (
    <section className="pda-card" aria-labelledby="forecast-heading" data-testid="forecast">
      <h2 id="forecast-heading">Enrollment forecast</h2>
      <p className="pda-muted">
        Months to enroll {number(forecast.target_enrollment)} patients on {forecast.sites} sites.{' '}
        {number(forecast.simulations)} seeded simulations, with sites opening over {number(forecast.ramp_months)}{' '}
        months.
      </p>

      <div className="pda-stats">
        <div className="pda-stat">
          <span className="pda-stat__value" data-testid="forecast-p50">
            {number(forecast.p50_months, 1)}
          </span>
          <span className="pda-stat__label">P50 months (half of simulations finish by then)</span>
        </div>
        <div className="pda-stat">
          <span className="pda-stat__value" data-testid="forecast-p90">
            {number(forecast.p90_months, 1)}
          </span>
          <span className="pda-stat__label">P90 months (9 in 10 finish by then)</span>
        </div>
        <div className={`pda-stat pda-stat--${risk.level}`} data-testid="termination-risk" data-level={risk.level}>
          <span className="pda-stat__value" data-testid="termination-risk-value">
            {percent(risk.risk)}
          </span>
          <span className="pda-stat__label">
            Risk of termination for low accrual{' '}
            <span className={`pda-tag pda-tag--${risk.level}`}>{LEVEL_LABEL[risk.level]}</span>
          </span>
        </div>
      </div>

      <details className="pda-details">
        <summary>How these numbers are computed</summary>
        <ul className="pda-trials">
          <li>
            Per-site accrual is drawn from{' '}
            {forecast.rate_source === 'similar_trials'
              ? `${forecast.n_rates} similar benchmark trials`
              : 'the indication and phase benchmark'}{' '}
            (median {number(forecast.median_benchmark_rate, 2)} patients per site per month).
          </li>
          <li>
            Narrow eligibility windows multiply that rate by {number(forecast.rate_multiplier, 2)}. This is a modelling
            assumption.
          </li>
          <li>
            Termination risk: {risk.similar_low_accrual} of {risk.n_similar} similar trials were terminated for low
            accrual ({percent(risk.indication_phase_share)} across the indication and phase). The smoothed share,{' '}
            {percent(risk.baseline_share)}, is multiplied by {number(risk.adjustment, 2)} because of the forecast length
            against the benchmark median duration.
          </li>
          <li data-testid="termination-trials">
            Trials terminated for low accrual behind the estimate:{' '}
            {risk.trial_ids.map((id, index) => (
              <span key={id}>
                {index > 0 && ', '}
                <a href={`${TRIAL_URL}${id}`} target="_blank" rel="noreferrer">
                  {id}
                </a>
              </span>
            ))}
          </li>
        </ul>
      </details>
    </section>
  );
}
