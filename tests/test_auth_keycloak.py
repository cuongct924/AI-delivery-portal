"""services/orchestration-api/auth/keycloak.py — patches `settings`/`jwt.decode`
directly, same pattern as tests/test_chat_router.py."""

from unittest.mock import patch

import pytest
from auth.keycloak import get_current_user
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials


def _bearer(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


def test_no_token_and_auth_disabled_returns_fake_dev_user() -> None:
    with patch("auth.keycloak.settings") as mock_settings:
        mock_settings.auth_enabled = False
        user = get_current_user(credentials=None)
    assert user == {"sub": "local-dev", "preferred_username": "dev"}


def test_no_token_and_auth_enabled_raises_401() -> None:
    with patch("auth.keycloak.settings") as mock_settings:
        mock_settings.auth_enabled = True
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(credentials=None)
    assert exc_info.value.status_code == 401


def test_valid_token_is_verified_even_when_auth_disabled() -> None:
    """A caller that presents a token gets it checked for real regardless of
    AUTH_ENABLED — what lets golden-paths-server get a trustworthy identity
    without flipping auth on for every caller (Backstage Scaffolder never
    sends a token — see packages/backend/src/actions/mlopsActions.ts)."""
    with (
        patch("auth.keycloak.settings") as mock_settings,
        patch("auth.keycloak._jwks", return_value={"keys": []}),
        patch("auth.keycloak.jwt.decode", return_value={"azp": "golden-paths-agent"}),
    ):
        mock_settings.auth_enabled = False
        user = get_current_user(credentials=_bearer("a-real-token"))
    assert user == {"azp": "golden-paths-agent"}


def test_invalid_token_raises_401_even_when_auth_disabled() -> None:
    """A caller that presents a bad token must not silently fall back to the
    fake dev user — that would mask a real bug in the caller."""
    with (
        patch("auth.keycloak.settings") as mock_settings,
        patch("auth.keycloak._jwks", return_value={"keys": []}),
        patch("auth.keycloak.jwt.decode", side_effect=Exception("bad signature")),
    ):
        mock_settings.auth_enabled = False
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(credentials=_bearer("a-bad-token"))
    assert exc_info.value.status_code == 401
