import { useEffect, useState } from 'react';
import { discoveryApiRef, fetchApiRef, useApi } from '@backstage/core-plugin-api';
import {
  Page,
  Header,
  Content,
  Table,
  TableColumn,
  Progress,
  ResponseErrorPanel,
} from '@backstage/core-components';
import Chip from '@material-ui/core/Chip';
import Link from '@material-ui/core/Link';

/**
 * A single Argo Workflow summary, as returned by
 * `GET /trigger-training/recent` (services/orchestration-api/routers/models.py
 * `WorkflowSummary`). Field names and nullability mirror that Pydantic model
 * exactly — every field can be `None`/`null` (e.g. a workflow whose status
 * hasn't been reported yet).
 */
interface TrainingRun {
  readonly name: string | null;
  readonly phase: string | null;
  readonly started_at: string | null;
}

/**
 * A registered model version summary, as returned by `GET /models`
 * (services/orchestration-api/routers/models.py `ModelSummary`). `tags` may
 * carry `gate_passed` ("true"/"false", MLflow tags are always strings),
 * `gate_safety`/`gate_correctness`/`gate_relevance`, and `deploy_pr_url` —
 * all optional, set only once the corresponding pipeline step has run.
 */
interface RegisteredModel {
  readonly name: string;
  readonly version: string;
  readonly metrics: Readonly<Record<string, number>>;
  readonly tags: Readonly<Record<string, string>>;
}

const PHASE_COLORS: Readonly<Record<string, string>> = {
  Succeeded: '#4caf50',
  Failed: '#f44336',
  Error: '#f44336',
  Running: '#2196f3',
};

/** Renders an Argo Workflow phase as a colored chip, falling back to a neutral chip for unknown/missing phases. */
const PhaseChip = ({ phase }: { readonly phase: string | null }): JSX.Element => {
  const color = phase ? PHASE_COLORS[phase] : undefined;
  return (
    <Chip
      label={phase ?? 'Unknown'}
      size="small"
      style={color ? { backgroundColor: color, color: '#fff' } : undefined}
    />
  );
};

/** Renders the Evaluate Gate pass/fail badge derived from the `gate_passed` MLflow tag. */
const GateChip = ({ tags }: { readonly tags: Readonly<Record<string, string>> }): JSX.Element => {
  if (!('gate_passed' in tags)) {
    return <Chip label="Not checked" size="small" />;
  }
  const passed = tags.gate_passed === 'true';
  return (
    <Chip
      label={passed ? 'Passed' : 'Failed'}
      size="small"
      style={{ backgroundColor: passed ? '#4caf50' : '#f44336', color: '#fff' }}
    />
  );
};

const trainingRunColumns: TableColumn<TrainingRun>[] = [
  { title: 'Name', field: 'name', render: row => row.name ?? '—' },
  {
    title: 'Phase',
    field: 'phase',
    render: row => <PhaseChip phase={row.phase} />,
  },
  {
    title: 'Started At',
    field: 'started_at',
    render: row => (row.started_at ? new Date(row.started_at).toLocaleString() : '—'),
  },
];

const registeredModelColumns: TableColumn<RegisteredModel>[] = [
  { title: 'Name', field: 'name' },
  { title: 'Version', field: 'version' },
  {
    title: 'Metrics',
    field: 'metrics',
    render: row =>
      Object.entries(row.metrics)
        .map(([key, value]) => `${key}=${value}`)
        .join(', ') || '—',
  },
  {
    title: 'Gate',
    field: 'tags',
    render: row => <GateChip tags={row.tags} />,
  },
  {
    title: 'Deploy PR',
    field: 'tags',
    render: row =>
      row.tags.deploy_pr_url ? (
        <Link href={row.tags.deploy_pr_url} target="_blank" rel="noopener noreferrer">
          View PR
        </Link>
      ) : (
        '—'
      ),
  },
];

/** Dashboard page listing recent training-workflow runs and registered model versions for the MLOps Golden Paths. */
export const MlopsDashboardPage = (): JSX.Element => {
  const discoveryApi = useApi(discoveryApiRef);
  const { fetch } = useApi(fetchApiRef);

  const [trainingRuns, setTrainingRuns] = useState<TrainingRun[] | null>(null);
  const [trainingRunsError, setTrainingRunsError] = useState<Error | null>(null);

  const [models, setModels] = useState<RegisteredModel[] | null>(null);
  const [modelsError, setModelsError] = useState<Error | null>(null);

  useEffect(() => {
    // NOTE: a relative fetch() would hit the wrong origin and skip auth.
    discoveryApi
      .getBaseUrl('proxy')
      .then(proxyUrl => fetch(`${proxyUrl}/orchestration-api/trigger-training/recent`))
      .then(res => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then(setTrainingRuns)
      .catch(setTrainingRunsError);
  }, [discoveryApi, fetch]);

  useEffect(() => {
    discoveryApi
      .getBaseUrl('proxy')
      .then(proxyUrl => fetch(`${proxyUrl}/orchestration-api/models`))
      .then(res => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then(setModels)
      .catch(setModelsError);
  }, [discoveryApi, fetch]);

  return (
    <Page themeId="tool">
      <Header
        title="MLOps Dashboard"
        subtitle="Training runs and registered models for the Golden Path pipelines"
      />
      <Content>
        {trainingRunsError && <ResponseErrorPanel error={trainingRunsError} />}
        {!trainingRunsError && !trainingRuns && <Progress />}
        {trainingRuns && (
          <Table
            title="Training Runs"
            columns={trainingRunColumns}
            data={trainingRuns}
            options={{ search: true, paging: false }}
          />
        )}

        {modelsError && <ResponseErrorPanel error={modelsError} />}
        {!modelsError && !models && <Progress />}
        {models && (
          <Table
            title="Registered Models"
            columns={registeredModelColumns}
            data={models}
            options={{ search: true, paging: false }}
          />
        )}
      </Content>
    </Page>
  );
};
