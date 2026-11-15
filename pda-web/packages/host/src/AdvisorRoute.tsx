import { lazy, Suspense } from 'react';
import { RemoteBoundary } from './RemoteBoundary';

const AdvisorApp = lazy(() => import('advisor/AdvisorApp'));

interface Props {
  protocolId?: string;
  onProtocolChange: (protocolId: string | undefined) => void;
}

export function AdvisorRoute(props: Props) {
  return (
    <RemoteBoundary name="Advisor">
      <Suspense fallback={<p className="shell-loading">Loading the Advisor…</p>}>
        <AdvisorApp {...props} />
      </Suspense>
    </RemoteBoundary>
  );
}
