import { LEVEL_LABEL, number, phaseLabel, TRIAL_URL } from '../format';
import type { CompetingTrials as CompetingTrialsData, Level } from '../types';

const CROWDING: Record<Level, string> = { high: 'Crowded', moderate: 'Busy', low: 'Open' };

export function CompetingTrials({ data }: { data: CompetingTrialsData }) {
  return (
    <section className="pda-card" aria-labelledby="competing-heading" data-testid="competing">
      <h2 id="competing-heading">Competing recruiting trials</h2>
      <p className="pda-muted">
        Trials in the same indication that are recruiting now in each planned country. Source: ClinicalTrials.gov.
      </p>
      {data.countries.length === 0 && <p>No planned countries were found in the protocol.</p>}
      <div className="pda-columns">
        {data.countries.map((country) => (
          <div key={country.country} className="pda-country" data-testid="competing-country">
            <h3>
              {country.country}{' '}
              <span className={`pda-tag pda-tag--${country.crowding}`} title={LEVEL_LABEL[country.crowding]}>
                {CROWDING[country.crowding]}
              </span>
            </h3>
            <p>
              <strong data-testid="competing-count">{country.competing_trials}</strong> recruiting trials with{' '}
              {number(country.competing_sites)} sites, against {number(country.planned_sites)} planned here.
            </p>
            {country.trials.length > 0 && (
              <details className="pda-details">
                <summary>Largest {country.trials.length} by sites in country</summary>
                <ul className="pda-trials">
                  {country.trials.map((trial) => (
                    <li key={trial.nct_id}>
                      <a href={`${TRIAL_URL}${trial.nct_id}`} target="_blank" rel="noreferrer">
                        {trial.nct_id}
                      </a>{' '}
                      {phaseLabel(trial.phase)}, {trial.sites_in_country} sites. {trial.title}
                    </li>
                  ))}
                </ul>
              </details>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}
