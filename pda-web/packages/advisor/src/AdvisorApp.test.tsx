import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import AdvisorApp from './AdvisorApp';
import { assessment, competing, protocol, samples, stubApi } from './test-data';

const reviewRoutes = {
  '/api/protocols/p-1': { body: protocol },
  '/api/protocols/p-1/assessment': { body: assessment },
  '/api/protocols/p-1/competing-trials': { body: competing },
};

describe('AdvisorApp', () => {
  it('uploads a chosen file and shows the review', async () => {
    const calls = stubApi({
      '/api/samples': { body: samples },
      '/api/protocols': { status: 201, body: protocol },
      ...reviewRoutes,
    });
    render(<AdvisorApp />);
    await userEvent.upload(screen.getByTestId('protocol-file'), new File(['text'], 'weak.txt'));

    expect(await screen.findByTestId('fact-indication')).toHaveTextContent('Type 2 diabetes');
    expect(screen.getByTestId('fact-countries')).toHaveTextContent('United States (5), China');
    expect(screen.getByTestId('fact-age')).toHaveTextContent('40 to 60 years');
    expect(await screen.findByTestId('red-flag-count')).toHaveTextContent('1');
    expect(calls.some((call) => call.path === '/api/protocols' && call.init?.method === 'POST')).toBe(true);
  });

  it('orders scores from most to least restrictive and can show red flags only', async () => {
    stubApi(reviewRoutes);
    render(<AdvisorApp protocolId="p-1" onProtocolChange={() => {}} />);

    const rows = await screen.findAllByTestId('criterion-score');
    expect(rows.map((row) => within(row).getByTestId('score-value').textContent)).toEqual(['100', '10']);
    expect(within(rows[0]!).getByRole('link', { name: 'NCT00000001' })).toHaveAttribute(
      'href',
      'https://clinicaltrials.gov/study/NCT00000001',
    );

    await userEvent.click(screen.getByTestId('only-red-flags'));
    expect(screen.getAllByTestId('criterion-score')).toHaveLength(1);
  });

  it('shows competing trials per country and the similar trials table', async () => {
    stubApi(reviewRoutes);
    render(<AdvisorApp protocolId="p-1" onProtocolChange={() => {}} />);

    const countries = await screen.findAllByTestId('competing-country');
    expect(countries).toHaveLength(2);
    expect(countries[0]).toHaveTextContent('Crowded');
    expect(within(countries[0]!).getByTestId('competing-count')).toHaveTextContent('31');
    expect(countries[1]).toHaveTextContent('Open');

    const row = await screen.findByTestId('similar-trial');
    expect(row).toHaveTextContent('Terminated');
    expect(row).toHaveTextContent('Low accrual');
    expect(row).toHaveTextContent('n/a');
  });

  it('loads a sample protocol through the same upload path', async () => {
    const onProtocolChange = vi.fn();
    stubApi({
      '/api/samples': { body: samples },
      '/api/samples/t2d_phase3_weak': { body: 'Title: Diabetes study' },
      '/api/protocols': { status: 201, body: protocol },
    });
    render(<AdvisorApp onProtocolChange={onProtocolChange} />);

    const sample = await screen.findByTestId('sample-t2d_phase3_weak');
    expect(sample).toHaveTextContent('Deliberately weak');
    await userEvent.click(sample);
    await waitFor(() => expect(onProtocolChange).toHaveBeenCalledWith('p-1'));
  });

  it('shows why an upload was rejected', async () => {
    stubApi({
      '/api/samples': { body: samples },
      '/api/protocols': {
        status: 422,
        body: { detail: { message: 'No design found', warnings: ['Could not extract indication.'] } },
      },
    });
    render(<AdvisorApp />);
    await userEvent.upload(screen.getByTestId('protocol-file'), new File(['x'], 'notes.txt'));

    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent('No design found');
    expect(alert).toHaveTextContent('Could not extract indication.');
  });

  it('reports a failed sample list and a failed sample download', async () => {
    stubApi({ '/api/samples': { status: 500, body: {} } });
    render(<AdvisorApp />);
    expect(await screen.findByRole('alert')).toHaveTextContent('Request failed (500)');
  });

  it('reports a sample that cannot be downloaded', async () => {
    stubApi({ '/api/samples': { body: samples } });
    render(<AdvisorApp />);
    await userEvent.click(await screen.findByTestId('sample-asthma_phase3'));
    expect(await screen.findByRole('alert')).toHaveTextContent('Could not load the sample protocol.');
  });

  it('reports an unknown protocol and lets the author start over', async () => {
    const onProtocolChange = vi.fn();
    stubApi({});
    render(<AdvisorApp protocolId="missing" onProtocolChange={onProtocolChange} />);

    expect(await screen.findByRole('alert')).toHaveTextContent('Not found');
    await userEvent.click(screen.getByTestId('start-over'));
    expect(onProtocolChange).toHaveBeenCalledWith(undefined);
  });

  it('shows extraction warnings with the design', async () => {
    stubApi({
      ...reviewRoutes,
      '/api/protocols/p-1': {
        body: { ...protocol, design: { ...protocol.design, warnings: ['Could not extract site count.'] } },
      },
    });
    render(<AdvisorApp protocolId="p-1" onProtocolChange={() => {}} />);
    expect(await screen.findByTestId('design-warnings')).toHaveTextContent('Could not extract site count.');
  });
});
