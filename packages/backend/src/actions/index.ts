/**
 * Backend module registering the orchestration-api Custom Scaffolder
 * Actions (mlopsActions.ts) used by Golden Path #1 (Train->Track->Register),
 * #2 (Register->Deploy), and #3 (Recommend->Track->Register, mục 6e) — see
 * examples/templates/.
 */

import { coreServices, createBackendModule } from '@backstage/backend-plugin-api';
import { scaffolderActionsExtensionPoint } from '@backstage/plugin-scaffolder-node';
import {
  createModelSummaryAction,
  createPolicyCheckAction,
  createPrepareDeployManifestAction,
  createRecordDeployAction,
  createTriggerRecTrainingAction,
  createTriggerTrainingAction,
  createValidateDatasetAction,
  createValidateRecDatasetAction,
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
          createValidateDatasetAction({ config }),
          createTriggerTrainingAction({ config }),
          createModelSummaryAction({ config }),
          createPolicyCheckAction({ config }),
          createPrepareDeployManifestAction({ config }),
          createRecordDeployAction({ config }),
          createValidateRecDatasetAction({ config }),
          createTriggerRecTrainingAction({ config }),
        );
      },
    });
  },
});
