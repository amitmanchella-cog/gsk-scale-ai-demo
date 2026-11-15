import { createMemoryHistory, RouterProvider } from '@tanstack/react-router';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { assessment, competing, protocol, samples, stubApi } from '../../advisor/src/test-data';
import { createAppRouter } from './router';

function renderAt(path: string) {
  const router = createAppRouter(createMemoryHistory({ initialEntries: [path] }));
  render(<RouterProvider router={router} />);
  return router;
}

describe('host shell', () => {
  it('shows the upload step at the root and moves to the protocol route after an upload', async () => {
    stubApi({
      '/api/samples': { body: samples },
      '/api/protocols': { status: 201, body: protocol },
      '/api/protocols/p-1': { body: protocol },
      '/api/protocols/p-1/assessment': { body: assessment },
      '/api/protocols/p-1/competing-trials': { body: competing },
    });
    const router = renderAt('/');
    expect(await screen.findByTestId('shell-header')).toHaveTextContent('Protocol Design Advisor');

    await userEvent.upload(await screen.findByTestId('protocol-file'), new File(['text'], 'weak.txt'));
    expect(await screen.findByTestId('fact-enrollment')).toHaveTextContent('900');
    expect(router.state.location.pathname).toBe('/protocols/p-1');

    await userEvent.click(screen.getByTestId('start-over'));
    expect(await screen.findByTestId('protocol-file')).toBeInTheDocument();
    expect(router.state.location.pathname).toBe('/');
  });

  it('opens a protocol from its URL', async () => {
    stubApi({
      '/api/protocols/p-1': { body: protocol },
      '/api/protocols/p-1/assessment': { body: assessment },
      '/api/protocols/p-1/competing-trials': { body: competing },
    });
    renderAt('/protocols/p-1');
    expect(await screen.findByTestId('red-flag-count')).toHaveTextContent('1');
  });

  it('has an About page owned by the shell', async () => {
    stubApi({ '/api/samples': { body: samples } });
    renderAt('/');
    await userEvent.click(await screen.findByRole('link', { name: 'About' }));
    expect(await screen.findByTestId('about')).toHaveTextContent('No external model is called');
  });
});
