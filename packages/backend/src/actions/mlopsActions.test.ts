import os from 'node:os';
import fs from 'node:fs/promises';
import path from 'node:path';
import { ConfigReader } from '@backstage/config';
import {
  createModelSummaryAction,
  createPolicyCheckAction,
  createPrepareDeployManifestAction,
  createRecordDeployAction,
  createTriggerTrainingAction,
  createValidateDatasetAction,
} from './mlopsActions';

const BASE_URL = 'http://orchestration-api.test';
const config = new ConfigReader({ orchestrationApi: { baseUrl: BASE_URL } });

/**
 * Builds a minimal mock of the Scaffolder `ActionContext` for a given
 * action's handler — there is no `@backstage/plugin-scaffolder-node-test-utils`
 * dependency in this repo, so the handful of members these actions actually
 * touch are stubbed by hand. `TAction` pins the mock to that action's exact
 * (inferred) input/output types.
 */
function createMockContext<
  TAction extends { handler: (ctx: never) => Promise<void> },
>(
  input: Parameters<TAction['handler']>[0]['input'],
  workspacePath: string,
): {
  ctx: Parameters<TAction['handler']>[0];
  outputs: Record<string, unknown>;
} {
  const outputs: Record<string, unknown> = {};
  const mock = {
    logger: {
      info: jest.fn(),
      warn: jest.fn(),
      error: jest.fn(),
      debug: jest.fn(),
      child: jest.fn(),
    },
    workspacePath,
    input,
    checkpoint: jest.fn(),
    output: jest.fn((name: string, value: unknown) => {
      outputs[name] = value;
    }),
    createTemporaryDirectory: jest.fn(),
    getInitiatorCredentials: jest.fn(),
    task: { id: 'test-task' },
  };
  // No official test-utils package for this Backstage version — a cast is
  // the standard way to hand a hand-rolled mock to a strongly-typed handler.
  return { ctx: mock as unknown as Parameters<TAction['handler']>[0], outputs };
}

function mockFetchResponses(
  responses: readonly { readonly ok: boolean; readonly body: unknown }[],
): jest.Mock {
  const fetchMock = jest.fn();
  responses.forEach(({ ok, body }) => {
    fetchMock.mockImplementationOnce(async () => ({
      ok,
      status: ok ? 200 : 500,
      json: async () => body,
      text: async () => JSON.stringify(body),
    }));
  });
  global.fetch = fetchMock as unknown as typeof fetch;
  return fetchMock;
}

describe('orchestration:trigger-training', () => {
  it('polls until Succeeded and outputs the final phase and model version', async () => {
    mockFetchResponses([
      { ok: true, body: { workflow_name: 'wf-1' } },
      { ok: true, body: { name: 'wf-1', phase: 'Running', message: null } },
      { ok: true, body: { name: 'wf-1', phase: 'Succeeded', message: null } },
      { ok: true, body: { name: 'fraud-detection', version: '3' } },
    ]);
    const action = createTriggerTrainingAction({ config, pollIntervalMs: 1 });
    const { ctx, outputs } = createMockContext<typeof action>(
      {
        modelName: 'fraud-detection',
        datasetUri: 'file:///data.csv',
        taskType: 'classification',
        algorithm: 'LogisticRegression',
      },
      '/tmp/workspace',
    );

    await action.handler(ctx);

    expect(outputs.workflowName).toBe('wf-1');
    expect(outputs.phase).toBe('Succeeded');
    expect(outputs.modelVersion).toBe('3');
  });

  it('throws with the status message when the workflow fails', async () => {
    mockFetchResponses([
      { ok: true, body: { workflow_name: 'wf-2' } },
      {
        ok: true,
        body: { name: 'wf-2', phase: 'Failed', message: 'training script exited 1' },
      },
    ]);
    const action = createTriggerTrainingAction({ config, pollIntervalMs: 1 });
    const { ctx } = createMockContext<typeof action>(
      {
        modelName: 'fraud-detection',
        datasetUri: 'file:///data.csv',
        taskType: 'classification',
        algorithm: 'LogisticRegression',
      },
      '/tmp/workspace',
    );

    await expect(action.handler(ctx)).rejects.toThrow(
      'training script exited 1',
    );
  });

  it('throws a timeout error when no terminal phase is reached in time', async () => {
    const fetchMock = jest.fn();
    fetchMock.mockImplementationOnce(async () => ({
      ok: true,
      status: 200,
      json: async () => ({ workflow_name: 'wf-3' }),
      text: async () => '',
    }));
    fetchMock.mockImplementation(async () => ({
      ok: true,
      status: 200,
      json: async () => ({ name: 'wf-3', phase: 'Running', message: null }),
      text: async () => '',
    }));
    global.fetch = fetchMock as unknown as typeof fetch;
    const action = createTriggerTrainingAction({
      config,
      pollIntervalMs: 1,
      pollTimeoutMs: 5,
    });
    const { ctx } = createMockContext<typeof action>(
      {
        modelName: 'fraud-detection',
        datasetUri: 'file:///data.csv',
        taskType: 'classification',
        algorithm: 'LogisticRegression',
      },
      '/tmp/workspace',
    );

    await expect(action.handler(ctx)).rejects.toThrow(/Timed out/);
  });

  it('forwards architecture and DL hyperparameters to the orchestration API', async () => {
    const fetchMock = mockFetchResponses([
      { ok: true, body: { workflow_name: 'wf-4' } },
      { ok: true, body: { name: 'wf-4', phase: 'Succeeded', message: null } },
      { ok: true, body: { name: 'sensor-forecast', version: '1' } },
    ]);
    const action = createTriggerTrainingAction({ config, pollIntervalMs: 1 });
    const { ctx } = createMockContext<typeof action>(
      {
        modelName: 'sensor-forecast',
        datasetUri: 'file:///sensor.csv',
        taskType: 'regression',
        architecture: 'lstm',
        targetColumn: 'target',
        timeColumn: 'timestamp',
        sequenceLength: 10,
        numLayers: 2,
        hiddenSize: 32,
        learningRate: 0.001,
        epochs: 20,
        batchSize: 16,
      },
      '/tmp/workspace',
    );

    await action.handler(ctx);

    const [, requestInit] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(JSON.parse(requestInit.body as string)).toEqual({
      model_name: 'sensor-forecast',
      dataset_uri: 'file:///sensor.csv',
      task_type: 'regression',
      architecture: 'lstm',
      target_column: 'target',
      time_column: 'timestamp',
      sequence_length: 10,
      num_layers: 2,
      hidden_size: 32,
      learning_rate: 0.001,
      epochs: 20,
      batch_size: 16,
    });
  });

  it('forwards BYOC fields to the orchestration API when algorithm is custom', async () => {
    const fetchMock = mockFetchResponses([
      { ok: true, body: { workflow_name: 'wf-5' } },
      { ok: true, body: { name: 'wf-5', phase: 'Succeeded', message: null } },
      { ok: true, body: { name: 'custom-model', version: '1' } },
    ]);
    const action = createTriggerTrainingAction({ config, pollIntervalMs: 1 });
    const { ctx } = createMockContext<typeof action>(
      {
        modelName: 'custom-model',
        datasetUri: 'file:///fraud.csv',
        taskType: 'classification',
        algorithm: 'custom',
        targetColumn: 'is_fraud',
        codeRepoUrl: 'https://github.com/dev/my-training-code',
        entrypointPath: 'my_train.py',
        customConfig: '{"lr": 0.01}',
      },
      '/tmp/workspace',
    );

    await action.handler(ctx);

    const [, requestInit] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(JSON.parse(requestInit.body as string)).toEqual({
      model_name: 'custom-model',
      dataset_uri: 'file:///fraud.csv',
      task_type: 'classification',
      algorithm: 'custom',
      target_column: 'is_fraud',
      code_repo_url: 'https://github.com/dev/my-training-code',
      entrypoint_path: 'my_train.py',
      custom_config: '{"lr": 0.01}',
    });
  });

  it('forwards HPO fields to the orchestration API when searchStrategy is not fixed', async () => {
    const fetchMock = mockFetchResponses([
      { ok: true, body: { workflow_name: 'wf-6' } },
      { ok: true, body: { name: 'wf-6', phase: 'Succeeded', message: null } },
      { ok: true, body: { name: 'sensor-forecast', version: '1' } },
    ]);
    const action = createTriggerTrainingAction({ config, pollIntervalMs: 1 });
    const { ctx } = createMockContext<typeof action>(
      {
        modelName: 'sensor-forecast',
        datasetUri: 'file:///sensor.csv',
        taskType: 'regression',
        architecture: 'mlp',
        targetColumn: 'target',
        searchStrategy: 'bayesian',
        numTrials: 20,
        searchSpaceJson: '{"learning_rate": {"low": 0.0001, "high": 0.1}}',
        objectiveMetric: 'r2',
        objectiveDirection: 'maximize',
      },
      '/tmp/workspace',
    );

    await action.handler(ctx);

    const [, requestInit] = fetchMock.mock.calls[0] as [string, RequestInit];
    const body = JSON.parse(requestInit.body as string);
    expect(body.search_strategy).toBe('bayesian');
    expect(body.num_trials).toBe(20);
    expect(body.search_space_json).toBe('{"learning_rate": {"low": 0.0001, "high": 0.1}}');
    expect(body.objective_metric).toBe('r2');
    expect(body.objective_direction).toBe('maximize');
  });
});

describe('orchestration:validate-dataset', () => {
  it('outputs results and does not throw when nothing is blocking', async () => {
    mockFetchResponses([
      {
        ok: true,
        body: [
          { check_name: 'check_missing_values', severity: 'info', message: 'clean', details: {} },
          {
            check_name: 'check_class_imbalance',
            severity: 'warning',
            message: 'minority class is 3%',
            details: {},
          },
        ],
      },
    ]);
    const action = createValidateDatasetAction({ config });
    const { ctx, outputs } = createMockContext<typeof action>(
      { datasetUri: 'file:///data.csv', taskType: 'classification', targetColumn: 'is_fraud' },
      '/tmp/workspace',
    );

    await action.handler(ctx);

    expect(outputs.results).toEqual([
      { checkName: 'check_missing_values', severity: 'info', message: 'clean' },
      { checkName: 'check_class_imbalance', severity: 'warning', message: 'minority class is 3%' },
    ]);
  });

  it('throws with the blocking checks summary when any check is blocking', async () => {
    mockFetchResponses([
      {
        ok: true,
        body: [
          {
            check_name: 'check_missing_values',
            severity: 'blocking',
            message: "target column 'is_fraud' has 2 missing value(s)",
            details: {},
          },
        ],
      },
    ]);
    const action = createValidateDatasetAction({ config });
    const { ctx } = createMockContext<typeof action>(
      { datasetUri: 'file:///data.csv', taskType: 'classification', targetColumn: 'is_fraud' },
      '/tmp/workspace',
    );

    await expect(action.handler(ctx)).rejects.toThrow('check_missing_values');
  });
});

describe('orchestration:model-summary', () => {
  it('outputs the task type and metrics', async () => {
    mockFetchResponses([
      {
        ok: true,
        body: {
          name: 'fraud-detection',
          version: '3',
          task_type: 'classification',
          metrics: { accuracy: 0.92 },
          tags: { task_type: 'classification' },
        },
      },
    ]);
    const action = createModelSummaryAction({ config });
    const { ctx, outputs } = createMockContext<typeof action>(
      { modelName: 'fraud-detection', modelVersion: '3' },
      '/tmp/workspace',
    );

    await action.handler(ctx);

    expect(outputs.taskType).toBe('classification');
    expect(outputs.metrics).toEqual({ accuracy: 0.92 });
  });
});

describe('orchestration:policy-check', () => {
  it('outputs passed=true and the metrics when the gate passes', async () => {
    mockFetchResponses([
      {
        ok: true,
        body: {
          passed: true,
          metrics: { accuracy: 0.92, precision: 0.85, recall: 0.8 },
          thresholds: { min_accuracy: 0.7, min_precision: 0.6, min_recall: 0.6 },
        },
      },
    ]);
    const action = createPolicyCheckAction({ config });
    const { ctx, outputs } = createMockContext<typeof action>(
      { modelName: 'fraud-detection', modelVersion: '3' },
      '/tmp/workspace',
    );

    await action.handler(ctx);

    expect(outputs.passed).toBe(true);
    expect(outputs.metrics).toEqual({ accuracy: 0.92, precision: 0.85, recall: 0.8 });
  });

  it('throws with the metrics summary when the gate rejects the model', async () => {
    mockFetchResponses([
      {
        ok: true,
        body: {
          passed: false,
          metrics: { accuracy: 0.4, precision: 0.3, recall: 0.3 },
          thresholds: { min_accuracy: 0.7, min_precision: 0.6, min_recall: 0.6 },
        },
      },
    ]);
    const action = createPolicyCheckAction({ config });
    const { ctx } = createMockContext<typeof action>(
      { modelName: 'fraud-detection', modelVersion: '3' },
      '/tmp/workspace',
    );

    await expect(action.handler(ctx)).rejects.toThrow('accuracy=0.4');
  });
});

describe('orchestration:prepare-deploy-manifest', () => {
  it('writes the rendered manifest into the workspace and outputs its path', async () => {
    const workspacePath = await fs.mkdtemp(
      path.join(os.tmpdir(), 'mlops-actions-test-'),
    );
    const fileName = 'infra/inference-services/fraud-detection/3.yaml';
    const fetchMock = mockFetchResponses([
      {
        ok: true,
        body: { file_name: fileName, content: 'kind: InferenceService\n', deployed: false },
      },
    ]);
    const action = createPrepareDeployManifestAction({ config });
    const { ctx, outputs } = createMockContext<typeof action>(
      { modelName: 'fraud-detection', modelVersion: '3' },
      workspacePath,
    );

    await action.handler(ctx);

    expect(outputs.filePath).toBe(fileName);
    expect(outputs.deployed).toBe(false);
    const written = await fs.readFile(
      path.join(workspacePath, fileName),
      'utf-8',
    );
    expect(written).toBe('kind: InferenceService\n');
    expect(fetchMock).toHaveBeenCalledWith(
      `${BASE_URL}/deploy-model/prepare`,
      expect.objectContaining({
        body: JSON.stringify({
          model_name: 'fraud-detection',
          model_version: '3',
          traffic_strategy: undefined,
          traffic_percent: undefined,
          release_strategy: undefined,
        }),
      }),
    );

    await fs.rm(workspacePath, { recursive: true, force: true });
  });

  it('forwards the traffic/release strategy fields and outputs deployed=true for instant', async () => {
    const workspacePath = await fs.mkdtemp(
      path.join(os.tmpdir(), 'mlops-actions-test-'),
    );
    const fileName = 'infra/inference-services/fraud-detection/4.yaml';
    const fetchMock = mockFetchResponses([
      {
        ok: true,
        body: { file_name: fileName, content: 'kind: InferenceService\n', deployed: true },
      },
    ]);
    const action = createPrepareDeployManifestAction({ config });
    const { ctx, outputs } = createMockContext<typeof action>(
      {
        modelName: 'fraud-detection',
        modelVersion: '4',
        trafficStrategy: 'canary',
        trafficPercent: 10,
        releaseStrategy: 'instant',
      },
      workspacePath,
    );

    await action.handler(ctx);

    expect(outputs.deployed).toBe(true);
    expect(fetchMock).toHaveBeenCalledWith(
      `${BASE_URL}/deploy-model/prepare`,
      expect.objectContaining({
        body: JSON.stringify({
          model_name: 'fraud-detection',
          model_version: '4',
          traffic_strategy: 'canary',
          traffic_percent: 10,
          release_strategy: 'instant',
        }),
      }),
    );

    await fs.rm(workspacePath, { recursive: true, force: true });
  });
});

describe('orchestration:record-deploy', () => {
  it('posts the PR URL and outputs recorded=true', async () => {
    const fetchMock = mockFetchResponses([
      {
        ok: true,
        body: {
          model_name: 'fraud-detection',
          model_version: '3',
          pr_url: 'https://github.com/org/repo/pull/1',
        },
      },
    ]);
    const action = createRecordDeployAction({ config });
    const { ctx, outputs } = createMockContext<typeof action>(
      {
        modelName: 'fraud-detection',
        modelVersion: '3',
        prUrl: 'https://github.com/org/repo/pull/1',
      },
      '/tmp/workspace',
    );

    await action.handler(ctx);

    expect(outputs.recorded).toBe(true);
    expect(fetchMock).toHaveBeenCalledWith(
      `${BASE_URL}/deploy-model/record`,
      expect.objectContaining({
        body: JSON.stringify({
          model_name: 'fraud-detection',
          model_version: '3',
          pr_url: 'https://github.com/org/repo/pull/1',
        }),
      }),
    );
  });

  it('omits prUrl for an instant release with no PR', async () => {
    const fetchMock = mockFetchResponses([
      {
        ok: true,
        body: { model_name: 'fraud-detection', model_version: '5', pr_url: null },
      },
    ]);
    const action = createRecordDeployAction({ config });
    const { ctx, outputs } = createMockContext<typeof action>(
      { modelName: 'fraud-detection', modelVersion: '5' },
      '/tmp/workspace',
    );

    await action.handler(ctx);

    expect(outputs.recorded).toBe(true);
    expect(fetchMock).toHaveBeenCalledWith(
      `${BASE_URL}/deploy-model/record`,
      expect.objectContaining({
        body: JSON.stringify({
          model_name: 'fraud-detection',
          model_version: '5',
          pr_url: undefined,
        }),
      }),
    );
  });
});
