import { number, phaseLabel, TRIAL_URL } from '../format';
import type { SimilarTrial } from '../types';

const STATUS: Record<string, string> = { COMPLETED: 'Completed', TERMINATED: 'Terminated' };

export function SimilarTrials({ trials }: { trials: SimilarTrial[] }) {
  return (
    <section className="pda-card" aria-labelledby="similar-heading" data-testid="similar-trials">
      <h2 id="similar-heading">Similar benchmark trials</h2>
      <p className="pda-muted">
        {trials.length} completed or terminated trials of the same indication and phase, closest by enrollment, age
        range and criteria mix. Source: ClinicalTrials.gov.
      </p>
      <details className="pda-details">
        <summary data-testid="similar-toggle">Show the {trials.length} trials</summary>
        <div className="pda-table-scroll">
          <table className="pda-table">
            <thead>
              <tr>
                <th scope="col">Trial</th>
                <th scope="col">Phase</th>
                <th scope="col">Status</th>
                <th scope="col" className="pda-num">
                  Enrolled
                </th>
                <th scope="col" className="pda-num">
                  Sites
                </th>
                <th scope="col" className="pda-num">
                  Months
                </th>
                <th scope="col" className="pda-num">
                  Per site / month
                </th>
              </tr>
            </thead>
            <tbody>
              {trials.map((trial) => (
                <tr key={trial.nct_id} data-testid="similar-trial">
                  <td>
                    <a href={`${TRIAL_URL}${trial.nct_id}`} target="_blank" rel="noreferrer">
                      {trial.nct_id}
                    </a>
                    <span className="pda-table__title">{trial.title}</span>
                  </td>
                  <td>{phaseLabel(trial.phase)}</td>
                  <td>
                    {STATUS[trial.overall_status] ?? trial.overall_status}
                    {trial.stop_category === 'low_accrual' && (
                      <span className="pda-tag pda-tag--high">Low accrual</span>
                    )}
                  </td>
                  <td className="pda-num">{number(trial.enrollment)}</td>
                  <td className="pda-num">{number(trial.site_count)}</td>
                  <td className="pda-num">{number(trial.duration_months, 1)}</td>
                  <td className="pda-num">{number(trial.accrual_rate_per_site_month, 2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </section>
  );
}
