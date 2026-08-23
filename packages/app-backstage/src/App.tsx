import { createApp } from '@backstage/frontend-defaults';
import catalogPlugin from '@backstage/plugin-catalog/alpha';
import promptRegistryPlugin from '@internal/plugin-prompt-registry/alpha';
import { navModule } from './modules/nav';
import { homeModule } from './modules/home';
import argocdPlugin from '@roadiehq/backstage-plugin-argo-cd/alpha';
import grafanaPlugin from '@backstage-community/plugin-grafana/alpha';
import mcpChatPlugin from '@backstage-community/plugin-mcp-chat/alpha';
import {
  convertLegacyPlugin,
  convertLegacyPageExtension,
} from '@backstage/core-compat-api';
import { convertLegacyEntityContentExtension } from '@backstage/plugin-catalog-react/alpha';
import {
  backstagePluginPrometheusPlugin,
  EntityPrometheusContent,
  isPrometheusAvailable,
} from '@roadiehq/backstage-plugin-prometheus';
import { litellmPlugin, LitellmPage } from '@cakecrusher/plugin-litellm';

// Legacy plugins (no /alpha export) converted for the new frontend system.
const convertedPrometheusPlugin = convertLegacyPlugin(
  backstagePluginPrometheusPlugin,
  {
    extensions: [
      convertLegacyEntityContentExtension(EntityPrometheusContent, {
        name: 'prometheus',
        path: '/prometheus',
        title: 'Prometheus',
        filter: isPrometheusAvailable,
      }),
    ],
  },
);

const convertedLitellmPlugin = convertLegacyPlugin(litellmPlugin, {
  extensions: [
    convertLegacyPageExtension(LitellmPage, {
      name: 'litellm',
      path: '/litellm',
    }),
  ],
});

export default createApp({
  features: [
    catalogPlugin,
    promptRegistryPlugin,
    navModule,
    homeModule,
    argocdPlugin,
    grafanaPlugin,
    mcpChatPlugin,
    convertedPrometheusPlugin,
    convertedLitellmPlugin,
  ],
});
