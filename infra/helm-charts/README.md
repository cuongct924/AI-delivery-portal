# helm-charts

Helm chart for each service (`orchestration-api`, `mlops-server`, `k8s-server`,
Portal Backstage). **Not implemented yet**, once the services are running
stably via `docker-compose.yml`.

Each chart is expected to live at `infra/helm-charts/<service-name>/` with
`Chart.yaml`, `values.yaml`, `templates/`.
