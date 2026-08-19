import { createApp } from '@backstage/frontend-defaults';
import catalogPlugin from '@backstage/plugin-catalog/alpha';
import promptRegistryPlugin from '@internal/plugin-prompt-registry/alpha';
import { navModule } from './modules/nav';
import { homeModule } from './modules/home';

export default createApp({
  features: [catalogPlugin, promptRegistryPlugin, navModule, homeModule],
});
