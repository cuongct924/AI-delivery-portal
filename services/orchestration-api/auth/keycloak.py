"""OIDC authentication via Keycloak — every request from Portal/Agent goes
through here before touching real infrastructure. `auth_enabled=False` (the
local dev default) makes auth OPTIONAL rather than off: a caller that sends
no Bearer token still gets a fake dev user (Backstage Scaffolder actions
never send one — see packages/backend/src/actions/mlopsActions.ts's
postJson), but a caller that DOES send a token (golden-paths-server, using
its own Keycloak service-account identity — see
agents/mcp-servers/golden-paths-server/auth.py) gets it verified for real,
giving a trustworthy identity in logs even without flipping AUTH_ENABLED=true
globally. Set `AUTH_ENABLED=true` to require a valid token from everyone.
"""

import logging
from functools import lru_cache

import httpx
from core.config import settings
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import jwt

bearer_scheme = HTTPBearer(auto_error=False)
logger = logging.getLogger("orchestration_api.auth")


@lru_cache
def _jwks() -> dict:
    url = f"{settings.keycloak_url}/realms/{settings.keycloak_realm}/protocol/openid-connect/certs"
    response = httpx.get(url, timeout=5)
    response.raise_for_status()
    return response.json()


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict:
    if credentials is None:
        if not settings.auth_enabled:
            logger.info("authenticated as local-dev (no token, AUTH_ENABLED=false)")
            return {"sub": "local-dev", "preferred_username": "dev"}
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing Bearer token")

    # A token was presented — verify it for real regardless of AUTH_ENABLED.
    # Silently accepting an invalid token under dev-bypass would mask real
    # bugs in whichever caller thought it had a valid identity.
    try:
        claims = jwt.decode(
            credentials.credentials,
            _jwks(),
            algorithms=["RS256"],
            audience=settings.keycloak_client_id,
        )
    except Exception as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, f"Invalid token: {exc}") from exc

    identity = claims.get("azp") or claims.get("preferred_username") or claims.get("sub")
    logger.info("authenticated as %s", identity)
    return claims
