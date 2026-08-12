"""Benefit Evaluator (bölüm 6.14): kısayolun kullanıcı ACTION sayısını azaltıp azaltmadığını
ölçer. Popülasyon istatistiği (medyan/p25/p75) yoktur — her Shortcut Intent kendi tek,
deterministik Benefit değerini taşır.

`planned_actions` yorumu: doğrudan-geçiş (route/open) bir anchor'da NAVIGATE'in kendisi
zaten anchor adımının karşılığıdır (kullanıcı hâlâ yapması gereken ayrı bir "son işlem"
bırakmaz) → `planned=1` (yalnızca kısayol dokunuşu). Action-surface bir anchor'da (PREFILL
dahil) motor o işlemi hiç çalıştırmaz; kullanıcı hâlâ son işlemi kendisi yapmalıdır →
`planned=2` (dokunuş + son işlem). Bölüm 6.14'ün iki örneği de (K1→K2→K3 NAVIGATE: planned=1;
open_messages→apply_filter: planned=2) bu ayrımla birebir örtüşür.
"""

from __future__ import annotations

from awe.domain.benefit import BenefitEvidence
from awe.domain.plan import ShortcutIntent
from awe.planner.anchors import ROUTE_OPEN_EFFECTS


def evaluate_benefit(intent: ShortcutIntent, scope_length: int) -> BenefitEvidence:
    is_direct_transition = intent.anchor.symbol[1] in ROUTE_OPEN_EFFECTS
    planned_actions = 1 if is_direct_transition else 2
    return BenefitEvidence(
        intent_id=intent.intent_id, observed_actions=scope_length, planned_actions=planned_actions
    )
