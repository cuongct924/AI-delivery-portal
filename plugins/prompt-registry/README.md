# plugin-prompt-registry

Backstage frontend plugin (New Frontend System — `PageBlueprint` +
`createFrontendPlugin`) — a page for managing system prompt / persona
versions for the AI Agent, kept separate from the Model Registry (MLflow)
as requested.

Already wired into `packages/app-backstage/src/App.tsx`
(`features: [..., promptRegistryPlugin]`) — the page appears automatically
in the sidebar ("rest" menu, sorted by title) and at the `/prompt-registry` route.

Data comes from `services/orchestration-api` (`GET /prompts`), called through
the Backstage backend proxy — see `proxy.endpoints['/orchestration-api']` in
the repo's root `app-config.yaml`. Run `docker compose up` (or local
`uvicorn`) before opening this page, otherwise you'll see a fetch error.

## Note

This package was hand-written to match the `@backstage/*` versions already
installed in `packages/app-backstage/package.json` (based on `backstage.json`
version 1.54.0). If you later run `yarn new` to scaffold another plugin, the
Backstage CLI will generate a similar structure automatically.
