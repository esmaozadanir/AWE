"""awe.pull.fetch_raw_data -- jenerik kimlik doğrulama + HTTP GET (bkz. awe.config.PullConfig).

Gerçek bir dış sunucu olmadığı için `httpx.MockTransport` kullanılır -- bu, kendi kodumuzu
mock'lamak değil, httpx'in kendi test için sağladığı sahte bir ağ katmanı (yeni bir bağımlılık
gerekmiyor); istek/yanıt işleme mantığımızın kendisi gerçek şekilde çalıştırılır."""

from __future__ import annotations

import json

import httpx
import pytest

from awe.config.project_config import PullConfig
from awe.pull import PullAuthError, fetch_raw_data


def _client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_auth_type_none_sends_no_authorization_header():
    def handler(request: httpx.Request) -> httpx.Response:
        assert "authorization" not in request.headers
        return httpx.Response(200, json={"events": []})

    config = PullConfig(enabled=True, pull_url="https://example.com/data", auth_type="none")

    assert fetch_raw_data(config, client=_client(handler)) == {"events": []}


def test_bearer_env_attaches_token_from_environment(monkeypatch):
    monkeypatch.setenv("TESTSVC_TOKEN", "secret-token-123")

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer secret-token-123"
        return httpx.Response(200, json={"events": []})

    config = PullConfig(
        enabled=True, pull_url="https://example.com/data", auth_type="bearer_env", auth_env_var="TESTSVC_TOKEN"
    )
    fetch_raw_data(config, client=_client(handler))


def test_bearer_env_missing_token_sends_no_header(monkeypatch):
    monkeypatch.delenv("TESTSVC_MISSING_TOKEN", raising=False)

    def handler(request: httpx.Request) -> httpx.Response:
        assert "authorization" not in request.headers
        return httpx.Response(200, json={})

    config = PullConfig(
        enabled=True,
        pull_url="https://example.com/data",
        auth_type="bearer_env",
        auth_env_var="TESTSVC_MISSING_TOKEN",
    )
    fetch_raw_data(config, client=_client(handler))


def test_login_then_bearer_logs_in_then_fetches_with_token(monkeypatch):
    monkeypatch.setenv("TESTSVC_EMAIL", "user@example.com")
    monkeypatch.setenv("TESTSVC_PASSWORD", "hunter2")

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/auth/login":
            body = json.loads(request.content)
            assert body == {"email": "user@example.com", "password": "hunter2"}
            return httpx.Response(200, json={"token": "jwt-abc"})
        assert request.headers["authorization"] == "Bearer jwt-abc"
        return httpx.Response(200, json={"actions": []})

    config = PullConfig(
        enabled=True,
        pull_url="https://example.com/api/data/export",
        auth_type="login_then_bearer",
        login_url="https://example.com/auth/login",
        login_email_env_var="TESTSVC_EMAIL",
        login_password_env_var="TESTSVC_PASSWORD",
    )

    assert fetch_raw_data(config, client=_client(handler)) == {"actions": []}


def test_login_then_bearer_finds_nested_token_field(monkeypatch):
    """CompanyHelper'ın gerçek yanıt şekli gibi -- token üst seviyede değil `data` altında."""
    monkeypatch.setenv("TESTSVC_EMAIL", "user@example.com")
    monkeypatch.setenv("TESTSVC_PASSWORD", "hunter2")

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/auth/login":
            return httpx.Response(200, json={"success": True, "data": {"accessToken": "nested-jwt"}})
        assert request.headers["authorization"] == "Bearer nested-jwt"
        return httpx.Response(200, json={"ok": True})

    config = PullConfig(
        enabled=True,
        pull_url="https://example.com/export",
        auth_type="login_then_bearer",
        login_url="https://example.com/auth/login",
        login_email_env_var="TESTSVC_EMAIL",
        login_password_env_var="TESTSVC_PASSWORD",
    )
    fetch_raw_data(config, client=_client(handler))


def test_login_then_bearer_missing_credentials_raises():
    config = PullConfig(
        enabled=True,
        pull_url="https://example.com/export",
        auth_type="login_then_bearer",
        login_url="https://example.com/auth/login",
        login_email_env_var="MISSING_EMAIL_VAR",
        login_password_env_var="MISSING_PASSWORD_VAR",
    )

    with pytest.raises(PullAuthError):
        fetch_raw_data(config, client=_client(lambda r: httpx.Response(200, json={})))


def test_login_then_bearer_no_token_in_response_raises(monkeypatch):
    monkeypatch.setenv("TESTSVC_EMAIL", "user@example.com")
    monkeypatch.setenv("TESTSVC_PASSWORD", "hunter2")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"unexpected": "shape"})

    config = PullConfig(
        enabled=True,
        pull_url="https://example.com/export",
        auth_type="login_then_bearer",
        login_url="https://example.com/auth/login",
        login_email_env_var="TESTSVC_EMAIL",
        login_password_env_var="TESTSVC_PASSWORD",
    )

    with pytest.raises(PullAuthError):
        fetch_raw_data(config, client=_client(handler))


def test_unknown_auth_type_raises_value_error():
    config = PullConfig(enabled=True, pull_url="https://example.com/data", auth_type="oauth2")

    with pytest.raises(ValueError):
        fetch_raw_data(config, client=_client(lambda r: httpx.Response(200, json={})))


def test_missing_pull_url_raises_value_error():
    config = PullConfig(enabled=True, pull_url=None, auth_type="none")

    with pytest.raises(ValueError):
        fetch_raw_data(config)
