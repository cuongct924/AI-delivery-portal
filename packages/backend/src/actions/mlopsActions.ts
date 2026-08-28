/**
 * Custom Scaffolder Actions that call `services/orchestration-api` — the
 * HTTP surface Golden Path #1 (Train->Track->Register), #2
 * (Register->Deploy), #3 (Recommend->Track->Register), and "Setup Model
 * Monitoring" drive. Business logic stays in orchestration-api (CLAUDE.md);
 * these actions only translate Scaffolder input/output and, for training,
 * poll the workflow status until it finishes.
 */

import fs from 'node:fs/promises';
import path from 'node:path';
import { setTimeout as sleep } from 'node:timers/promises';
import { Config } from '@backstage/config';
import { createTemplateAction } from '@backstage/plugin-scaffolder-node';

const DEFAULT_BASE_URL = 'http://localhost:8000';
const POLL_INTERVAL_MS = 3_000;
const POLL_TIMEOUT_MS = 5 * 60 * 1000;

/** Terminal phases reported by Argo Workflows (routers/models.py `WorkflowStatusResponse`). */
type TerminalPhase = 'Succeeded' | 'Failed' | 'Error';

const TERMINAL_PHASES: ReadonlySet<TerminalPhase> = new Set([
  'Succeeded',
  'Failed',
  'Error',
]);

/** Response body of `POST {baseUrl}/trigger-training`. */
interface TriggerTrainingResponse {
  readonly workflow_name: string;
}

/** Response body of `POST {baseUrl}/trigger-rec-training`. */
interface TriggerRecTrainingResponse {
  readonly workflow_name: string;
}

/** Response body of `POST {baseUrl}/setup-monitoring`. */
interface SetupMonitoringResponse {
  readonly cron_workflow_name: string;
}

/** Response body of `GET {baseUrl}/trigger-training/{workflowName}/status`. */
interface WorkflowStatusResponse {
  readonly name: string;
  readonly phase: string | null;
  readonly message: string | null;
}

/** Response body of `GET {baseUrl}/models/{name}/latest-version`. */
interface LatestVersionResponse {
  readonly name: string;
  readonly version: string;
}

/** Response body of `POST {baseUrl}/models/register`. */
interface RegisterModelResponse {
  readonly name: string;
  readonly version: string;
}

/** Response body of `POST {baseUrl}/datasets/enrich-features`. */
interface EnrichDatasetFeaturesResponse {
  readonly dataset_uri: string;
}

/** One entry of `POST {baseUrl}/datasets/validate`'s response array. */
interface CheckResultItem {
  readonly check_name: string;
  readonly severity: 'blocking' | 'warning' | 'info';
  readonly message: string;
  readonly details: Record<string, unknown>;
}

/** Response body of `GET {baseUrl}/models/{name}/{version}/summary`. */
interface ModelVersionSummaryResponse {
  readonly name: string;
  readonly version: string;
  readonly task_type: string | null;
  readonly metrics: Record<string, number>;
  readonly tags: Record<string, string>;
}

/** Response body of `POST {baseUrl}/policy-check`. */
interface PolicyCheckResponse {
  readonly passed: boolean;
  readonly metrics: Record<string, number>;
  readonly thresholds: Record<string, number>;
}

/** Response body of `POST {baseUrl}/deploy-model/prepare`. */
interface PrepareDeployResponse {
  readonly file_name: string;
  readonly content: string;
  readonly deployed: boolean;
}

/** Response body of `POST {baseUrl}/llm-deploy/prepare`. */
interface PrepareLlmDeployResponse {
  readonly file_name: string;
  readonly content: string;
  readonly deployed: boolean;
}

/** Response body of `POST {baseUrl}/deploy-model/record`. */
interface RecordDeployResponse {
  readonly model_name: string;
  readonly model_version: string;
  readonly pr_url: string;
}

interface ActionDeps {
  readonly config: Config;
}

interface TriggerTrainingActionDeps extends ActionDeps {
  /** Overridable for tests — production callers rely on the defaults below. */
  readonly pollIntervalMs?: number;
  readonly pollTimeoutMs?: number;
}

function getBaseUrl(config: Config): string {
  return (
    config.getOptionalString('orchestrationApi.baseUrl') ?? DEFAULT_BASE_URL
  );
}

async function postJson<T>(url: string, body: unknown): Promise<T> {
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    throw new Error(
      `POST ${url} failed with ${response.status}: ${await response.text()}`,
    );
  }
  return (await response.json()) as T;
}

/**
 * `orchestration:trigger-training` — starts the train/fine-tune Argo
 * Workflow and polls it until it reaches a terminal phase.
 */
export function createTriggerTrainingAction({
  config,
  pollIntervalMs = POLL_INTERVAL_MS,
  pollTimeoutMs = POLL_TIMEOUT_MS,
}: TriggerTrainingActionDeps) {
  return createTemplateAction({
    id: 'orchestration:trigger-training',
    description:
      'Triggers the train (or fine-tune) Argo Workflow and waits for it to finish.',
    schema: {
      input: {
        modelName: z => z.string({ description: 'Name to register the trained model under' }),
        datasetUri: z => z.string({ description: 'URI of the training dataset' }),
        taskType: z =>
          z.string({ description: 'classification, regression, or clustering' }),
        architecture: z =>
          z
            .string({ description: '"sklearn" (default), "mlp", or "lstm" — see dl_architecture_registry.py' })
            .optional(),
        algorithm: z =>
          z
            .string({ description: 'Registry key, e.g. "XGBClassifier" — required when architecture is "sklearn"' })
            .optional(),
        targetColumn: z =>
          z
            .string({ description: 'Label column — required unless taskType is clustering' })
            .optional(),
        idColumns: z =>
          z
            .array(z.string(), { description: 'Columns to exclude as identifiers, e.g. transaction_id' })
            .optional(),
        timeColumn: z =>
          z
            .string({
              description:
                'Date/time column — when set, training always uses TimeSeriesSplit to avoid future leakage',
            })
            .optional(),
        baseModelUri: z =>
          z
            .string({
              description:
                'Base model URI — when set, fine-tunes instead of training from scratch',
            })
            .optional(),
        hiddenLayers: z =>
          z
            .array(z.number(), { description: 'Hidden layer sizes, e.g. [64, 32] — architecture=mlp' })
            .optional(),
        dropout: z => z.number({ description: 'Dropout rate — architecture=mlp' }).optional(),
        sequenceLength: z =>
          z.number({ description: 'Sliding-window length — architecture=lstm' }).optional(),
        numLayers: z => z.number({ description: 'LSTM layer count — architecture=lstm' }).optional(),
        hiddenSize: z => z.number({ description: 'LSTM hidden size — architecture=lstm' }).optional(),
        learningRate: z =>
          z.number({ description: 'Optimizer learning rate — architecture=mlp/lstm' }).optional(),
        epochs: z => z.number({ description: 'Training epochs — architecture=mlp/lstm' }).optional(),
        batchSize: z => z.number({ description: 'Batch size — architecture=mlp/lstm' }).optional(),
        optimizer: z =>
          z
            .string({
              description: '"adam" (default) or "sgd" — architecture=mlp/lstm/nlp/cv',
            })
            .optional(),
        codeRepoUrl: z =>
          z
            .string({ description: 'Git repo URL to clone — algorithm="custom" (BYOC)' })
            .optional(),
        entrypointPath: z =>
          z
            .string({
              description: 'Path, relative to the repo root, to the file defining train() — algorithm="custom"',
            })
            .optional(),
        customConfig: z =>
          z
            .string({
              description: 'JSON object of hyperparameters passed to train()\'s config arg — algorithm="custom"',
            })
            .optional(),
        searchStrategy: z =>
          z
            .string({ description: '"fixed" (default), "grid", "random", or "bayesian"' })
            .optional(),
        numTrials: z =>
          z.number({ description: 'Trial budget — searchStrategy=random/bayesian' }).optional(),
        searchSpaceJson: z =>
          z
            .string({
              description: 'JSON object mapping hyperparameter name to {choices:[...]} or {low,high} — searchStrategy!=fixed',
            })
            .optional(),
        objectiveMetric: z =>
          z
            .string({ description: 'Metric name to optimize across trials — searchStrategy!=fixed' })
            .optional(),
        objectiveDirection: z =>
          z
            .string({ description: '"maximize" (default) or "minimize" — searchStrategy!=fixed' })
            .optional(),
        textColumn: z =>
          z.string({ description: 'Column containing the text to classify — architecture="nlp"' }).optional(),
        baseModelName: z =>
          z
            .string({ description: 'HuggingFace Hub model id to fine-tune — architecture="nlp"' })
            .optional(),
      },
      output: {
        workflowName: z => z.string({ description: 'Name of the Argo Workflow that ran' }),
        phase: z => z.string({ description: 'Terminal phase the workflow finished in' }),
        modelVersion: z =>
          z.string({
            description:
              'MLflow model version the register-step registered — resolved after the workflow succeeds',
          }),
      },
    },
    async handler(ctx) {
      const baseUrl = getBaseUrl(config);
      const { workflow_name: workflowName } =
        await postJson<TriggerTrainingResponse>(`${baseUrl}/trigger-training`, {
          model_name: ctx.input.modelName,
          dataset_uri: ctx.input.datasetUri,
          task_type: ctx.input.taskType,
          architecture: ctx.input.architecture,
          algorithm: ctx.input.algorithm,
          target_column: ctx.input.targetColumn,
          id_columns: ctx.input.idColumns,
          time_column: ctx.input.timeColumn,
          base_model_uri: ctx.input.baseModelUri,
          hidden_layers: ctx.input.hiddenLayers,
          dropout: ctx.input.dropout,
          sequence_length: ctx.input.sequenceLength,
          num_layers: ctx.input.numLayers,
          hidden_size: ctx.input.hiddenSize,
          learning_rate: ctx.input.learningRate,
          epochs: ctx.input.epochs,
          batch_size: ctx.input.batchSize,
          optimizer: ctx.input.optimizer,
          code_repo_url: ctx.input.codeRepoUrl,
          entrypoint_path: ctx.input.entrypointPath,
          custom_config: ctx.input.customConfig,
          search_strategy: ctx.input.searchStrategy,
          num_trials: ctx.input.numTrials,
          search_space_json: ctx.input.searchSpaceJson,
          objective_metric: ctx.input.objectiveMetric,
          objective_direction: ctx.input.objectiveDirection,
          text_column: ctx.input.textColumn,
          base_model_name: ctx.input.baseModelName,
        });
      ctx.logger.info(`Triggered training workflow "${workflowName}"`);

      const deadline = Date.now() + pollTimeoutMs;
      let status: WorkflowStatusResponse;
      for (;;) {
        const response = await fetch(
          `${baseUrl}/trigger-training/${workflowName}/status`,
        );
        if (!response.ok) {
          throw new Error(
            `GET workflow status failed with ${response.status}: ${await response.text()}`,
          );
        }
        status = (await response.json()) as WorkflowStatusResponse;
        ctx.logger.info(
          `Workflow "${workflowName}" phase: ${status.phase ?? 'unknown'}`,
        );
        if (status.phase !== null && TERMINAL_PHASES.has(status.phase as TerminalPhase)) {
          break;
        }
        if (Date.now() >= deadline) {
          throw new Error(
            `Timed out after ${pollTimeoutMs / 1000}s waiting for workflow "${workflowName}" to finish`,
          );
        }
        await sleep(pollIntervalMs);
      }

      const finalPhase = status.phase;
      if (finalPhase !== 'Succeeded') {
        throw new Error(
          `Workflow "${workflowName}" ended in phase "${finalPhase}": ${status.message ?? 'no message'}`,
        );
      }

      // register-step registers async — fetch the resulting version now.
      const latestVersionResponse = await fetch(
        `${baseUrl}/models/${encodeURIComponent(ctx.input.modelName)}/latest-version`,
      );
      if (!latestVersionResponse.ok) {
        throw new Error(
          `GET latest model version failed with ${latestVersionResponse.status}: ${await latestVersionResponse.text()}`,
        );
      }
      const { version: modelVersion } =
        (await latestVersionResponse.json()) as LatestVersionResponse;

      ctx.output('workflowName', workflowName);
      ctx.output('phase', finalPhase);
      ctx.output('modelVersion', modelVersion);
    },
  });
}

/**
 * `orchestration:validate-dataset` — runs the Data Quality checks
 * (services/orchestration-api/data_quality/) before training starts, and
 * fails fast (no Argo compute spent) if any check comes back blocking.
 */
export function createValidateDatasetAction({ config }: ActionDeps) {
  return createTemplateAction({
    id: 'orchestration:validate-dataset',
    description:
      'Runs data quality checks against the dataset and fails the step on any blocking result.',
    schema: {
      input: {
        datasetUri: z => z.string({ description: 'URI of the dataset to validate' }),
        taskType: z =>
          z.string({ description: 'classification, regression, or clustering' }),
        targetColumn: z =>
          z
            .string({ description: 'Label column — required unless taskType is clustering' })
            .optional(),
        timeColumn: z => z.string({ description: 'Date/time column, if the data is ordered' }).optional(),
      },
      output: {
        results: z =>
          z
            .array(
              z.object({
                checkName: z.string(),
                severity: z.enum(['blocking', 'warning', 'info']),
                message: z.string(),
              }),
              { description: 'One entry per check that ran, grouped by severity in the log' },
            ),
      },
    },
    async handler(ctx) {
      const baseUrl = getBaseUrl(config);
      const results = await postJson<CheckResultItem[]>(`${baseUrl}/datasets/validate`, {
        dataset_uri: ctx.input.datasetUri,
        task_type: ctx.input.taskType,
        target_column: ctx.input.targetColumn,
        time_column: ctx.input.timeColumn,
      });

      for (const result of results) {
        ctx.logger.info(`[${result.severity}] ${result.check_name}: ${result.message}`);
      }

      const blocking = results.filter(r => r.severity === 'blocking');
      if (blocking.length > 0) {
        const summary = blocking.map(r => `${r.check_name}: ${r.message}`).join('; ');
        throw new Error(`Dataset validation failed (blocking): ${summary}`);
      }

      ctx.output(
        'results',
        results.map(r => ({
          checkName: r.check_name,
          severity: r.severity,
          message: r.message,
        })),
      );
    },
  });
}

/**
 * `orchestration:enrich-dataset-features` — merges precomputed Feast
 * features into a training dataset before it's handed to
 * `orchestration:trigger-training`. Opt-in — most Golden Path #1 runs skip
 * this step entirely.
 */
export function createEnrichDatasetFeaturesAction({ config }: ActionDeps) {
  return createTemplateAction({
    id: 'orchestration:enrich-dataset-features',
    description: "Merges precomputed Feast features into a dataset's rows.",
    schema: {
      input: {
        datasetUri: z => z.string({ description: 'URI of the dataset to enrich' }),
        entityIdColumn: z =>
          z.string({ description: 'Column identifying each row for the Feast lookup, e.g. "transaction_id"' }),
        featureNames: z =>
          z.array(z.string(), {
            description: 'Feast "<feature_view>:<feature>" references, e.g. "transaction_features:amount"',
          }),
      },
      output: {
        datasetUri: z => z.string({ description: 'URI of the enriched dataset, with feature columns merged in' }),
      },
    },
    async handler(ctx) {
      const baseUrl = getBaseUrl(config);
      const result = await postJson<EnrichDatasetFeaturesResponse>(
        `${baseUrl}/datasets/enrich-features`,
        {
          dataset_uri: ctx.input.datasetUri,
          entity_id_column: ctx.input.entityIdColumn,
          feature_names: ctx.input.featureNames,
        },
      );
      ctx.output('datasetUri', result.dataset_uri);
    },
  });
}

/**
 * `orchestration:register-model` — registers an existing MLflow run's
 * logged model into the Model Registry. Reuses `POST /models/register`
 * unchanged, the same endpoint the Golden Path #1/#3 Argo Workflow's
 * register-step calls — this is the entry point for a model trained
 * outside any Golden Path (e.g. interactively in AI Notebook).
 */
export function createRegisterModelAction({ config }: ActionDeps) {
  return createTemplateAction({
    id: 'orchestration:register-model',
    description: "Registers an existing MLflow run's logged model into the Model Registry.",
    schema: {
      input: {
        modelName: z => z.string({ description: 'Name to register the model under' }),
        artifactUri: z =>
          z.string({
            description:
              'Logged model URI, e.g. "runs:/<run_id>/<artifact_path>" — printed as model_info.model_uri by mlflow.<flavor>.log_model()',
          }),
        taskType: z =>
          z.string({ description: 'classification, regression, or clustering' }),
        datasetVersion: z =>
          z
            .string({
              description: 'Dataset version — a DVC digest if available, otherwise any free-text identifier',
            })
            .optional(),
      },
      output: {
        modelName: z => z.string({ description: 'Registered model name' }),
        modelVersion: z =>
          z.string({ description: 'MLflow version number assigned to the new registration' }),
      },
    },
    async handler(ctx) {
      const baseUrl = getBaseUrl(config);
      const result = await postJson<RegisterModelResponse>(`${baseUrl}/models/register`, {
        name: ctx.input.modelName,
        artifact_uri: ctx.input.artifactUri,
        task_type: ctx.input.taskType,
        dataset_version: ctx.input.datasetVersion,
      });
      ctx.logger.info(`Registered "${result.name}" as version ${result.version}`);
      ctx.output('modelName', result.name);
      ctx.output('modelVersion', result.version);
    },
  });
}

/**
 * `orchestration:model-summary` — fetches a registered model version's
 * task type, metrics, and tags for display mid-template.
 */
export function createModelSummaryAction({ config }: ActionDeps) {
  return createTemplateAction({
    id: 'orchestration:model-summary',
    description: 'Fetches a registered model version — task type, metrics, and tags.',
    schema: {
      input: {
        modelName: z => z.string({ description: 'Registered model name' }),
        modelVersion: z => z.string({ description: 'Registered model version' }),
      },
      output: {
        taskType: z => z.string({ description: 'Task type tag set at register time' }).nullable(),
        metrics: z => z.record(z.number(), { description: 'Logged training metrics' }),
      },
    },
    async handler(ctx) {
      const baseUrl = getBaseUrl(config);
      const response = await fetch(
        `${baseUrl}/models/${encodeURIComponent(ctx.input.modelName)}/${encodeURIComponent(ctx.input.modelVersion)}/summary`,
      );
      if (!response.ok) {
        throw new Error(
          `GET model version summary failed with ${response.status}: ${await response.text()}`,
        );
      }
      const summary = (await response.json()) as ModelVersionSummaryResponse;

      ctx.output('taskType', summary.task_type);
      ctx.output('metrics', summary.metrics);
    },
  });
}

/**
 * `orchestration:policy-check` — runs the Evaluate Gate (direct metric
 * thresholds, no LLM call) against a registered model version and fails
 * the step on rejection.
 */
export function createPolicyCheckAction({ config }: ActionDeps) {
  return createTemplateAction({
    id: 'orchestration:policy-check',
    description:
      'Runs the Evaluate Gate (metric thresholds) against a registered model version.',
    schema: {
      input: {
        modelName: z => z.string({ description: 'Registered model name' }),
        modelVersion: z => z.string({ description: 'Registered model version' }),
      },
      output: {
        passed: z => z.boolean({ description: 'Whether the model passed the Evaluate Gate' }),
        metrics: z =>
          z.record(z.number(), { description: 'Model metrics compared against thresholds' }),
      },
    },
    async handler(ctx) {
      const baseUrl = getBaseUrl(config);
      const result = await postJson<PolicyCheckResponse>(
        `${baseUrl}/policy-check`,
        {
          model_name: ctx.input.modelName,
          model_version: ctx.input.modelVersion,
        },
      );
      if (result.passed !== true) {
        const summary = Object.entries(result.metrics)
          .map(([key, value]) => `${key}=${value}`)
          .join(', ');
        throw new Error(
          `Evaluate Gate rejected ${ctx.input.modelName}:${ctx.input.modelVersion} — metrics below threshold (${summary})`,
        );
      }
      ctx.output('passed', result.passed);
      ctx.output('metrics', result.metrics);
    },
  });
}

/**
 * `orchestration:prepare-deploy-manifest` — fetches the rendered
 * InferenceService manifest and writes it into the Scaffolder workspace so
 * a later `publish:github:pull-request` step can commit it.
 */
export function createPrepareDeployManifestAction({ config }: ActionDeps) {
  return createTemplateAction({
    id: 'orchestration:prepare-deploy-manifest',
    description:
      'Renders the KServe InferenceService manifest for a model version and writes it into the workspace.',
    schema: {
      input: {
        modelName: z => z.string({ description: 'Registered model name' }),
        modelVersion: z => z.string({ description: 'Registered model version' }),
        trafficStrategy: z =>
          z
            .enum(['direct', 'canary', 'ab', 'blue-green'], {
              description: 'How traffic moves to the new version — canary/ab/blue-green require a prior deploy',
            })
            .optional(),
        trafficPercent: z =>
          z
            .number({ description: 'Required unless trafficStrategy is direct/unset' })
            .optional(),
        releaseStrategy: z =>
          z
            .enum(['pr-gated', 'instant'], {
              description: 'pr-gated (default) opens a PR; instant deploys directly, no PR',
            })
            .optional(),
      },
      output: {
        filePath: z => z.string({ description: 'Workspace-relative path the manifest was written to' }),
        deployed: z =>
          z.boolean({
            description: 'True when releaseStrategy=instant already deployed it — no PR to publish',
          }),
      },
    },
    async handler(ctx) {
      const baseUrl = getBaseUrl(config);
      const {
        file_name: fileName,
        content,
        deployed,
      } = await postJson<PrepareDeployResponse>(`${baseUrl}/deploy-model/prepare`, {
        model_name: ctx.input.modelName,
        model_version: ctx.input.modelVersion,
        traffic_strategy: ctx.input.trafficStrategy,
        traffic_percent: ctx.input.trafficPercent,
        release_strategy: ctx.input.releaseStrategy,
      });
      const absolutePath = path.join(ctx.workspacePath, fileName);
      await fs.mkdir(path.dirname(absolutePath), { recursive: true });
      await fs.writeFile(absolutePath, content, 'utf-8');
      ctx.logger.info(
        deployed
          ? `Deployed "${ctx.input.modelName}:${ctx.input.modelVersion}" directly (releaseStrategy=instant)`
          : `Wrote deploy manifest to "${fileName}"`,
      );
      ctx.output('filePath', fileName);
      ctx.output('deployed', deployed);
    },
  });
}

/**
 * `orchestration:prepare-llm-deploy-manifest` — renders the KServe
 * InferenceService manifest for a self-hosted LLM (vLLM, referenced by
 * HuggingFace Hub id — not an MLflow-registered artifact) and writes it
 * into the Scaffolder workspace, same shape as
 * `orchestration:prepare-deploy-manifest` but a separate endpoint since
 * that one hardcodes the MLflow Model Registry URI formula.
 */
export function createPrepareLlmDeployManifestAction({ config }: ActionDeps) {
  return createTemplateAction({
    id: 'orchestration:prepare-llm-deploy-manifest',
    description:
      'Renders the KServe InferenceService manifest for a self-hosted LLM and writes it into the workspace.',
    schema: {
      input: {
        modelName: z => z.string({ description: 'Name to deploy the LLM under' }),
        huggingFaceModelId: z =>
          z.string({ description: 'HuggingFace Hub model id, e.g. "meta-llama/Llama-3.1-8B-Instruct"' }),
        runtime: z =>
          z.string({ description: '"vllm" (default) — see llm_serving/registry.py' }).optional(),
        gpuType: z =>
          z.enum(['L4', 'L40S', 'A100', 'H100', 'H200', 'B200'], {
            description: 'GPU type to request',
          }),
        gpuCount: z =>
          z.enum(['1', '2', '4', '8'], { description: 'GPU count — also used as tensor-parallel-size' }).optional(),
        quantization: z =>
          z
            .enum(['none', 'fp8', 'int8', 'int4-awq'], {
              description: 'Not every gpuType supports every value — see llm_serving/registry.py',
            })
            .optional(),
        maxContextLength: z =>
          z.number({ description: 'Max context length in tokens' }).optional(),
        trafficStrategy: z =>
          z
            .enum(['direct', 'canary', 'ab', 'blue-green'], {
              description: 'How traffic moves to the new version — canary/ab/blue-green require a prior deploy',
            })
            .optional(),
        trafficPercent: z =>
          z
            .number({ description: 'Required unless trafficStrategy is direct/unset' })
            .optional(),
        releaseStrategy: z =>
          z
            .enum(['pr-gated', 'instant'], {
              description: 'pr-gated (default) opens a PR; instant deploys directly, no PR',
            })
            .optional(),
      },
      output: {
        filePath: z => z.string({ description: 'Workspace-relative path the manifest was written to' }),
        deployed: z =>
          z.boolean({
            description: 'True when releaseStrategy=instant already deployed it — no PR to publish',
          }),
      },
    },
    async handler(ctx) {
      const baseUrl = getBaseUrl(config);
      const {
        file_name: fileName,
        content,
        deployed,
      } = await postJson<PrepareLlmDeployResponse>(`${baseUrl}/llm-deploy/prepare`, {
        model_name: ctx.input.modelName,
        huggingface_model_id: ctx.input.huggingFaceModelId,
        runtime: ctx.input.runtime,
        gpu_type: ctx.input.gpuType,
        gpu_count: ctx.input.gpuCount ? Number(ctx.input.gpuCount) : undefined,
        quantization: ctx.input.quantization,
        max_context_length: ctx.input.maxContextLength,
        traffic_strategy: ctx.input.trafficStrategy,
        traffic_percent: ctx.input.trafficPercent,
        release_strategy: ctx.input.releaseStrategy,
      });
      const absolutePath = path.join(ctx.workspacePath, fileName);
      await fs.mkdir(path.dirname(absolutePath), { recursive: true });
      await fs.writeFile(absolutePath, content, 'utf-8');
      ctx.logger.info(
        deployed
          ? `Deployed LLM "${ctx.input.modelName}" directly (releaseStrategy=instant)`
          : `Wrote LLM deploy manifest to "${fileName}"`,
      );
      ctx.output('filePath', fileName);
      ctx.output('deployed', deployed);
    },
  });
}

/**
 * `orchestration:record-deploy` — records the deploy PR URL as an MLflow
 * model version tag so the Dashboard can read it back later.
 */
export function createRecordDeployAction({ config }: ActionDeps) {
  return createTemplateAction({
    id: 'orchestration:record-deploy',
    description: 'Records the deploy pull request URL against the model version.',
    schema: {
      input: {
        modelName: z => z.string({ description: 'Registered model name' }),
        modelVersion: z => z.string({ description: 'Registered model version' }),
        prUrl: z =>
          z
            .string({ description: 'URL of the deploy pull request — omitted for an instant release' })
            .optional(),
      },
      output: {
        recorded: z => z.boolean({ description: 'Always true on success — an HTTP error throws instead' }),
      },
    },
    async handler(ctx) {
      const baseUrl = getBaseUrl(config);
      await postJson<RecordDeployResponse>(`${baseUrl}/deploy-model/record`, {
        model_name: ctx.input.modelName,
        model_version: ctx.input.modelVersion,
        pr_url: ctx.input.prUrl,
      });
      ctx.output('recorded', true);
    },
  });
}

/**
 * `orchestration:validate-rec-dataset` — RecSys's own dataset checks, a
 * separate endpoint from `orchestration:validate-dataset` since the shape
 * (interactions, no target column) doesn't match.
 */
export function createValidateRecDatasetAction({ config }: ActionDeps) {
  return createTemplateAction({
    id: 'orchestration:validate-rec-dataset',
    description:
      'Runs RecSys data quality checks against the interactions dataset and fails the step on any blocking result.',
    schema: {
      input: {
        interactionsUri: z => z.string({ description: 'URI of the interactions dataset to validate' }),
        userIdColumn: z => z.string({ description: 'Column identifying the user in each interaction' }),
        itemIdColumn: z => z.string({ description: 'Column identifying the item in each interaction' }),
      },
      output: {
        results: z =>
          z.array(
            z.object({
              checkName: z.string(),
              severity: z.enum(['blocking', 'warning', 'info']),
              message: z.string(),
            }),
            { description: 'One entry per check that ran, grouped by severity in the log' },
          ),
      },
    },
    async handler(ctx) {
      const baseUrl = getBaseUrl(config);
      const results = await postJson<CheckResultItem[]>(`${baseUrl}/rec-datasets/validate`, {
        interactions_uri: ctx.input.interactionsUri,
        user_id_column: ctx.input.userIdColumn,
        item_id_column: ctx.input.itemIdColumn,
      });

      for (const result of results) {
        ctx.logger.info(`[${result.severity}] ${result.check_name}: ${result.message}`);
      }

      const blocking = results.filter(r => r.severity === 'blocking');
      if (blocking.length > 0) {
        const summary = blocking.map(r => `${r.check_name}: ${r.message}`).join('; ');
        throw new Error(`RecSys dataset validation failed (blocking): ${summary}`);
      }

      ctx.output(
        'results',
        results.map(r => ({
          checkName: r.check_name,
          severity: r.severity,
          message: r.message,
        })),
      );
    },
  });
}

/**
 * `orchestration:trigger-rec-training` — starts the RecSys Argo Workflow
 * (Golden Path #3) and polls it to completion. Reuses the same
 * `/trigger-training/{workflowName}/status` and `/models/{name}/latest-
 * version` endpoints `orchestration:trigger-training` uses — both are
 * keyed by workflow/model name, not by which WorkflowTemplate produced
 * them, so there's nothing RecSys-specific to add there.
 */
export function createTriggerRecTrainingAction({
  config,
  pollIntervalMs = POLL_INTERVAL_MS,
  pollTimeoutMs = POLL_TIMEOUT_MS,
}: TriggerTrainingActionDeps) {
  return createTemplateAction({
    id: 'orchestration:trigger-rec-training',
    description: 'Triggers the RecSys Argo Workflow and waits for it to finish.',
    schema: {
      input: {
        modelName: z => z.string({ description: 'Name to register the trained model under' }),
        interactionsUri: z => z.string({ description: 'URI of the interactions dataset' }),
        userIdColumn: z => z.string({ description: 'Column identifying the user in each interaction' }),
        itemIdColumn: z => z.string({ description: 'Column identifying the item in each interaction' }),
        timestampColumn: z => z.string({ description: 'Column with the interaction timestamp — used for the temporal train/test split' }),
        algorithm: z =>
          z.string({ description: 'als, bpr, svd, knn, tfidf_cosine, or popularity — see rec_algorithm_registry.py' }),
        k: z => z.number({ description: 'Recommendation list length used for recall@k/ndcg@k/map@k' }).optional(),
        hyperparametersJson: z =>
          z
            .string({ description: 'JSON object of the chosen algorithm\'s hyperparameters' })
            .optional(),
        ratingColumn: z =>
          z.string({ description: 'Rating column — required for algorithm=svd/knn' }).optional(),
        itemFeaturesUri: z =>
          z.string({ description: 'URI of item metadata — required for algorithm=tfidf_cosine' }).optional(),
        itemIdColumnFeatures: z =>
          z.string({ description: 'Item id column in itemFeaturesUri — required for algorithm=tfidf_cosine' }).optional(),
        itemTextColumn: z =>
          z.string({ description: 'Text column in itemFeaturesUri — required for algorithm=tfidf_cosine' }).optional(),
      },
      output: {
        workflowName: z => z.string({ description: 'Name of the Argo Workflow that ran' }),
        phase: z => z.string({ description: 'Terminal phase the workflow finished in' }),
        modelVersion: z =>
          z.string({
            description:
              'MLflow model version the register-step registered — resolved after the workflow succeeds',
          }),
      },
    },
    async handler(ctx) {
      const baseUrl = getBaseUrl(config);
      const { workflow_name: workflowName } =
        await postJson<TriggerRecTrainingResponse>(`${baseUrl}/trigger-rec-training`, {
          model_name: ctx.input.modelName,
          interactions_uri: ctx.input.interactionsUri,
          user_id_column: ctx.input.userIdColumn,
          item_id_column: ctx.input.itemIdColumn,
          timestamp_column: ctx.input.timestampColumn,
          algorithm: ctx.input.algorithm,
          k: ctx.input.k,
          hyperparameters_json: ctx.input.hyperparametersJson,
          rating_column: ctx.input.ratingColumn,
          item_features_uri: ctx.input.itemFeaturesUri,
          item_id_column_features: ctx.input.itemIdColumnFeatures,
          item_text_column: ctx.input.itemTextColumn,
        });
      ctx.logger.info(`Triggered RecSys training workflow "${workflowName}"`);

      const deadline = Date.now() + pollTimeoutMs;
      let status: WorkflowStatusResponse;
      for (;;) {
        const response = await fetch(
          `${baseUrl}/trigger-training/${workflowName}/status`,
        );
        if (!response.ok) {
          throw new Error(
            `GET workflow status failed with ${response.status}: ${await response.text()}`,
          );
        }
        status = (await response.json()) as WorkflowStatusResponse;
        ctx.logger.info(
          `Workflow "${workflowName}" phase: ${status.phase ?? 'unknown'}`,
        );
        if (status.phase !== null && TERMINAL_PHASES.has(status.phase as TerminalPhase)) {
          break;
        }
        if (Date.now() >= deadline) {
          throw new Error(
            `Timed out after ${pollTimeoutMs / 1000}s waiting for workflow "${workflowName}" to finish`,
          );
        }
        await sleep(pollIntervalMs);
      }

      const finalPhase = status.phase;
      if (finalPhase !== 'Succeeded') {
        throw new Error(
          `Workflow "${workflowName}" ended in phase "${finalPhase}": ${status.message ?? 'no message'}`,
        );
      }

      const latestVersionResponse = await fetch(
        `${baseUrl}/models/${encodeURIComponent(ctx.input.modelName)}/latest-version`,
      );
      if (!latestVersionResponse.ok) {
        throw new Error(
          `GET latest model version failed with ${latestVersionResponse.status}: ${await latestVersionResponse.text()}`,
        );
      }
      const { version: modelVersion } =
        (await latestVersionResponse.json()) as LatestVersionResponse;

      ctx.output('workflowName', workflowName);
      ctx.output('phase', finalPhase);
      ctx.output('modelVersion', modelVersion);
    },
  });
}

/**
 * `orchestration:setup-monitoring` — registers a periodic Argo CronWorkflow.
 * Unlike every other action here, this doesn't poll a workflow to
 * completion — Setup just registers the schedule and returns.
 */
export function createSetupMonitoringAction({ config }: ActionDeps) {
  return createTemplateAction({
    id: 'orchestration:setup-monitoring',
    description: 'Registers a periodic Argo CronWorkflow that checks the model for data drift.',
    schema: {
      input: {
        modelName: z => z.string({ description: 'Registered model name' }),
        modelVersion: z => z.string({ description: 'Registered model version' }),
        referenceDataUri: z =>
          z.string({
            description: 'file:// CSV path — normally the dataset the model was trained on',
          }),
        productionDataUri: z =>
          z.string({
            description: 'file:// CSV path with recent production input data to compare against it',
          }),
        schedule: z => z.string({ description: 'Cron expression, e.g. "0 0 * * *" for daily' }),
        driftThreshold: z =>
          z
            .number({
              description: 'Share of columns (0-1) Evidently must flag as drifted to count as drift',
            })
            .optional(),
        onDriftDetected: z =>
          z.string({ description: '"alert-only" (default) or "auto-retrain"' }).optional(),
        retrainRequestJson: z =>
          z
            .string({
              description:
                'JSON body to POST to /trigger-training — required when onDriftDetected="auto-retrain"',
            })
            .optional(),
      },
      output: {
        cronWorkflowName: z => z.string({ description: 'Name of the registered CronWorkflow' }),
      },
    },
    async handler(ctx) {
      const baseUrl = getBaseUrl(config);
      const { cron_workflow_name: cronWorkflowName } =
        await postJson<SetupMonitoringResponse>(`${baseUrl}/setup-monitoring`, {
          model_name: ctx.input.modelName,
          model_version: ctx.input.modelVersion,
          reference_data_uri: ctx.input.referenceDataUri,
          production_data_uri: ctx.input.productionDataUri,
          schedule: ctx.input.schedule,
          drift_threshold: ctx.input.driftThreshold,
          on_drift_detected: ctx.input.onDriftDetected,
          retrain_request_json: ctx.input.retrainRequestJson,
        });
      ctx.logger.info(`Registered monitoring CronWorkflow "${cronWorkflowName}"`);
      ctx.output('cronWorkflowName', cronWorkflowName);
    },
  });
}

/** Response body of `POST {baseUrl}/rag/ingest`. */
interface RagIngestResponse {
  readonly collection: string;
  readonly index_version: string;
  readonly chunks_ingested: number;
}

/** Response body of `POST {baseUrl}/rag/evaluate`. */
interface RagEvaluateResponse {
  readonly passed: boolean;
  readonly pass_rate: number;
  readonly results: Record<string, unknown>[];
}

/** Response body of `POST {baseUrl}/rag/activate`. */
interface RagActivateResponse {
  readonly collection: string;
  readonly active_version: string;
}

/** Response body of `POST {baseUrl}/prompts`. */
interface DraftPromptResponse {
  readonly id: string;
  readonly name: string;
  readonly version: string;
  readonly persona: string;
  readonly content: string;
}

/** Response body of `POST {baseUrl}/prompts/{name}/evaluate`. */
interface EvaluatePromptResponse {
  readonly passed: boolean;
  readonly pass_rate: number;
  readonly results: Record<string, unknown>[];
}

/** Response body of `POST {baseUrl}/prompts/{name}/activate`. */
interface ActivatePromptResponse {
  readonly name: string;
  readonly active_version: string;
}

function parseEvalCasesJson(evalCasesJson: string): unknown {
  try {
    return JSON.parse(evalCasesJson);
  } catch (err) {
    throw new Error(`evalCasesJson is not valid JSON: ${err}`);
  }
}

/**
 * `orchestration:rag-ingest` — chunks and embeds documents into a Qdrant
 * collection, registering a new (inactive) RAG index version.
 */
export function createRagIngestAction({ config }: ActionDeps) {
  return createTemplateAction({
    id: 'orchestration:rag-ingest',
    description:
      'Chunks and embeds documents into a Qdrant collection, registering a new (inactive) RAG index version.',
    schema: {
      input: {
        collection: z => z.string({ description: 'Qdrant collection name' }),
        sourcePaths: z =>
          z.array(z.string(), {
            description: 'Repo-relative paths to ingest, e.g. ["docs/playbook-ai-delivery-portal.md"]',
          }),
        chunkSize: z => z.number({ description: 'Characters per chunk' }).optional(),
        chunkOverlap: z =>
          z.number({ description: 'Character overlap between consecutive chunks' }).optional(),
      },
      output: {
        indexVersion: z =>
          z.string({ description: 'Newly registered RAG index version — not active yet' }),
        chunksIngested: z => z.number({ description: 'Number of chunks embedded and upserted' }),
      },
    },
    async handler(ctx) {
      const baseUrl = getBaseUrl(config);
      const result = await postJson<RagIngestResponse>(`${baseUrl}/rag/ingest`, {
        collection: ctx.input.collection,
        source_paths: ctx.input.sourcePaths,
        chunk_size: ctx.input.chunkSize,
        chunk_overlap: ctx.input.chunkOverlap,
      });
      ctx.logger.info(
        `Ingested ${result.chunks_ingested} chunks into "${result.collection}" as version ${result.index_version}`,
      );
      ctx.output('indexVersion', result.index_version);
      ctx.output('chunksIngested', result.chunks_ingested);
    },
  });
}

/**
 * `orchestration:rag-evaluate` — runs the LLM-as-judge Evaluate Gate
 * against a RAG index version and reports the pass rate.
 */
export function createRagEvaluateAction({ config }: ActionDeps) {
  return createTemplateAction({
    id: 'orchestration:rag-evaluate',
    description:
      'Runs the LLM-as-judge Evaluate Gate against a RAG index version and reports the pass rate.',
    schema: {
      input: {
        collection: z => z.string({ description: 'Qdrant collection name' }),
        indexVersion: z => z.string({ description: 'RAG index version to evaluate' }),
        evalCasesJson: z =>
          z.string({ description: 'JSON array of {"question": "..."} objects' }),
        model: z =>
          z
            .string({
              description:
                'model_name registered in litellm-config.yaml — including a self-hosted model deployed via the Serving LLM Golden Path. Defaults to "claude-sonnet-5"',
            })
            .optional(),
      },
      output: {
        passed: z => z.boolean({ description: 'True when pass_rate >= 0.8' }),
        passRate: z => z.number({ description: 'Fraction of eval_cases that passed the gate' }),
      },
    },
    async handler(ctx) {
      const baseUrl = getBaseUrl(config);
      const evalCases = parseEvalCasesJson(ctx.input.evalCasesJson);
      const result = await postJson<RagEvaluateResponse>(`${baseUrl}/rag/evaluate`, {
        collection: ctx.input.collection,
        index_version: ctx.input.indexVersion,
        eval_cases: evalCases,
        model: ctx.input.model,
      });
      ctx.logger.info(`RAG evaluate: passed=${result.passed} pass_rate=${result.pass_rate}`);
      ctx.output('passed', result.passed);
      ctx.output('passRate', result.pass_rate);
    },
  });
}

/**
 * `orchestration:rag-activate` — activates a RAG index version;
 * routers/chat.py starts retrieving from it immediately.
 */
export function createRagActivateAction({ config }: ActionDeps) {
  return createTemplateAction({
    id: 'orchestration:rag-activate',
    description: 'Activates a RAG index version for use by the chat endpoint.',
    schema: {
      input: {
        collection: z => z.string({ description: 'Qdrant collection name' }),
        indexVersion: z => z.string({ description: 'RAG index version to activate' }),
      },
      output: {
        activeVersion: z => z.string({ description: 'The version now active for this collection' }),
      },
    },
    async handler(ctx) {
      const baseUrl = getBaseUrl(config);
      const result = await postJson<RagActivateResponse>(`${baseUrl}/rag/activate`, {
        collection: ctx.input.collection,
        index_version: ctx.input.indexVersion,
      });
      ctx.logger.info(`Activated RAG index "${result.collection}" version ${result.active_version}`);
      ctx.output('activeVersion', result.active_version);
    },
  });
}

/**
 * `orchestration:draft-prompt` — registers a new (inactive) prompt version.
 */
export function createDraftPromptAction({ config }: ActionDeps) {
  return createTemplateAction({
    id: 'orchestration:draft-prompt',
    description: 'Registers a new (inactive) prompt version.',
    schema: {
      input: {
        name: z => z.string({ description: 'Persona key, e.g. "mlops"' }),
        persona: z => z.string({ description: 'Display name, e.g. "MLOps Assistant"' }),
        content: z => z.string({ description: 'System prompt content' }),
      },
      output: {
        version: z => z.string({ description: 'Newly registered prompt version — not active yet' }),
      },
    },
    async handler(ctx) {
      const baseUrl = getBaseUrl(config);
      const result = await postJson<DraftPromptResponse>(`${baseUrl}/prompts`, {
        name: ctx.input.name,
        persona: ctx.input.persona,
        content: ctx.input.content,
      });
      ctx.logger.info(`Drafted prompt "${result.name}" version ${result.version}`);
      ctx.output('version', result.version);
    },
  });
}

/**
 * `orchestration:evaluate-prompt` — runs the LLM-as-judge Evaluate Gate
 * against a prompt version and reports the pass rate.
 */
export function createEvaluatePromptAction({ config }: ActionDeps) {
  return createTemplateAction({
    id: 'orchestration:evaluate-prompt',
    description:
      'Runs the LLM-as-judge Evaluate Gate against a prompt version and reports the pass rate.',
    schema: {
      input: {
        name: z => z.string({ description: 'Persona key' }),
        version: z => z.string({ description: 'Prompt version to evaluate' }),
        evalCasesJson: z =>
          z.string({ description: 'JSON array of {"question": "..."} objects' }),
        model: z =>
          z
            .string({
              description:
                'model_name registered in litellm-config.yaml — including a self-hosted model deployed via the Serving LLM Golden Path. Defaults to "claude-sonnet-5"',
            })
            .optional(),
      },
      output: {
        passed: z => z.boolean({ description: 'True when pass_rate >= 0.8' }),
        passRate: z => z.number({ description: 'Fraction of eval_cases that passed the gate' }),
      },
    },
    async handler(ctx) {
      const baseUrl = getBaseUrl(config);
      const evalCases = parseEvalCasesJson(ctx.input.evalCasesJson);
      const result = await postJson<EvaluatePromptResponse>(
        `${baseUrl}/prompts/${encodeURIComponent(ctx.input.name)}/evaluate`,
        {
          version: ctx.input.version,
          eval_cases: evalCases,
          model: ctx.input.model,
        },
      );
      ctx.logger.info(`Prompt evaluate: passed=${result.passed} pass_rate=${result.pass_rate}`);
      ctx.output('passed', result.passed);
      ctx.output('passRate', result.pass_rate);
    },
  });
}

/**
 * `orchestration:activate-prompt` — activates a prompt version;
 * routers/chat.py starts using it immediately.
 */
export function createActivatePromptAction({ config }: ActionDeps) {
  return createTemplateAction({
    id: 'orchestration:activate-prompt',
    description: 'Activates a prompt version for use by the chat endpoint.',
    schema: {
      input: {
        name: z => z.string({ description: 'Persona key' }),
        version: z => z.string({ description: 'Prompt version to activate' }),
      },
      output: {
        activeVersion: z => z.string({ description: 'The version now active for this persona' }),
      },
    },
    async handler(ctx) {
      const baseUrl = getBaseUrl(config);
      const result = await postJson<ActivatePromptResponse>(
        `${baseUrl}/prompts/${encodeURIComponent(ctx.input.name)}/activate`,
        { version: ctx.input.version },
      );
      ctx.logger.info(`Activated prompt "${result.name}" version ${result.active_version}`);
      ctx.output('activeVersion', result.active_version);
    },
  });
}
