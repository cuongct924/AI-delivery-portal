"""Adapter for the Vector DB (Qdrant) — powers the RAG architecture (semantic
search over internal docs/techdocs/runbooks). Spun up via docker-compose.yml
(the `qdrant` service).

Note: this only accepts pre-computed vectors — the embedding step (Voyage AI
or self-hosted) happens at the layer calling this adapter, see
infra/vector-dbs/README.md.
"""

import os

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from adapters.interfaces import IVectorStoreAdapter


class QdrantAdapter(IVectorStoreAdapter):
    def __init__(self, url: str | None = None, collection: str = "ai-delivery-portal-docs"):
        self.url = url or os.getenv("QDRANT_URL", "http://localhost:6333")
        self.collection = collection
        self.client = QdrantClient(url=self.url)

    def ensure_collection(self, vector_size: int = 1536) -> None:
        if not self.client.collection_exists(self.collection):
            self.client.create_collection(
                collection_name=self.collection,
                vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
            )

    def upsert(self, ids: list[str], vectors: list[list[float]], payloads: list[dict]) -> dict:
        points = [
            PointStruct(id=i, vector=v, payload=p)
            for i, v, p in zip(ids, vectors, payloads, strict=True)
        ]
        result = self.client.upsert(collection_name=self.collection, points=points)
        return {"status": str(result.status)}

    def search(self, query_vector: list[float], top_k: int = 5) -> list[dict]:
        hits = self.client.query_points(
            collection_name=self.collection, query=query_vector, limit=top_k
        ).points
        return [{"id": h.id, "score": h.score, "payload": h.payload} for h in hits]
