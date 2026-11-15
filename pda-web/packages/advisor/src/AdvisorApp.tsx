import { QueryClient, QueryClientProvider, useMutation, useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { api, type ApiError } from './api';
import { CompetingTrials } from './components/CompetingTrials';
import { DesignSummary } from './components/DesignSummary';
import { Restrictiveness } from './components/Restrictiveness';
import { SimilarTrials } from './components/SimilarTrials';
import { Upload } from './components/Upload';
import './advisor.css';

export interface AdvisorAppProps {
  /** Protocol to show. Without it the upload step is shown. */
  protocolId?: string;
  /** Called after a successful upload, and with `undefined` to start over. */
  onProtocolChange?: (protocolId: string | undefined) => void;
}

function createClient() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false, staleTime: 60_000, refetchOnWindowFocus: false } },
  });
}

export default function AdvisorApp(props: AdvisorAppProps) {
  const [client] = useState(createClient);
  return (
    <QueryClientProvider client={client}>
      <Advisor {...props} />
    </QueryClientProvider>
  );
}

function Advisor({ protocolId, onProtocolChange }: AdvisorAppProps) {
  const [localId, setLocalId] = useState<string>();
  const controlled = onProtocolChange !== undefined;
  const id = controlled ? protocolId : localId;
  const setId = controlled ? onProtocolChange : setLocalId;

  const upload = useMutation({ mutationFn: api.upload, onSuccess: (protocol) => setId(protocol.id) });

  return (
    <div className="pda-advisor" data-testid="advisor">
      {id ? (
        <Review protocolId={id} onReset={() => setId(undefined)} />
      ) : (
        <Upload busy={upload.isPending} error={upload.error as ApiError | null} onFile={upload.mutate} />
      )}
    </div>
  );
}

function Review({ protocolId, onReset }: { protocolId: string; onReset: () => void }) {
  const protocol = useQuery({ queryKey: ['protocol', protocolId], queryFn: () => api.protocol(protocolId) });
  const assessment = useQuery({ queryKey: ['assessment', protocolId], queryFn: () => api.assessment(protocolId) });
  const competing = useQuery({ queryKey: ['competing', protocolId], queryFn: () => api.competing(protocolId) });
  const failure = protocol.error ?? assessment.error ?? competing.error;

  return (
    <>
      <div className="pda-toolbar">
        <button type="button" className="pda-button" data-testid="start-over" onClick={onReset}>
          Upload another protocol
        </button>
      </div>
      {failure && (
        <p role="alert" className="pda-alert">
          {failure.message}
        </p>
      )}
      {protocol.isPending && <p className="pda-muted">Loading the design…</p>}
      {protocol.data && <DesignSummary protocol={protocol.data} />}
      {assessment.isPending && !failure && <p className="pda-muted">Scoring against benchmark trials…</p>}
      {assessment.data && <Restrictiveness assessment={assessment.data} />}
      {competing.data && <CompetingTrials data={competing.data} />}
      {assessment.data && <SimilarTrials trials={assessment.data.similar_trials} />}
    </>
  );
}
