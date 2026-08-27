VENV := .venv
PYTHON312 := python3.12
PY := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
UV := $(VENV)/bin/uv
RUFF := $(VENV)/bin/ruff
PYRIGHT := $(VENV)/bin/pyright
PYTEST := $(VENV)/bin/pytest
DVC := $(VENV)/bin/dvc

# Auto-loads .env (AWS_ACCESS_KEY_ID, KEYCLOAK_URL, ...) into every recipe's
# environment — no more manually exporting before dvc/uvicorn/etc.
ifneq (,$(wildcard .env))
include .env
export
endif

# Per-service requirements.txt (source of truth) -> requirements.lock.txt
# (fully pinned incl. transitive deps, what each Dockerfile actually installs
# from). Kept separate per service on purpose: each is resolved for its own
# Docker build context and they are NOT required to agree with each other.
SERVICE_REQS := requirements-dev.txt \
	adapters/requirements.txt \
	services/orchestration-api/requirements.txt \
	agents/mcp-servers/mlops-server/requirements.txt \
	agents/mcp-servers/k8s-server/requirements.txt \
	agents/mcp-servers/metrics-server/requirements.txt \
	infra/argo-workflows/training-image/requirements.txt

.PHONY: venv install lock hooks lint format format-check typecheck test check \
	gitleaks checkov trivy security \
	run-orchestration-api run-mlops-mcp run-k8s-mcp run-metrics-mcp \
	dvc-pull dvc-push \
	clean-venv

# Pinned to 3.12 to match the Dockerfile base image (python:3.12-slim) — avoids
# version drift from the machine's default python3 (which may be newer via pyenv/brew).
# Install: brew install python@3.12
venv:
	$(PYTHON312) -m venv $(VENV)
	$(PIP) install --upgrade pip uv -q

## Installs from dev.lock.txt — one lock file resolved across every service's
## requirements.txt together, so the single shared local .venv (and your
## editor's Pylance, which reads it) can see every import in the repo without
## version conflicts. This file is NOT used by any Dockerfile — each service
## builds from its own requirements.lock.txt instead (see `make lock`).
## Also installs the pre-commit git hook.
install: venv
	$(UV) pip install -r dev.lock.txt
	$(VENV)/bin/pre-commit install

## Regenerates dev.lock.txt (merged, local-venv-only) and every service's own
## requirements.lock.txt (what its Dockerfile installs from) after you edit a
## requirements.txt. Review the diff, then commit the *.lock.txt files too.
## dev.lock.txt uses --universal (keeps each package's own platform markers,
## e.g. xgboost's Linux-only nvidia-nccl-cu12 dependency) so `make install`
## works on any dev machine's OS/arch, not just Linux. Each service's own
## *.lock.txt stays pinned to linux/x86_64 (--python-platform) to match the
## Docker images and GitHub Actions runners those actually build/run on.
## --index-strategy unsafe-best-match: training-image/requirements.txt's
## --extra-index-url (torch CPU wheels) otherwise makes uv refuse to
## resolve *any* package's version past what that one extra index offers
## (e.g. its stale urllib3), even for packages that never touch torch —
## both PyPI and download.pytorch.org are trusted here, so relaxing this
## uv default (meant to guard against dependency-confusion attacks) is safe.
## --emit-index-url writes --extra-index-url back into the generated
## *.lock.txt so `uv pip install -r *.lock.txt` (each Dockerfile's builder
## stage) can still find torch==...+cpu on its own — without this, the
## lock file has no record of which index that pinned version came from
## and the Docker build fails to resolve it.
lock: venv
	$(UV) pip compile $(SERVICE_REQS) --python-version 3.12 --universal --index-strategy unsafe-best-match --emit-index-url -o dev.lock.txt
	@for f in $(SERVICE_REQS); do \
		echo "Locking $$f..."; \
		$(UV) pip compile "$$f" --python-version 3.12 --python-platform x86_64-unknown-linux-gnu --index-strategy unsafe-best-match --emit-index-url -o "$${f%.txt}.lock.txt"; \
	done

hooks:
	$(VENV)/bin/pre-commit install

lint:
	$(RUFF) check .

format:
	$(RUFF) format .

## Non-mutating version of `format`, for CI — fails instead of rewriting files.
format-check:
	$(RUFF) format --check .

typecheck:
	$(PYRIGHT)

test:
	$(PYTEST)

check: lint format-check typecheck test

# ---------------------------------------------------------------------------
# Security scanners — same commands/args as the security-* and
# docker-build-and-scan jobs in .github/workflows/ci.yml, run from natively
# installed CLIs instead of Docker (faster, and doesn't need a working Docker
# daemon for gitleaks/checkov). Install once: brew install gitleaks checkov trivy
# ---------------------------------------------------------------------------

## Secret scanning — scans full git history, same as CI.
gitleaks:
	gitleaks detect --source . --redact -v

## IaC misconfig scan — same framework/skip-path as CI.
checkov:
	checkov --directory . --framework dockerfile,argo_workflows,github_actions \
		--skip-path node_modules --skip-path .venv --skip-path packages --skip-path plugins \
		--compact --quiet

## Builds the 4 service images, then Trivy-scans each — needs Docker running.
trivy:
	docker build -t orchestration-api:local -f services/orchestration-api/Dockerfile .
	docker build -t mlops-server:local -f agents/mcp-servers/mlops-server/Dockerfile .
	docker build -t k8s-server:local -f agents/mcp-servers/k8s-server/Dockerfile .
	docker build -t metrics-server:local -f agents/mcp-servers/metrics-server/Dockerfile .
	@for img in orchestration-api mlops-server k8s-server metrics-server; do \
		echo "=== Trivy scan: $$img ==="; \
		trivy image --severity CRITICAL,HIGH --ignore-unfixed --exit-code 1 "$$img:local"; \
	done

## Everything security — secrets + IaC + image CVEs.
security: gitleaks checkov trivy

run-orchestration-api:
	cd services/orchestration-api && PYTHONPATH=$(CURDIR) $(CURDIR)/$(PY) -m uvicorn main:app --reload

run-mlops-mcp:
	bash scripts/run-mcp-local.sh mlops

run-k8s-mcp:
	bash scripts/run-mcp-local.sh k8s

run-metrics-mcp:
	bash scripts/run-mcp-local.sh metrics

## Pulls/pushes the DVC-tracked dataset (data/) against the local MinIO
## remote — needs AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY, auto-loaded from
## .env above instead of exporting them by hand.
dvc-pull:
	$(DVC) pull

dvc-push:
	$(DVC) push

clean-venv:
	rm -rf $(VENV)
