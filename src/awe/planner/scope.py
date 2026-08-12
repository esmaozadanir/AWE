"""Scope Projector (bölüm 6.10): yeni davranış kararı vermez, Anchor çözülmüşse family
prefix'ini mekanik olarak keser. Anchor ambiguous/unresolved ise scope boş kalır."""

from __future__ import annotations

from awe.domain.enums import AnchorStatus
from awe.domain.plan import Scope, ShortcutAnchor
from awe.domain.tokens import Symbol

_PROJECTABLE_STATUSES = frozenset({AnchorStatus.RESOLVED, AnchorStatus.ATTEMPT_ONLY})


def project_scope(family_symbols: tuple[Symbol, ...], variant_id: str, anchor: ShortcutAnchor) -> Scope:
    if anchor.status not in _PROJECTABLE_STATUSES:
        return Scope(variant_id=variant_id, included=(), excluded_trailing=())

    included = family_symbols[: anchor.position + 1]
    excluded_trailing = family_symbols[anchor.position + 1 :]
    return Scope(variant_id=variant_id, included=included, excluded_trailing=excluded_trailing)
