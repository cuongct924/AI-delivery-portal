import { PageBlueprint, createFrontendPlugin } from '@backstage/frontend-plugin-api';
import DescriptionIcon from '@material-ui/icons/Description';
import { rootRouteRef } from './routes';

const promptRegistryPage = PageBlueprint.make({
  params: {
    path: '/prompt-registry',
    routeRef: rootRouteRef,
    title: 'Prompt Registry',
    icon: <DescriptionIcon fontSize="inherit" />,
    loader: () =>
      import('./components/PromptRegistryPage').then(m => (
        <m.PromptRegistryPage />
      )),
  },
});

export default createFrontendPlugin({
  pluginId: 'prompt-registry',
  extensions: [promptRegistryPage],
  routes: { root: rootRouteRef },
});
