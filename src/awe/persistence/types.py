"""SQLite, `DateTime(timezone=True)` sütunlarında dahi timezone bilgisini kalıcı olarak
saklamaz; okuma sırasında naive bir datetime döner. Bu, aware/naive datetime karışmasına yol
açar (bölüm 15'in açıkça yasakladığı durum). `UTCDateTime`, hem yazarken UTC'ye normalize eder
hem de okurken eksik tzinfo'yu UTC olarak geri tamamlar — böylece PostgreSQL'de zaten doğru
davranan kod SQLite'ta da sessizce bozulmaz.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime
from sqlalchemy.types import TypeDecorator


class UTCDateTime(TypeDecorator):
    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("naive datetime kabul edilmez; UTC'ye normalize edilmiş bir değer bekleniyor")
        return value.astimezone(UTC)

    def process_result_value(self, value: datetime | None, dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
