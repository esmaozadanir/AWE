"""Dış sunucudan HAM veri çekmek için jenerik HTTP istemcisi -- yalnızca kimlik doğrulama +
getirme jeneriktir. Çekilen ham veriyi AWE'nin canonical event şekline çevirmek (TRANSFORM)
her zaman servise özeldir ve bu modülün kapsamında DEĞİLDİR (bkz.
`scripts/external_sync_template.py`, `awe.config.PullConfig`).

İki kimlik doğrulama kalıbı desteklenir:
- `bearer_env`: `.env`deki sabit bir token doğrudan `Authorization: Bearer` olarak eklenir.
- `login_then_bearer`: önce email+şifreyle giriş isteği atılır, yanıttan JWT çıkarılır, sonra
  o token'la asıl veri isteği yapılır (CompanyHelper'ın kullandığı akışla aynı desen, bkz.
  `scripts/fetch_companyhelper_export.py`).
"""

from __future__ import annotations

import os
from typing import Any

import httpx

from awe.config import PullConfig

_TOKEN_KEYS = ("token", "accessToken", "access_token", "jwt")


class PullAuthError(Exception):
    """Kimlik doğrulama başarısız oldu -- eksik .env değeri, giriş isteği reddedildi, ya da
    giriş yanıtında beklenen alan adlarından hiçbiri bulunamadı."""


def _extract_token(data: Any) -> str | None:
    if not isinstance(data, dict):
        return None
    for key in _TOKEN_KEYS:
        value = data.get(key)
        if isinstance(value, str):
            return value
    nested = data.get("data")
    if isinstance(nested, dict):
        return _extract_token(nested)
    return None


def _bearer_token(config: PullConfig) -> str | None:
    if config.auth_env_var is None:
        return None
    return os.environ.get(config.auth_env_var)


def _login_then_bearer_token(config: PullConfig, client: httpx.Client) -> str:
    if not config.login_url:
        raise PullAuthError("auth_type='login_then_bearer' için login_url ayarlı değil")
    email = os.environ.get(config.login_email_env_var) if config.login_email_env_var else None
    password = os.environ.get(config.login_password_env_var) if config.login_password_env_var else None
    if not email or not password:
        raise PullAuthError(f"'{config.login_email_env_var}'/'{config.login_password_env_var}' .env'de bulunamadı")

    response = client.post(config.login_url, json={"email": email, "password": password}, timeout=15.0)
    if response.status_code >= 400:
        raise PullAuthError(f"giriş başarısız ({response.status_code}): {response.text}")

    token = _extract_token(response.json())
    if token is None:
        raise PullAuthError(f"giriş yanıtında token bulunamadı, beklenen alanlardan biri yok: {_TOKEN_KEYS}")
    return token


def _auth_headers(config: PullConfig, client: httpx.Client) -> dict[str, str]:
    if config.auth_type == "none":
        return {}
    if config.auth_type == "bearer_env":
        token = _bearer_token(config)
        return {"Authorization": f"Bearer {token}"} if token else {}
    if config.auth_type == "login_then_bearer":
        token = _login_then_bearer_token(config, client)
        return {"Authorization": f"Bearer {token}"}
    raise ValueError(f"bilinmeyen PullConfig.auth_type: '{config.auth_type}'")


def fetch_raw_data(config: PullConfig, client: httpx.Client | None = None) -> Any:
    """`config.pull_url`e, `config.auth_type`e göre kimlik doğrulayarak GET atar, ham JSON
    yanıtı (dict ya da list) döner. Yanıtı AWE'nin event şekline çevirmek (TRANSFORM) çağıranın
    işidir -- bu fonksiyon o şekli hiç bilmez.

    `client`, testlerde `httpx.MockTransport` ile sahte bir sunucuya bağlamak için opsiyonel
    olarak enjekte edilebilir; verilmezse gerçek bir `httpx.Client()` kullanılır."""
    if not config.pull_url:
        raise ValueError("PullConfig.pull_url ayarlı değil")

    owns_client = client is None
    http_client = client or httpx.Client()
    try:
        headers = _auth_headers(config, http_client)
        response = http_client.get(config.pull_url, headers=headers, timeout=15.0)
        response.raise_for_status()
        return response.json()
    finally:
        if owns_client:
            http_client.close()
