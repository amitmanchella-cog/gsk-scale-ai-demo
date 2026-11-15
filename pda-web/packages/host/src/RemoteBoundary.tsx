import { Component, type ReactNode } from 'react';

interface Props {
  name: string;
  children: ReactNode;
}

/** Keeps the shell alive when a federated remote fails to load or crashes. */
export class RemoteBoundary extends Component<Props, { failed: boolean }> {
  state = { failed: false };

  static getDerivedStateFromError() {
    return { failed: true };
  }

  componentDidCatch(error: unknown) {
    console.error(`Remote "${this.props.name}" failed`, error);
  }

  render() {
    if (!this.state.failed) return this.props.children;
    return (
      <section className="shell-fallback" role="alert" data-testid="remote-fallback">
        <h2>The {this.props.name} is temporarily unavailable</h2>
        <p>
          The rest of the application is still working. The {this.props.name} module could not be loaded, which usually
          means its server is down or unreachable.
        </p>
        <button type="button" className="shell-button" onClick={() => window.location.reload()}>
          Try again
        </button>
      </section>
    );
  }
}
