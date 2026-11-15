import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { RemoteBoundary } from './RemoteBoundary';

function Broken(): never {
  throw new Error('Loading script failed: remoteEntry.js');
}

describe('RemoteBoundary', () => {
  it('renders the remote when it loads', () => {
    render(
      <RemoteBoundary name="Advisor">
        <p>remote content</p>
      </RemoteBoundary>,
    );
    expect(screen.getByText('remote content')).toBeInTheDocument();
    expect(screen.queryByTestId('remote-fallback')).not.toBeInTheDocument();
  });

  it('shows a clear fallback instead of crashing the shell', () => {
    const logged = vi.spyOn(console, 'error').mockImplementation(() => {});
    render(
      <div>
        <header>shell header</header>
        <RemoteBoundary name="Advisor">
          <Broken />
        </RemoteBoundary>
      </div>,
    );
    expect(screen.getByText('shell header')).toBeInTheDocument();
    expect(screen.getByRole('alert')).toHaveTextContent('The Advisor is temporarily unavailable');
    expect(screen.getByRole('button', { name: 'Try again' })).toBeInTheDocument();
    expect(logged).toHaveBeenCalled();
  });
});
