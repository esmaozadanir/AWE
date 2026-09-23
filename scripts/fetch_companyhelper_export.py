#!/usr/bin/env python
"""CompanyHelper backend'inden (login -> JWT -> export) tek seferlik event verisi çeker.

AWE'ye YAZMAZ, hiçbir Observation/ingest çağrısı yapmaz -- yalnızca CompanyHelper'ın gerçek
event/session/action şeklini görüp bunun için bir AdapterMapping (config_examples/*.yaml)
yazabilmek amacıyla bir keşif betiğidir.

Kimlik bilgileri asla bu dosyaya YAZILMAZ: .env dosyasından okunur (bkz. .env.example) --
COMPANYHELPER_EMAIL / COMPANYHELPER_PASSWORD. .env zaten git'e girmez.

Akış (bize verilen, export path'i doğrulanıp düzeltildi -- /api/v1/export değil /api/data/export):
    POST {base_url}/auth/login  {email, password}  -> JWT token
    GET  {base_url}/api/data/export  (Authorization: Bearer <token>)  -> actions + sessions + events

NOT: /api/data/export şu an backend tarafında 500 ("Data export failed") dönüyor -- route var,
ama sunucu tarafında bir hata var (query param farkı değil; format=json/type=events/tarih
aralığı hiçbiri değiştirmedi). Bu betik hazır, backend düzeltilince direkt çalışacak.

Giriş veya token-çıkarma alan adları tahminimiz tutmazsa (gerçek API dokümantasyonu yok),
betik ham yanıtı basıp net bir hata ile durur -- sessizce yanlış varsayımda bulunmaz.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _env import load_env_file  # noqa: E402

_REPO_ROOT = Path(__file__).resolve().parent.parent
_ENV_PATH = _REPO_ROOT / ".env"
_OUT_PATH = _REPO_ROOT / "scratch" / "companyhelper_export.json"

_TOKEN_KEYS = ("token", "accessToken", "access_token", "jwt")


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


def _describe_shape(value: Any, indent: int = 0) -> None:
    """Gerçek değerleri DEĞİL, yalnızca anahtar adlarını/tiplerini/uzunlukları basar --
    export gerçek CompanyHelper kullanıcı verisi (PII) içerebilir, konsola/konuşmaya
    dökülmemesi için."""
    prefix = "  " * indent
    if isinstance(value, dict):
        for key, val in value.items():
            print(f"{prefix}{key}: {type(val).__name__}")
            if isinstance(val, (dict, list)):
                _describe_shape(val, indent + 1)
    elif isinstance(value, list):
        print(f"{prefix}[{len(value)} eleman]")
        if value:
            _describe_shape(value[0], indent + 1)


def main() -> None:
    load_env_file(_ENV_PATH)

    base_url = os.environ.get("COMPANYHELPER_BASE_URL")
    email = os.environ.get("COMPANYHELPER_EMAIL")
    password = os.environ.get("COMPANYHELPER_PASSWORD")
    if not base_url or not email or not password:
        sys.exit(
            "COMPANYHELPER_BASE_URL / COMPANYHELPER_EMAIL / COMPANYHELPER_PASSWORD .env dosyasında yok.\n"
            f".env.example'a bakıp {_ENV_PATH} dosyasını doldur (git'e girmez)."
        )

    with httpx.Client(base_url=base_url, timeout=15.0) as client:
        login_response = client.post("/auth/login", json={"email": email, "password": password})
        print(f"POST /auth/login -> {login_response.status_code}")
        if login_response.status_code >= 400:
            print(login_response.text)
            sys.exit("Giriş başarısız -- yukarıdaki gövdeye bak, alan adları (email/password) farklı olabilir.")

        login_data = login_response.json()
        token = _extract_token(login_data)
        if token is None:
            print(json.dumps(login_data, indent=2, ensure_ascii=False))
            sys.exit("Login yanıtında token bulunamadı -- yukarıdaki yapıya bakıp _TOKEN_KEYS'i güncelle.")

        export_response = client.get("/api/data/export", headers={"Authorization": f"Bearer {token}"})
        print(f"GET /api/data/export -> {export_response.status_code}")
        if export_response.status_code >= 400:
            print(export_response.text)
            sys.exit("Export başarısız.")

        export_data = export_response.json()

    _OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    _OUT_PATH.write_text(json.dumps(export_data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n{_OUT_PATH.stat().st_size} bayt yazıldı -> {_OUT_PATH} (git'e girmez)")

    print("\n=== ŞEKİL ÖZETİ (gerçek değerler değil, yalnızca alan adları/tipler) ===")
    _describe_shape(export_data)


if __name__ == "__main__":
    main()
