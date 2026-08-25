import { PageBlueprint, createFrontendPlugin } from '@backstage/frontend-plugin-api';
import TimelineIcon from '@material-ui/icons/Timeline';
import { rootRouteRef } from './routes';

const mlopsDashboardPage = PageBlueprint.make({
  params: {
    path: '/mlops-dashboard',
    routeRef: rootRouteRef,
    title: 'MLOps Dashboard',
    icon: <TimelineIcon fontSize="inherit" />,
    loader: () =>
      import('./components/MlopsDashboardPage').then(m => (
        <m.MlopsDashboardPage />
      )),
  },
});

export default createFrontendPlugin({
  pluginId: 'mlops-dashboard',
  extensions: [mlopsDashboardPage],
  routes: { root: rootRouteRef },
});
