import { ageRange, categoryLabel, indicationLabel, number, phaseLabel } from '../format';
import type { Protocol } from '../types';

export function DesignSummary({ protocol }: { protocol: Protocol }) {
  const { design } = protocol;
  const inclusion = design.criteria.filter((criterion) => criterion.kind === 'inclusion');
  const exclusion = design.criteria.filter((criterion) => criterion.kind === 'exclusion');

  return (
    <section className="pda-card" aria-labelledby="design-heading" data-testid="design">
      <h2 id="design-heading">Extracted design</h2>
      <p className="pda-muted">
        {design.title ?? protocol.document} <span className="pda-nowrap">({protocol.document})</span>
      </p>

      {design.warnings.length > 0 && (
        <ul className="pda-alert" data-testid="design-warnings">
          {design.warnings.map((warning) => (
            <li key={warning}>{warning}</li>
          ))}
        </ul>
      )}

      <dl className="pda-facts">
        <Fact label="Indication" value={indicationLabel(design.indication)} testId="fact-indication" />
        <Fact label="Phase" value={phaseLabel(design.phase)} testId="fact-phase" />
        <Fact label="Target enrollment" value={number(design.target_enrollment)} testId="fact-enrollment" />
        <Fact label="Sites" value={number(design.site_count)} testId="fact-sites" />
        <Fact label="Age" value={ageRange(design.population)} testId="fact-age" />
        <Fact
          label="Countries"
          testId="fact-countries"
          value={
            design.planned_countries.length
              ? design.planned_countries
                  .map(({ country, sites }) => (sites === null ? country : `${country} (${sites})`))
                  .join(', ')
              : 'Not found'
          }
        />
      </dl>
      {design.population.summary && <p>{design.population.summary}</p>}

      <details className="pda-details">
        <summary data-testid="criteria-toggle">
          {inclusion.length} inclusion and {exclusion.length} exclusion criteria
        </summary>
        <div className="pda-columns">
          {[
            { title: 'Inclusion', items: inclusion },
            { title: 'Exclusion', items: exclusion },
          ].map(({ title, items }) => (
            <div key={title}>
              <h3>{title}</h3>
              <ol className="pda-criteria">
                {items.map((criterion) => (
                  <li key={criterion.id} data-testid={`criterion-${criterion.id}`}>
                    <span className="pda-tag">{categoryLabel(criterion.category)}</span> {criterion.text}
                  </li>
                ))}
              </ol>
            </div>
          ))}
        </div>
      </details>
    </section>
  );
}

function Fact({ label, value, testId }: { label: string; value: string; testId: string }) {
  return (
    <div className="pda-fact">
      <dt>{label}</dt>
      <dd data-testid={testId}>{value}</dd>
    </div>
  );
}
