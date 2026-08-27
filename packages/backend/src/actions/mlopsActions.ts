/**
 * Custom Scaffolder Actions that call `services/orchestration-api` — the
 * HTTP surface Golden Path #1 (Train->Track->Register) and #2
 * (Register->Deploy) drive. Business logic stays in orchestration-api
 * (CLAUDE.md); these actions only translate Scaffolder input/output and,
 * for training, poll the workflow status until it finishes.
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
        algorithm: z =>
          z.string({ description: 'Registry key, e.g. "XGBClassifier" — see algorithm_registry.py' }),
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
          algorithm: ctx.input.algorithm,
          target_column: ctx.input.targetColumn,
          id_columns: ctx.input.idColumns,
          time_column: ctx.input.timeColumn,
          base_model_uri: ctx.input.baseModelUri,
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
      },
      output: {
        filePath: z => z.string({ description: 'Workspace-relative path the manifest was written to' }),
      },
    },
    async handler(ctx) {
      const baseUrl = getBaseUrl(config);
      const { file_name: fileName, content } =
        await postJson<PrepareDeployResponse>(`${baseUrl}/deploy-model/prepare`, {
          model_name: ctx.input.modelName,
          model_version: ctx.input.modelVersion,
        });
      const absolutePath = path.join(ctx.workspacePath, fileName);
      await fs.mkdir(path.dirname(absolutePath), { recursive: true });
      await fs.writeFile(absolutePath, content, 'utf-8');
      ctx.logger.info(`Wrote deploy manifest to "${fileName}"`);
      ctx.output('filePath', fileName);
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
        prUrl: z => z.string({ description: 'URL of the deploy pull request' }),
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
