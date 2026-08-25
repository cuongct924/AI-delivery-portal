/**
 * Backend module registering the orchestration-api Custom Scaffolder
 * Actions (mlopsActions.ts) used by Golden Path #1 (Train->Track->Register)
 * and #2 (Register->Deploy) — see examples/templates/.
 */

import { coreServices, createBackendModule } from '@backstage/backend-plugin-api';
import { scaffolderActionsExtensionPoint } from '@backstage/plugin-scaffolder-node';
import {
  createPolicyCheckAction,
  createPrepareDeployManifestAction,
  createRecordDeployAction,
  createTriggerTrainingAction,
} from './mlopsActions';

export default createBackendModule({
  pluginId: 'scaffolder',
  moduleId: 'mlops-actions',
  register(reg) {
    reg.registerInit({
      deps: {
        scaffolder: scaffolderActionsExtensionPoint,
        config: coreServices.rootConfig,
      },
      async init({ scaffolder, config }) {
        scaffolder.addActions(
          createTriggerTrainingAction({ config }),
          createPolicyCheckAction({ config }),
          createPrepareDeployManifestAction({ config }),
          createRecordDeployAction({ config }),
        );
      },
    });
  },
});
