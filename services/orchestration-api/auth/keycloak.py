"""OIDC authentication via Keycloak — every request from Portal/Agent goes
through here before touching real infrastructure. `auth_enabled=False` (the
local dev default) skips the token check and returns a fake user — set
`AUTH_ENABLED=true` (see docker-compose.yml) to enforce authentication like a
real environment.
"""

from functools import lru_cache

import httpx
from core.config import settings
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import jwt

bearer_scheme = HTTPBearer(auto_error=False)


@lru_cache
def _jwks() -> dict:
    url = f"{settings.keycloak_url}/realms/{settings.keycloak_realm}/protocol/openid-connect/certs"
    response = httpx.get(url, timeout=5)
    response.raise_for_status()
    return response.json()


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict:
    if not settings.auth_enabled:
        return {"sub": "local-dev", "preferred_username": "dev"}

    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing Bearer token")

    try:
        claims = jwt.decode(
            credentials.credentials,
            _jwks(),
            algorithms=["RS256"],
            audience=settings.keycloak_client_id,
        )
    except Exception as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, f"Invalid token: {exc}") from exc

    return claims
