# plugin-mlops-dashboard

Backstage frontend plugin (New Frontend System — `PageBlueprint` +
`createFrontendPlugin`) — a single page showing the state of the two
MLOps Golden Paths (Train -> Track -> Register, Register -> Deploy), kept
separate from Prompt Registry as requested.

Already wired into `packages/app-backstage/src/App.tsx`
(`features: [..., mlopsDashboardPlugin]`) — the page appears automatically
in the sidebar ("rest" menu, sorted by title) and at the `/mlops-dashboard`
route.

Data comes from `services/orchestration-api`, called through the Backstage
backend proxy — see `proxy.endpoints['/orchestration-api']` in the repo's
root `app-config.yaml`. Run `docker compose up` (or local `uvicorn`) before
opening this page, otherwise you'll see a fetch error.

## Endpoints

- `GET /orchestration-api/trigger-training/recent` — recent Argo Workflow
  runs (`[{name, phase, started_at}]`), rendered as the "Training Runs"
  table.
- `GET /orchestration-api/models` — registered model versions
  (`[{name, version, metrics, tags}]`), rendered as the "Registered Models"
  table. `tags.gate_passed` drives the Gate badge and `tags.deploy_pr_url`
  drives the Deploy PR link — both are absent until the corresponding
  pipeline step (`/policy-check`, `/deploy-model/record`) has run for that
  model version.

## Note

This package was hand-written to match the `@backstage/*` versions already
installed in `packages/app-backstage/package.json` (based on `backstage.json`
version 1.54.0), mirroring `plugins/prompt-registry`'s structure. If you
later run `yarn new` to scaffold another plugin, the Backstage CLI will
generate a similar structure automatically.
