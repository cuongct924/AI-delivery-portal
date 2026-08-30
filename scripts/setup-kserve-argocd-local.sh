#!/usr/bin/env bash
# Installs KServe + Knative Serving + Kourier + ArgoCD on the local kind
# cluster, builds/loads images, applies the ArgoCD Applications. Idempotent.
# Run `bash scripts/setup-k8s-local.sh` first — kept separate since
# Knative/KServe's install chain is fragile and shouldn't risk the stable
# Argo Workflows setup.
#
# Usage: bash scripts/setup-kserve-argocd-local.sh
set -euo pipefail

CLUSTER_NAME="ai-delivery-portal"
ARGOCD_NAMESPACE="argocd"
KNATIVE_NAMESPACE="knative-serving"
# Pinned so re-runs don't silently pick up a newer release.
CERT_MANAGER_VERSION="v1.21.1"
KNATIVE_VERSION="knative-v1.23.0"
KSERVE_VERSION="v0.20.0"
ARGOCD_VERSION="v3.5.1"
# Must match kind-config.yaml's extraPortMappings.
ARGOCD_NODE_PORT=32748
PORTAL_NODE_PORT=32749
# No real domain on kind — a placeholder is enough for InferenceServices to reach Ready.
KSERVE_LOCAL_DOMAIN="kserve-local.dev"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

for bin in kind kubectl docker helm; do
  if ! command -v "${bin}" >/dev/null 2>&1; then
    echo "ERROR: '${bin}' is not installed / not on PATH." >&2
    exit 1
  fi
done

if ! kind get clusters 2>/dev/null | grep -qx "${CLUSTER_NAME}"; then
  echo "ERROR: cluster '${CLUSTER_NAME}' not found — run scripts/setup-k8s-local.sh first." >&2
  exit 1
fi
kubectl config use-context "kind-${CLUSTER_NAME}" >/dev/null

echo "=== [1/9] cert-manager ${CERT_MANAGER_VERSION} (KServe's webhook needs it) ==="
kubectl apply -f "https://github.com/cert-manager/cert-manager/releases/download/${CERT_MANAGER_VERSION}/cert-manager.yaml"
kubectl -n cert-manager rollout status deployment/cert-manager --timeout=180s
kubectl -n cert-manager rollout status deployment/cert-manager-webhook --timeout=180s
kubectl -n cert-manager rollout status deployment/cert-manager-cainjector --timeout=180s

echo "=== [2/9] Knative Serving ${KNATIVE_VERSION} — Serverless mode's base ==="
kubectl apply -f "https://github.com/knative/serving/releases/download/${KNATIVE_VERSION}/serving-crds.yaml"
kubectl apply -f "https://github.com/knative/serving/releases/download/${KNATIVE_VERSION}/serving-core.yaml"
kubectl -n "${KNATIVE_NAMESPACE}" rollout status deployment/controller --timeout=180s
kubectl -n "${KNATIVE_NAMESPACE}" rollout status deployment/webhook --timeout=180s

echo "=== [3/9] Kourier ${KNATIVE_VERSION} — lightweight networking layer (no Istio) ==="
kubectl apply -f "https://github.com/knative-extensions/net-kourier/releases/download/${KNATIVE_VERSION}/kourier.yaml"
kubectl patch configmap/config-network \
  --namespace "${KNATIVE_NAMESPACE}" \
  --type merge \
  --patch '{"data":{"ingress-class":"kourier.ingress.networking.knative.dev"}}'

echo "=== [4/9] config-domain — placeholder domain (no real LoadBalancer on kind) ==="
kubectl patch configmap/config-domain \
  --namespace "${KNATIVE_NAMESPACE}" \
  --type merge \
  --patch "{\"data\":{\"${KSERVE_LOCAL_DOMAIN}\":\"\"}}"

echo "=== [5/9] KServe ${KSERVE_VERSION} (Serverless is the default deployMode) ==="
# NOTE: verify these 2 filenames against the v${KSERVE_VERSION} release assets.
kubectl apply --server-side -f "https://github.com/kserve/kserve/releases/download/${KSERVE_VERSION}/kserve.yaml"
kubectl apply --server-side -f "https://github.com/kserve/kserve/releases/download/${KSERVE_VERSION}/kserve-cluster-resources.yaml"
kubectl -n kserve rollout status deployment/kserve-controller-manager --timeout=180s

echo "=== [6/9] ArgoCD ${ARGOCD_VERSION} ==="
kubectl get namespace "${ARGOCD_NAMESPACE}" >/dev/null 2>&1 || kubectl create namespace "${ARGOCD_NAMESPACE}"
# --force-conflicts: ArgoCD's CRDs exceed client-side apply's 256KB limit.
kubectl apply -n "${ARGOCD_NAMESPACE}" --server-side --force-conflicts \
  -f "https://raw.githubusercontent.com/argoproj/argo-cd/${ARGOCD_VERSION}/manifests/install.yaml"
kubectl -n "${ARGOCD_NAMESPACE}" rollout status deployment/argocd-server --timeout=300s

echo "=== [7/9] Reconfiguring argocd-server for local dev (plain HTTP, fixed NodePort) ==="
# --insecure: same reasoning as argo-server in setup-k8s-local.sh — plain
# HTTP for local dev instead of the default HTTPS + client-cert mode.
kubectl -n "${ARGOCD_NAMESPACE}" patch deployment argocd-server --type=json \
  -p='[{"op": "add", "path": "/spec/template/spec/containers/0/args/-", "value": "--insecure"}]'
kubectl -n "${ARGOCD_NAMESPACE}" patch svc argocd-server --type=merge \
  -p="{\"spec\": {\"type\": \"NodePort\", \"ports\": [{\"name\": \"http\", \"port\": 80, \"targetPort\": 8080, \"nodePort\": ${ARGOCD_NODE_PORT}}]}}"
kubectl -n "${ARGOCD_NAMESPACE}" rollout status deployment/argocd-server --timeout=180s \
  || echo "WARNING: argocd-server rollout still settling — continuing anyway."

echo "=== [8/9] Building + loading orchestration-api and portal images ==="
docker build -t orchestration-api:local -f "${REPO_ROOT}/services/orchestration-api/Dockerfile" "${REPO_ROOT}"
kind load docker-image orchestration-api:local --name "${CLUSTER_NAME}"

if [ ! -f "${REPO_ROOT}/packages/backend/dist/bundle.tar.gz" ]; then
  echo "ERROR: packages/backend/dist/bundle.tar.gz not found — run first:" >&2
  echo "  yarn install --immutable && yarn tsc && yarn build:backend" >&2
  exit 1
fi
docker build -t portal:local -f "${REPO_ROOT}/packages/backend/Dockerfile" "${REPO_ROOT}"
kind load docker-image portal:local --name "${CLUSTER_NAME}"

echo "=== [9/9] Applying the 3 ArgoCD Applications ==="
kubectl apply \
  -f "${REPO_ROOT}/infra/argocd/inference-services-app.yaml" \
  -f "${REPO_ROOT}/infra/argocd/orchestration-api-app.yaml" \
  -f "${REPO_ROOT}/infra/argocd/portal-app.yaml"

ARGOCD_PASSWORD="$(kubectl -n "${ARGOCD_NAMESPACE}" get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d)"

cat <<MSG

Done.

ArgoCD UI: http://localhost:${ARGOCD_NODE_PORT} (user: admin, password: ${ARGOCD_PASSWORD})
Portal (once orchestration-api/portal Applications finish syncing): http://localhost:${PORTAL_NODE_PORT}

Check sync status: kubectl get applications -n ${ARGOCD_NAMESPACE}
Check InferenceServices: kubectl get inferenceservice

Note: Serverless/Kourier on kind has no real LoadBalancer — actually
calling a deployed model's predict endpoint needs a Host header trick or
port-forward, out of scope here (KServeAdapter.predict() itself isn't
implemented yet). This setup only needs InferenceServices to reach Ready.

Re-run this script after changing infra/helm-charts/orchestration-api,
infra/helm-charts/portal, or anything under services/orchestration-api/ —
it rebuilds and reloads both images and re-applies the Applications
(ArgoCD's selfHeal picks up the rest automatically).
MSG
