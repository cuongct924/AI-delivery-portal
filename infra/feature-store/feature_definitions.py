"""Feast feature repo definitions — `adapters/feature_store_adapter.py`'s
`FeastAdapter` connects here by default (`FEAST_REPO_PATH=infra/feature-store`).

`join_keys=["entity_id"]` is not a naming choice — it matches the column
name FeastAdapter itself hardcodes in its entity_df/entity_rows, so any
feature view added here must key on that same column to be reachable
through the adapter. If a real dataset's identifier column has a
different name, remap it via FileSource(field_mapping=...) here — never
in the adapter.
"""

import os
from datetime import timedelta

from feast import Entity, FeatureView, Field, FileSource
from feast.types import Float32, Int64, String
from feast.value_type import ValueType

entity = Entity(name="entity", join_keys=["entity_id"], value_type=ValueType.STRING)

# FEAST_S3_ENDPOINT_URL/FEAST_OFFLINE_STORE_PATH unset (or blank, per
# .env.example's convention for optional vars like GITHUB_TOKEN) -> local
# demo parquet, same "swap only env vars, code stays the same" convention
# data/README.md uses for DVC. `or` (not a bare .get() default) matters
# here — env_file: .env in docker-compose.yml passes a blank value through
# as an empty string, not an unset key, which .get()'s default wouldn't
# catch. Real deploys point FEAST_OFFLINE_STORE_PATH at an s3://<bucket>/...
# URI and set FEAST_S3_ENDPOINT_URL; credentials come from the same
# AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY DVC already uses.
transaction_features_source = FileSource(
    name="transaction_features_source",
    path=os.environ.get("FEAST_OFFLINE_STORE_PATH") or "data/transaction_features.parquet",
    s3_endpoint_override=os.environ.get("FEAST_S3_ENDPOINT_URL") or None,
    timestamp_field="event_timestamp",
    created_timestamp_column="created_timestamp",
)

transaction_features = FeatureView(
    name="transaction_features",
    entities=[entity],
    ttl=timedelta(days=365),
    schema=[
        Field(name="amount", dtype=Float32),
        Field(name="merchant_category", dtype=String),
        Field(name="hour_of_day", dtype=Int64),
    ],
    online=True,
    source=transaction_features_source,
    tags={"golden_path": "fraud-detection"},
)
