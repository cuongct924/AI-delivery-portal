#!/usr/bin/env bash
# Sets up local kind + Argo Workflows infra for Golden Path #1/#2. Idempotent.
# Usage: bash scripts/setup-k8s-local.sh
set -euo pipefail

CLUSTER_NAME="ai-delivery-portal"
ARGO_NAMESPACE="argo"
WORKFLOW_NAMESPACE="default"
# Pinned so re-runs don't silently pick up a newer Argo release.
ARGO_VERSION="v4.1.2"
ARGO_MANIFEST_URL="https://raw.githubusercontent.com/argoproj/argo-workflows/${ARGO_VERSION}/manifests/quick-start-minimal.yaml"
# Must match kind-config.yaml's extraPortMappings and the NodePort range.
ARGO_NODE_PORT=32746

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
K8S_LOCAL_DIR="${REPO_ROOT}/infra/k8s-local-cluster"
ARGO_WORKFLOWS_DIR="${REPO_ROOT}/infra/argo-workflows"
# Must match the `image:` referenced in train-register-template.yaml's
# train-step — kind clusters don't pull from a registry, only `kind load`.
TRAINING_IMAGE_TAG="training-image:local"

for bin in kind kubectl docker; do
  if ! command -v "${bin}" >/dev/null 2>&1; then
    echo "ERROR: '${bin}' is not installed / not on PATH." >&2
    exit 1
  fi
done

echo "=== [1/7] kind cluster '${CLUSTER_NAME}' ==="
if kind get clusters 2>/dev/null | grep -qx "${CLUSTER_NAME}"; then
  echo "Cluster already exists, skipping create."
else
  # kind resolves extraMounts.hostPath relative to cwd, not the config file.
  (cd "${K8S_LOCAL_DIR}" && kind create cluster --config kind-config.yaml --name "${CLUSTER_NAME}")
fi
kubectl config use-context "kind-${CLUSTER_NAME}" >/dev/null

echo "=== [2/7] Argo Workflows ${ARGO_VERSION} (namespace ${ARGO_NAMESPACE}) ==="
kubectl get namespace "${ARGO_NAMESPACE}" >/dev/null 2>&1 || kubectl create namespace "${ARGO_NAMESPACE}"
# Cluster-scoped by default, so it can manage the `default` namespace's workflows too.
# --server-side: client-side apply's annotation exceeds Argo CRDs' 256KB limit.
kubectl apply --server-side --force-conflicts -n "${ARGO_NAMESPACE}" -f "${ARGO_MANIFEST_URL}"

echo "=== [3/7] Waiting for workflow-controller/argo-server rollout ==="
kubectl -n "${ARGO_NAMESPACE}" rollout status deployment/workflow-controller --timeout=300s
kubectl -n "${ARGO_NAMESPACE}" rollout status deployment/argo-server --timeout=300s

echo "=== [4/7] Reconfiguring argo-server for local dev (server auth-mode, plain HTTP) ==="
# Default HTTPS + client-auth mode doesn't match ArgoAdapter's plain HTTP calls.
# The readinessProbe must switch to HTTP too, or it keeps probing HTTPS on a
# plain-HTTP server, the pod never goes Ready, and the old pod never rotates out.
kubectl -n "${ARGO_NAMESPACE}" patch deployment argo-server --type=json \
  -p='[
    {"op": "replace", "path": "/spec/template/spec/containers/0/args", "value": ["server", "--auth-mode", "server", "--secure=false"]},
    {"op": "replace", "path": "/spec/template/spec/containers/0/readinessProbe/httpGet/scheme", "value": "HTTP"}
  ]'
# NodePort survives terminal restarts, unlike a port-forward process.
kubectl -n "${ARGO_NAMESPACE}" patch svc argo-server --type=merge \
  -p="{\"spec\": {\"type\": \"NodePort\", \"ports\": [{\"name\": \"web\", \"port\": 2746, \"targetPort\": 2746, \"nodePort\": ${ARGO_NODE_PORT}}]}}"
# A lingering old pod stuck Terminating shouldn't block the RBAC/WorkflowTemplate steps below.
kubectl -n "${ARGO_NAMESPACE}" rollout status deployment/argo-server --timeout=300s \
  || echo "WARNING: argo-server rollout still settling — continuing anyway."

echo "=== [5/7] ServiceAccount + RBAC for workflow pods (namespace ${WORKFLOW_NAMESPACE}) ==="
# Minimal executor Role — emissary executor only needs workflowtaskresults write access.
kubectl -n "${WORKFLOW_NAMESPACE}" apply -f - <<EOF
apiVersion: v1
kind: ServiceAccount
metadata:
  name: train-register-workflow
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: train-register-workflow
rules:
  - apiGroups: ["argoproj.io"]
    resources: ["workflowtaskresults"]
    verbs: ["create", "patch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: train-register-workflow
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: train-register-workflow
subjects:
  - kind: ServiceAccount
    name: train-register-workflow
    namespace: ${WORKFLOW_NAMESPACE}
EOF

echo "=== [6/7] Building + loading the training image (${TRAINING_IMAGE_TAG}) ==="
# Repo root as build context — the Dockerfile COPYs from
# infra/argo-workflows/training-image/, not the repo root itself.
docker build -t "${TRAINING_IMAGE_TAG}" -f "${ARGO_WORKFLOWS_DIR}/training-image/Dockerfile" "${REPO_ROOT}"
# kind clusters can't pull from a registry for a locally-tagged image —
# `kind load` copies it straight into every node's containerd.
kind load docker-image "${TRAINING_IMAGE_TAG}" --name "${CLUSTER_NAME}"

echo "=== [7/7] Applying the WorkflowTemplate ==="
kubectl apply -f "${ARGO_WORKFLOWS_DIR}/train-register-template.yaml"

cat <<MSG

Done.

Argo Server is reachable at http://localhost:2746 (NodePort ${ARGO_NODE_PORT},
mapped by kind-config.yaml's extraPortMappings — no port-forward to keep
running). Verify with:
  curl http://localhost:2746/api/v1/workflows/${WORKFLOW_NAMESPACE}

Next steps:
  1. docker compose up -d          # mlflow, orchestration-api, etc.
  2. .venv/bin/dvc pull             # make sure data/*.csv exist on the host
  3. make run-orchestration-api
  4. yarn start                     # Scaffolder UI -> run a Golden Path template

Re-run this script after changing anything under
infra/argo-workflows/training-image/ — it rebuilds and reloads the image.

To tear the cluster down: kind delete cluster --name ${CLUSTER_NAME}
MSG
