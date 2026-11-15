declare module 'advisor/AdvisorApp' {
  import type { ComponentType } from 'react';

  const AdvisorApp: ComponentType<{
    protocolId?: string;
    onProtocolChange?: (protocolId: string | undefined) => void;
  }>;
  export default AdvisorApp;
}
