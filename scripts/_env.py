"""`.env` dosyasını process ortam değişkenlerine yükleyen küçük, paylaşılan yardımcı.

Gerçek kimlik bilgileri hiçbir zaman bu dosyaya ya da git'e giren herhangi bir dosyaya YAZILMAZ
-- yalnızca `.env`den (gitignored) okunur."""

from __future__ import annotations

import os
from pathlib import Path


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        os.environ.setdefault(key.strip(), value.strip())
