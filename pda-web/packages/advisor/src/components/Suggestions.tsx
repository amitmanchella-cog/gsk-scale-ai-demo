import { useMutation } from '@tanstack/react-query';
import { useState } from 'react';
import { api, reportUrl } from '../api';
import { months, number, percent, TRIAL_URL } from '../format';
import type { Suggestion, Suggestions as SuggestionsData, WhatIf } from '../types';

interface Result {
  data: WhatIf;
  /** Time from the click to the updated forecast, measured in the browser. */
  seconds: number;
}

export function Suggestions({ protocolId, data }: { protocolId: string; data: SuggestionsData }) {
  const [selected, setSelected] = useState<string[]>([]);
  const chosen = data.suggestions.filter((suggestion) => selected.includes(suggestion.id));

  const whatIf = useMutation({
    mutationFn: async (suggestions: Suggestion[]): Promise<Result> => {
      const started = performance.now();
      const result = await api.whatIf(
        protocolId,
        suggestions.map((suggestion) => suggestion.change),
      );
      return { data: result, seconds: (performance.now() - started) / 1000 };
    },
  });

  function toggle(id: string) {
    setSelected((current) => (current.includes(id) ? current.filter((item) => item !== id) : [...current, id]));
    whatIf.reset();
  }

  return (
    <section className="pda-card" aria-labelledby="suggestions-heading" data-testid="suggestions">
      <h2 id="suggestions-heading">Suggested design changes</h2>
      <p className="pda-muted">
        Every number below is computed from the benchmark dataset and each suggestion cites the trials behind it. Tick
        changes to try them in the what-if panel.
      </p>
      {data.suggestions.length === 0 && <p>No change was found that shortens the forecast.</p>}

      <ul className="pda-scores">
        {data.suggestions.map((suggestion) => (
          <li key={suggestion.id} className="pda-score pda-suggestion" data-testid="suggestion">
            <label className="pda-check pda-suggestion__pick">
              <input
                type="checkbox"
                data-testid="suggestion-pick"
                checked={selected.includes(suggestion.id)}
                onChange={() => toggle(suggestion.id)}
              />
              <strong data-testid="suggestion-title">{suggestion.title}</strong>
            </label>
            <span className="pda-tag pda-tag--low" data-testid="suggestion-saving">
              saves {months(suggestion.months_saved)} at P50
            </span>
            <p>{suggestion.rationale}</p>
            <details className="pda-details">
              <summary>
                Evidence: <span data-testid="citation-count">{suggestion.cited_trial_ids.length}</span> benchmark trials
                cited
              </summary>
              <ul className="pda-trials" data-testid="suggestion-citations">
                {suggestion.cited_trial_ids.map((id) => (
                  <li key={id}>
                    <a href={`${TRIAL_URL}${id}`} target="_blank" rel="noreferrer" data-testid="citation">
                      {id}
                    </a>
                  </li>
                ))}
              </ul>
              <dl className="pda-evidence">
                {suggestion.evidence.map((item) => (
                  <div key={item.metric}>
                    <dt>{item.label}</dt>
                    <dd>{number(item.value, Number.isInteger(item.value) ? 0 : 1)}</dd>
                  </div>
                ))}
              </dl>
            </details>
          </li>
        ))}
      </ul>

      <div className="pda-whatif" data-testid="what-if">
        <h3>What-if</h3>
        {chosen.length === 0 ? (
          <p className="pda-muted">No change selected yet.</p>
        ) : (
          <ul className="pda-trials" data-testid="what-if-selected">
            {chosen.map((suggestion) => (
              <li key={suggestion.id}>{suggestion.title}</li>
            ))}
          </ul>
        )}
        <button
          type="button"
          className="pda-button pda-button--primary"
          data-testid="what-if-run"
          disabled={chosen.length === 0 || whatIf.isPending}
          onClick={() => whatIf.mutate(chosen)}
        >
          {whatIf.isPending ? 'Recomputing…' : 'Recompute forecast'}
        </button>
        {whatIf.error && (
          <p role="alert" className="pda-alert">
            {whatIf.error.message}
          </p>
        )}
        {whatIf.data && <WhatIfResult result={whatIf.data} />}
      </div>

      <div className="pda-whatif" data-testid="export">
        <h3>Design-review report</h3>
        <p className="pda-muted" data-testid="export-summary">
          {chosen.length === 0
            ? 'The report covers the draft as uploaded. Tick changes above to include them as accepted changes.'
            : `The report includes ${chosen.length} accepted ${chosen.length === 1 ? 'change' : 'changes'}: ${chosen
                .map((suggestion) => suggestion.title)
                .join('; ')}.`}
        </p>
        <div className="pda-actions">
          {(['html', 'pdf'] as const).map((format) => (
            <a
              key={format}
              className="pda-button"
              data-testid={`export-${format}`}
              href={reportUrl(
                protocolId,
                format,
                chosen.map((suggestion) => suggestion.id),
              )}
              download
            >
              Export {format.toUpperCase()}
            </a>
          ))}
        </div>
      </div>
    </section>
  );
}

function WhatIfResult({ result }: { result: Result }) {
  const { baseline, scenario } = result.data;
  return (
    <div data-testid="what-if-result" aria-live="polite">
      <div className="pda-table-scroll">
        <table className="pda-table">
          <thead>
            <tr>
              <th scope="col"></th>
              <th scope="col">Draft</th>
              <th scope="col">With changes</th>
              <th scope="col">Difference</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <th scope="row">P50 months</th>
              <td data-testid="what-if-baseline-p50">{number(baseline.p50_months, 1)}</td>
              <td data-testid="what-if-p50">{number(scenario.p50_months, 1)}</td>
              <td data-testid="what-if-p50-saved">{number(-result.data.p50_months_saved, 1)}</td>
            </tr>
            <tr>
              <th scope="row">P90 months</th>
              <td>{number(baseline.p90_months, 1)}</td>
              <td data-testid="what-if-p90">{number(scenario.p90_months, 1)}</td>
              <td>{number(-result.data.p90_months_saved, 1)}</td>
            </tr>
            <tr>
              <th scope="row">Sites</th>
              <td>{baseline.sites}</td>
              <td>{scenario.sites}</td>
              <td>{number(scenario.sites - baseline.sites)}</td>
            </tr>
            <tr>
              <th scope="row">Termination risk</th>
              <td>{percent(baseline.termination_risk.risk)}</td>
              <td data-testid="what-if-risk">{percent(scenario.termination_risk.risk)}</td>
              <td></td>
            </tr>
          </tbody>
        </table>
      </div>
      <p className="pda-muted">
        Recomputed in <span data-testid="what-if-seconds">{number(result.seconds, 2)}</span> seconds with the same seed
        and benchmark trials as the draft forecast.
      </p>
    </div>
  );
}
