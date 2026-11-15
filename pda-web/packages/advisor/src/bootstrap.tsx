import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import AdvisorApp from './AdvisorApp';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <AdvisorApp />
  </StrictMode>,
);
