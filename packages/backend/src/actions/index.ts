/**
 * Backend module registering the orchestration-api Custom Scaffolder
 * Actions (mlopsActions.ts) used by Golden Path #1 (Train->Track->Register),
 * #2 (Register->Deploy), #3 (Recommend->Track->Register), "Register
 * External Run", "Setup Model Monitoring", "Serving LLM", and the LLMOps
 * Lifecycle (RAG ingest/evaluate/activate, prompt draft/evaluate/activate)
 * — see examples/templates/.
 */

import { coreServices, createBackendModule } from '@backstage/backend-plugin-api';
import { scaffolderActionsExtensionPoint } from '@backstage/plugin-scaffolder-node';
import {
  createActivatePromptAction,
  createDraftPromptAction,
  createEnrichDatasetFeaturesAction,
  createEvaluatePromptAction,
  createModelSummaryAction,
  createPolicyCheckAction,
  createPrepareDeployManifestAction,
  createPrepareLlmDeployManifestAction,
  createRagActivateAction,
  createRagEvaluateAction,
  createRagIngestAction,
  createRecordDeployAction,
  createRegisterModelAction,
  createSetupMonitoringAction,
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
          createEnrichDatasetFeaturesAction({ config }),
          createTriggerTrainingAction({ config }),
          createRegisterModelAction({ config }),
          createModelSummaryAction({ config }),
          createPolicyCheckAction({ config }),
          createPrepareDeployManifestAction({ config }),
          createPrepareLlmDeployManifestAction({ config }),
          createRecordDeployAction({ config }),
          createValidateRecDatasetAction({ config }),
          createTriggerRecTrainingAction({ config }),
          createSetupMonitoringAction({ config }),
          createRagIngestAction({ config }),
          createRagEvaluateAction({ config }),
          createRagActivateAction({ config }),
          createDraftPromptAction({ config }),
          createEvaluatePromptAction({ config }),
          createActivatePromptAction({ config }),
        );
      },
    });
  },
});
