import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import AdvisorApp from './AdvisorApp';
import { assessment, competing, forecast, protocol, samples, stubApi, suggestions, whatIf } from './test-data';

const reviewRoutes = {
  '/api/protocols/p-1': { body: protocol },
  '/api/protocols/p-1/assessment': { body: assessment },
  '/api/protocols/p-1/competing-trials': { body: competing },
  '/api/protocols/p-1/forecast': { body: forecast },
  '/api/protocols/p-1/suggestions': { body: suggestions },
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

  it('shows P50, P90 and the termination risk with the trials behind it', async () => {
    stubApi(reviewRoutes);
    render(<AdvisorApp protocolId="p-1" onProtocolChange={() => {}} />);

    expect(await screen.findByTestId('forecast-p50')).toHaveTextContent('186.0');
    expect(screen.getByTestId('forecast-p90')).toHaveTextContent('1,372.4');
    expect(screen.getByTestId('termination-risk-value')).toHaveTextContent('1.4%');
    expect(screen.getByTestId('termination-risk')).toHaveAttribute('data-level', 'high');
    expect(within(screen.getByTestId('termination-trials')).getAllByRole('link')).toHaveLength(2);
  });

  it('lists suggestions with their citations', async () => {
    stubApi(reviewRoutes);
    render(<AdvisorApp protocolId="p-1" onProtocolChange={() => {}} />);

    const items = await screen.findAllByTestId('suggestion');
    expect(items).toHaveLength(2);
    expect(within(items[0]!).getByTestId('suggestion-title')).toHaveTextContent('Add 5 sites in China');
    expect(within(items[0]!).getByTestId('suggestion-saving')).toHaveTextContent('saves 70.3 months');
    expect(within(items[0]!).getAllByTestId('citation')).toHaveLength(6);
    expect(within(items[1]!).getByTestId('citation-count')).toHaveTextContent('5');
    expect(within(items[0]!).getAllByTestId('citation')[0]).toHaveAttribute(
      'href',
      'https://clinicaltrials.gov/study/NCT00000100',
    );
    expect(screen.getByTestId('what-if-run')).toBeDisabled();
  });

  it('applies the ticked changes in the what-if panel and shows the new forecast', async () => {
    const calls = stubApi({ ...reviewRoutes, '/api/protocols/p-1/what-if': { body: whatIf } });
    render(<AdvisorApp protocolId="p-1" onProtocolChange={() => {}} />);

    const picks = await screen.findAllByTestId('suggestion-pick');
    await userEvent.click(picks[0]!);
    await userEvent.click(picks[1]!);
    expect(within(screen.getByTestId('what-if-selected')).getAllByRole('listitem')).toHaveLength(2);
    await userEvent.click(screen.getByTestId('what-if-run'));

    expect(await screen.findByTestId('what-if-p50')).toHaveTextContent('105.9');
    expect(screen.getByTestId('what-if-baseline-p50')).toHaveTextContent('186.0');
    expect(screen.getByTestId('what-if-p50-saved')).toHaveTextContent('-80.1');
    expect(screen.getByTestId('what-if-risk')).toHaveTextContent('1.2%');
    const request = calls.find((call) => call.path === '/api/protocols/p-1/what-if');
    expect(JSON.parse(String(request?.init?.body))).toEqual({
      changes: suggestions.suggestions.map((suggestion) => suggestion.change),
    });

    // Changing the selection clears the stale result.
    await userEvent.click(picks[1]!);
    expect(screen.queryByTestId('what-if-result')).not.toBeInTheDocument();
  });

  it('reports a failed what-if and an empty suggestion list', async () => {
    stubApi({
      ...reviewRoutes,
      '/api/protocols/p-1/what-if': { status: 422, body: { detail: 'Unknown criterion: I99' } },
    });
    const view = render(<AdvisorApp protocolId="p-1" onProtocolChange={() => {}} />);
    await userEvent.click((await screen.findAllByTestId('suggestion-pick'))[0]!);
    await userEvent.click(screen.getByTestId('what-if-run'));
    expect(await screen.findByText('Unknown criterion: I99')).toBeInTheDocument();
    view.unmount();

    stubApi({
      ...reviewRoutes,
      '/api/protocols/p-1/suggestions': { body: { ...suggestions, suggestions: [] } },
      '/api/protocols/p-1/forecast': { body: { ...forecast, rate_source: 'indication_phase_benchmark' } },
    });
    render(<AdvisorApp protocolId="p-1" onProtocolChange={() => {}} />);
    expect(await screen.findByText('No change was found that shortens the forecast.')).toBeInTheDocument();
    expect(await screen.findByTestId('forecast')).toHaveTextContent('the indication and phase benchmark');
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
