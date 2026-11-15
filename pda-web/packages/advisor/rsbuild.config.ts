import { pluginModuleFederation } from '@module-federation/rsbuild-plugin';
import { defineConfig } from '@rsbuild/core';
import { pluginReact } from '@rsbuild/plugin-react';
import { apiProxy, ports, shared } from '../../federation.shared';

export default defineConfig({
  plugins: [
    pluginReact(),
    pluginModuleFederation({
      name: 'advisor',
      filename: 'remoteEntry.js',
      exposes: { './AdvisorApp': './src/AdvisorApp.tsx' },
      shared,
      dts: false,
    }),
  ],
  html: { title: 'Advisor remote (standalone)' },
  server: {
    port: ports.advisor,
    strictPort: true,
    proxy: apiProxy,
    headers: { 'Access-Control-Allow-Origin': '*' },
  },
  dev: { assetPrefix: 'auto' },
  output: { assetPrefix: 'auto' },
});
