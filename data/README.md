# data

Datasets tracked with [DVC](https://dvc.org) — actual files live in an S3-compatible
remote (`minio` service in `docker-compose.yml` for local dev; swap in real Viettel
S3 credentials later, only `.env`'s `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY`
change, `.dvc/config` stays the same).

Only the small `.dvc` pointer files (md5 hash + size) are committed to git —
the real data goes to the `storage` remote configured in `.dvc/config`.

## First time (pull the demo dataset)

```bash
docker compose up -d minio
# create the bucket once — minio doesn't auto-create it
docker run --rm --network host minio/mc alias set local http://localhost:9000 minioadmin minioadmin
docker run --rm --network host minio/mc mb local/mlops-datasets
.venv/bin/dvc push   # uploads data/fraud-detection-sample.csv to the remote
.venv/bin/dvc pull   # (on another machine) downloads it back
```

## Adding a new dataset version

```bash
.venv/bin/dvc add data/<file>
git add data/<file>.dvc data/.gitignore
.venv/bin/dvc push
```

`dvc add` prints an md5 hash into the resulting `data/<file>.dvc` — that hash is
the `dataset_version` passed to `IModelRegistryAdapter.register_model()`
(`adapters/mlflow_adapter.py`), so a registered model version is traceable back
to the exact dataset file that trained it.
