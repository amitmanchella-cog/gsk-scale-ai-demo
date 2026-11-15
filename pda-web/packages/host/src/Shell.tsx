import { Link, Outlet } from '@tanstack/react-router';

export function Shell() {
  return (
    <div className="shell">
      <header className="shell-header" data-testid="shell-header">
        <Link to="/" className="shell-brand">
          Protocol Design Advisor
        </Link>
        <nav aria-label="Main" className="shell-nav">
          <Link to="/" activeOptions={{ exact: true }}>
            Advisor
          </Link>
          <Link to="/about">About</Link>
        </nav>
      </header>
      <main className="shell-main">
        <Outlet />
      </main>
      <footer className="shell-footer">
        Demo with public ClinicalTrials.gov data and synthetic protocols. No person-level data.
      </footer>
    </div>
  );
}

export function About() {
  return (
    <section className="shell-card" data-testid="about">
      <h1>About this demo</h1>
      <p>
        The Advisor reads a draft clinical-trial protocol, extracts its design and compares it with completed and
        terminated trials registered on ClinicalTrials.gov.
      </p>
      <ul>
        <li>Benchmark trials: public study-level records for asthma, COPD and type 2 diabetes, phases 2 and 3.</li>
        <li>Extraction: a deterministic rule-based provider. No external model is called.</li>
        <li>Every number shown is computed from the benchmark dataset.</li>
        <li>This shell loads the Advisor as a separate module, so the shell keeps working if that module is down.</li>
      </ul>
    </section>
  );
}
