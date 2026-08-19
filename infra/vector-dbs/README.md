# vector-dbs

Vector Database powering the RAG architecture (semantic search over internal
docs, techdocs, runbooks...). Uses Qdrant — **works right away, locally** via
`docker compose up` (`qdrant` service, REST API at `http://localhost:6333`,
dashboard at `http://localhost:6333/dashboard`).

`adapters/vector_db_adapter.py` (`QdrantAdapter`) implements
`IVectorStoreAdapter` to upsert/search vectors — shared between
`agents/skills/` and `services/orchestration-api/`.

Helm chart to deploy Qdrant to a real K8s cluster — not implemented yet,
week 8+ (`docs/roadmap.md`).

## Note on the embedding model

The adapter only accepts pre-computed vectors (list[float]) — it does not
include the embedding step. When implemented for real, pick an embedding
model (Voyage AI, or self-hosted) and call it before passing data into
`QdrantAdapter.upsert()`/`.search()`.
