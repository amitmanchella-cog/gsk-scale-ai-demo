import { createRootRoute, createRoute, createRouter, useNavigate, type RouterHistory } from '@tanstack/react-router';
import { AdvisorRoute } from './AdvisorRoute';
import { About, Shell } from './Shell';

const rootRoute = createRootRoute({ component: Shell });

function useProtocolNavigation() {
  const navigate = useNavigate();
  return (protocolId: string | undefined) =>
    void (protocolId ? navigate({ to: '/protocols/$protocolId', params: { protocolId } }) : navigate({ to: '/' }));
}

const uploadRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/',
  component: function UploadPage() {
    return <AdvisorRoute onProtocolChange={useProtocolNavigation()} />;
  },
});

const protocolRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/protocols/$protocolId',
  component: function ProtocolPage() {
    const { protocolId } = protocolRoute.useParams();
    return <AdvisorRoute protocolId={protocolId} onProtocolChange={useProtocolNavigation()} />;
  },
});

const aboutRoute = createRoute({ getParentRoute: () => rootRoute, path: '/about', component: About });

const routeTree = rootRoute.addChildren([uploadRoute, protocolRoute, aboutRoute]);

export function createAppRouter(history?: RouterHistory) {
  return createRouter({ routeTree, history, defaultPreload: false });
}

export const router = createAppRouter();

declare module '@tanstack/react-router' {
  interface Register {
    router: typeof router;
  }
}
