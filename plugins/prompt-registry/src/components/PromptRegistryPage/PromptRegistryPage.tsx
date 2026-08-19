import { useEffect, useState } from 'react';
import {
  Page,
  Header,
  Content,
  Table,
  TableColumn,
  Progress,
  ResponseErrorPanel,
} from '@backstage/core-components';

type PromptVersion = {
  id: string;
  name: string;
  version: string;
  persona: string;
  content: string;
};

const columns: TableColumn<PromptVersion>[] = [
  { title: 'Name', field: 'name' },
  { title: 'Version', field: 'version' },
  { title: 'Persona', field: 'persona' },
  {
    title: 'Preview',
    field: 'content',
    render: row => `${row.content.slice(0, 80)}…`,
  },
];

export const PromptRegistryPage = () => {
  const [prompts, setPrompts] = useState<PromptVersion[] | null>(null);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    // Calls through the Backstage backend proxy (see app-config.yaml -> proxy.endpoints)
    // pointing to services/orchestration-api's GET /prompts.
    fetch('/api/proxy/orchestration-api/prompts')
      .then(res => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then(setPrompts)
      .catch(setError);
  }, []);

  return (
    <Page themeId="tool">
      <Header
        title="Prompt Registry"
        subtitle="Manage system prompt / persona versions for the AI Agent"
      />
      <Content>
        {error && <ResponseErrorPanel error={error} />}
        {!error && !prompts && <Progress />}
        {prompts && (
          <Table
            title="Prompts"
            columns={columns}
            data={prompts}
            options={{ search: true, paging: false }}
          />
        )}
      </Content>
    </Page>
  );
};
