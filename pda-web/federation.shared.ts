/** Libraries the host shell and the Advisor remote must load exactly once. */
export const shared = {
  react: { singleton: true, requiredVersion: '^19.0.0' },
  'react-dom': { singleton: true, requiredVersion: '^19.0.0' },
};

export const ports = { host: 3000, advisor: 3001 };

/** Both dev and preview servers forward /api to the FastAPI service. */
export const apiProxy = {
  '/api': { target: process.env.PDA_API_URL ?? 'http://localhost:8000', changeOrigin: true },
};
