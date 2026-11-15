import { pluginModuleFederation } from '@module-federation/rsbuild-plugin';
import { defineConfig } from '@rsbuild/core';
import { pluginReact } from '@rsbuild/plugin-react';
import { apiProxy, ports, shared } from '../../federation.shared';

const advisorUrl = process.env.PDA_ADVISOR_URL ?? `http://localhost:${ports.advisor}`;

export default defineConfig({
  plugins: [
    pluginReact(),
    pluginModuleFederation({
      name: 'host',
      remotes: { advisor: `advisor@${advisorUrl}/remoteEntry.js` },
      shared,
      dts: false,
    }),
  ],
  html: {
    title: 'Protocol Design Advisor',
    meta: { viewport: 'width=device-width, initial-scale=1' },
  },
  server: { port: ports.host, strictPort: true, proxy: apiProxy },
});
