import os from 'node:os';
import fs from 'node:fs/promises';
import path from 'node:path';
import { ConfigReader } from '@backstage/config';
import {
  createPolicyCheckAction,
  createPrepareDeployManifestAction,
  createRecordDeployAction,
  createTriggerTrainingAction,
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
      { modelName: 'fraud-detection', datasetUri: 'file:///data.csv' },
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
      { modelName: 'fraud-detection', datasetUri: 'file:///data.csv' },
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
      { modelName: 'fraud-detection', datasetUri: 'file:///data.csv' },
      '/tmp/workspace',
    );

    await expect(action.handler(ctx)).rejects.toThrow(/Timed out/);
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
    mockFetchResponses([
      {
        ok: true,
        body: { file_name: fileName, content: 'kind: InferenceService\n' },
      },
    ]);
    const action = createPrepareDeployManifestAction({ config });
    const { ctx, outputs } = createMockContext<typeof action>(
      { modelName: 'fraud-detection', modelVersion: '3' },
      workspacePath,
    );

    await action.handler(ctx);

    expect(outputs.filePath).toBe(fileName);
    const written = await fs.readFile(
      path.join(workspacePath, fileName),
      'utf-8',
    );
    expect(written).toBe('kind: InferenceService\n');

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
});
