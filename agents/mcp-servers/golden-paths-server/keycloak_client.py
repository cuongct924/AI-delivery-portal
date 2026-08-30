"""Keycloak client_credentials token fetch/cache — gives this server its own
verifiable service-account identity, distinct from any human, instead of a
self-reported header a caller could set to anything. orchestration-api
verifies the resulting JWT for real (see
services/orchestration-api/auth/keycloak.py) regardless of its own
AUTH_ENABLED setting, since a caller that presents a token always gets it
checked.

Client `golden-paths-agent` must exist in the `ai-delivery-portal` Keycloak
realm with `serviceAccountsEnabled=true` and an audience mapper adding
"orchestration-api" — provisioned via infra/keycloak/realm-export.json.
"""

import os
import time

import httpx

KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "http://localhost:8082")
KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM", "ai-delivery-portal")
KEYCLOAK_CLIENT_ID = os.getenv("KEYCLOAK_CLIENT_ID", "golden-paths-agent")
KEYCLOAK_CLIENT_SECRET = os.getenv("KEYCLOAK_CLIENT_SECRET", "golden-paths-agent-dev-secret")

_cached_token: str | None = None
_cached_expiry: float = 0.0


def get_access_token() -> str:
    """Return a cached client_credentials access token, refreshing it once expired."""
    global _cached_token, _cached_expiry
    now = time.monotonic()
    if _cached_token is not None and now < _cached_expiry:
        return _cached_token

    response = httpx.post(
        f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/token",
        data={
            "grant_type": "client_credentials",
            "client_id": KEYCLOAK_CLIENT_ID,
            "client_secret": KEYCLOAK_CLIENT_SECRET,
        },
        timeout=10,
    )
    response.raise_for_status()
    payload = response.json()
    # Refresh 10s early so a token doesn't expire mid-request.
    _cached_expiry = now + max(payload["expires_in"] - 10, 0)
    token: str = payload["access_token"]
    _cached_token = token
    return token


def auth_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {get_access_token()}"}
