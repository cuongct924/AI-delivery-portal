#!/usr/bin/env bash
# Idempotent local setup for the K8s (kind) + Argo Workflows infra that backs
# Golden Path #1/#2 (see infra/k8s-local-cluster/, infra/argo-workflows/,
# adapters/argo_adapter.py). Safe to re-run: every step checks before it
# creates/mutates.
#
# Usage: bash scripts/setup-k8s-local.sh
set -euo pipefail

CLUSTER_NAME="ai-delivery-portal"
ARGO_NAMESPACE="argo"
WORKFLOW_NAMESPACE="default"
# Pin an install manifest version rather than tracking `stable`/`latest` so a
# re-run months from now can't silently pull a newer Argo release with
# different default RBAC/flags than what this script was written against.
ARGO_VERSION="v4.1.2"
ARGO_MANIFEST_URL="https://raw.githubusercontent.com/argoproj/argo-workflows/${ARGO_VERSION}/manifests/quick-start-minimal.yaml"
# Must match the extraPortMappings entry in kind-config.yaml (containerPort
# 32746 -> hostPort 2746) and stay in the NodePort range (30000-32767).
ARGO_NODE_PORT=32746

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
K8S_LOCAL_DIR="${REPO_ROOT}/infra/k8s-local-cluster"
ARGO_WORKFLOWS_DIR="${REPO_ROOT}/infra/argo-workflows"

for bin in kind kubectl; do
  if ! command -v "${bin}" >/dev/null 2>&1; then
    echo "ERROR: '${bin}' is not installed / not on PATH." >&2
    exit 1
  fi
done

echo "=== [1/6] kind cluster '${CLUSTER_NAME}' ==="
if kind get clusters 2>/dev/null | grep -qx "${CLUSTER_NAME}"; then
  echo "Cluster already exists, skipping create."
else
  # kind resolves a relative extraMounts.hostPath against the process's
  # current working directory, not against the config file's location — so
  # kind-config.yaml's `hostPath: ../../data` only lands on the repo's
  # data/ dir if we invoke `kind create` from inside infra/k8s-local-cluster/.
  (cd "${K8S_LOCAL_DIR}" && kind create cluster --config kind-config.yaml --name "${CLUSTER_NAME}")
fi
kubectl config use-context "kind-${CLUSTER_NAME}" >/dev/null

echo "=== [2/6] Argo Workflows ${ARGO_VERSION} (namespace ${ARGO_NAMESPACE}) ==="
kubectl get namespace "${ARGO_NAMESPACE}" >/dev/null 2>&1 || kubectl create namespace "${ARGO_NAMESPACE}"
# quick-start-minimal.yaml is the official install manifest (controller +
# server + CRDs + cluster-wide RBAC, no Postgres). It's cluster-scoped by
# default (ClusterRole/ClusterRoleBinding, no --namespaced controller flag),
# which is what lets the controller/server manage workflows submitted into
# the `default` namespace even though Argo itself runs in `argo` — the
# simplest way to satisfy the two WorkflowTemplates' `namespace: default`
# without a second Argo install or a --namespaced controller restriction.
kubectl apply -n "${ARGO_NAMESPACE}" -f "${ARGO_MANIFEST_URL}"

echo "=== [3/6] Waiting for workflow-controller/argo-server rollout ==="
kubectl -n "${ARGO_NAMESPACE}" rollout status deployment/workflow-controller --timeout=180s
kubectl -n "${ARGO_NAMESPACE}" rollout status deployment/argo-server --timeout=180s

echo "=== [4/6] Reconfiguring argo-server for local dev (server auth-mode, plain HTTP) ==="
# quick-start-minimal.yaml's argo-server defaults to
# `--auth-mode server --auth-mode client` over HTTPS (self-signed cert) —
# `client` mode expects a kubeconfig-derived bearer token, and HTTPS doesn't
# match ArgoAdapter's plain `http://localhost:2746` base URL. Local dev only:
# server-only auth-mode + --secure=false so ArgoAdapter's unauthenticated
# REST calls work as-is.
kubectl -n "${ARGO_NAMESPACE}" patch deployment argo-server --type=json \
  -p='[{"op": "replace", "path": "/spec/template/spec/containers/0/args", "value": ["server", "--auth-mode", "server", "--secure=false"]}]'
# NodePort (fixed port, matched by kind-config.yaml's extraPortMappings) over
# `kubectl port-forward`: it survives terminal restarts/reboots since it's
# just cluster state, not a process someone has to remember to keep running
# or restart after it drops.
kubectl -n "${ARGO_NAMESPACE}" patch svc argo-server --type=merge \
  -p="{\"spec\": {\"type\": \"NodePort\", \"ports\": [{\"name\": \"web\", \"port\": 2746, \"targetPort\": 2746, \"nodePort\": ${ARGO_NODE_PORT}}]}}"
kubectl -n "${ARGO_NAMESPACE}" rollout status deployment/argo-server --timeout=180s

echo "=== [5/6] ServiceAccount + RBAC for workflow pods (namespace ${WORKFLOW_NAMESPACE}) ==="
# Both WorkflowTemplates reference `serviceAccountName: train-register-workflow`.
# Role scope mirrors Argo's own documented minimal "executor" Role
# (docs/workflow-rbac.md, also shipped as the `executor` example Role in
# quick-start-minimal.yaml): the default (emissary) executor only needs to
# report task outcomes via workflowtaskresults — it does not call the K8s API
# for pod/log access the way the legacy k8sapi executor did, so pods
# get/list/watch would be unused privilege, not least-privilege.
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

echo "=== [6/6] Applying WorkflowTemplates ==="
kubectl apply \
  -f "${ARGO_WORKFLOWS_DIR}/train-register-template.yaml" \
  -f "${ARGO_WORKFLOWS_DIR}/fine-tune-template.yaml"

cat <<MSG

Done.

Argo Server is reachable at http://localhost:2746 (NodePort ${ARGO_NODE_PORT},
mapped by kind-config.yaml's extraPortMappings — no port-forward to keep
running). Verify with:
  curl http://localhost:2746/api/v1/workflows/${WORKFLOW_NAMESPACE}

Next steps:
  1. docker compose up -d          # mlflow, orchestration-api, etc.
  2. .venv/bin/dvc pull             # make sure data/fraud-detection-sample.csv exists on the host
  3. make run-orchestration-api
  4. yarn start                     # Scaffolder UI -> run a Golden Path template

To tear the cluster down: kind delete cluster --name ${CLUSTER_NAME}
MSG
