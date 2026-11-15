# pda-web

Web app for the **Protocol Design Advisor** demo. React 19, TypeScript and Rsbuild with Module
Federation, as two packages in one npm workspace:

| Package            | Port | Role                                                                               |
| ------------------ | ---- | ---------------------------------------------------------------------------------- |
| `packages/host`    | 3000 | Shell: header, navigation, TanStack Router routes. Loads the Advisor at runtime    |
| `packages/advisor` | 3001 | Advisor remote, exposed as `advisor/AdvisorApp`. TanStack Query talks to `pda-api` |

If the Advisor remote cannot be loaded, the shell stays up and shows a fallback message.

## Run it

Needs Node 20 or newer and the API from `../pda-api` (see its README).

```bash
# terminal 1: API on http://localhost:8000
cd ../pda-api && make install && make run

# terminal 2: host on http://localhost:3000, Advisor remote on http://localhost:3001
cd pda-web && npm ci && npm run dev
```

Or start everything with Docker:

```bash
cd pda-web && docker compose up --build     # http://localhost:3000
```

Both servers forward `/api` to the API (`PDA_API_URL`, default `http://localhost:8000`). The host
finds the remote at `PDA_ADVISOR_URL` (default `http://localhost:3001`), fixed at build time.

## Scripts

| Command                            | What it does                                                       |
| ---------------------------------- | ------------------------------------------------------------------ |
| `npm run dev`                      | Both packages with hot reload                                      |
| `npm run build`, `npm run preview` | Production builds, then serve them                                 |
| `npm run lint`                     | ESLint and Prettier check                                          |
| `npm run typecheck`                | `tsc` for both packages and the e2e folder                         |
| `npm test`                         | Vitest unit tests with coverage (thresholds in `vitest.config.ts`) |
| `npm run e2e`                      | Playwright end-to-end suite                                        |
| `npm run sbom`                     | CycloneDX SBOM to `sbom.json`                                      |

## End-to-end tests

```bash
npx playwright install --with-deps
npm run e2e                       # all four projects
npm run e2e -- --project=webkit   # one engine
npx playwright show-report
```

- The suite starts the **real API** and the production builds of both packages itself
  (`webServer` in `playwright.config.ts`). The API runs from `../pda-api/.venv`, or from the
  interpreter named in `PDA_API_PYTHON`.
- Four projects: `chromium`, `firefox`, `webkit` (Safari's engine) and `iphone-14` (WebKit with the
  iPhone 14 device profile, for the mobile layout).
- Video, trace and a screenshot are recorded for every test. Results land in `test-results/` and
  the HTML report in `playwright-report/`.
- `e2e/author-journey.spec.ts` walks the weak sample protocol; `e2e/resilience.spec.ts` blocks the
  remote's `remoteEntry.js` and checks that the shell still renders.

## Layout

```
federation.shared.ts        shared singletons, ports and the /api proxy for both packages
packages/host/src           router.tsx, Shell.tsx, RemoteBoundary.tsx (fallback), AdvisorRoute.tsx
packages/advisor/src        AdvisorApp.tsx (exposed), api.ts, components/, advisor.css
e2e/                        Playwright specs
```

CI lives in `.github/workflows/pda-web.yml` and only runs for changes under `pda-web/`.
