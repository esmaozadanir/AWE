"""Session içi deterministik Observation sıralaması (bölüm 33-34)."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Sequence

from awe.domain.enums import OrderingConfidence
from awe.domain.observation import Observation


def group_by_session(observations: Iterable[Observation]) -> dict[str, list[Observation]]:
    """Tek bir project_id + subject_id kapsamındaki Observation'ları session_id'ye böler.

    Çağıran taraf, girdi observation'ların tek bir proje ve subject'e ait olduğunu garanti
    etmelidir; bu fonksiyon projectId/subjectId izolasyonunu tekrar doğrulamaz.
    """

    groups: dict[str, list[Observation]] = defaultdict(list)
    for obs in observations:
        groups[obs.session_id].append(obs)
    return dict(groups)


def order_session(observations: Sequence[Observation]) -> tuple[list[Observation], OrderingConfidence]:
    """Bir session'ın observation'larını deterministik sıraya sokar.

    Sıralama yalnızca timestamp + event_id (tie-break) kullanır; girdi batch sırasından
    bağımsız olarak her zaman aynı sonucu üretir. Motor hiçbir zaman kaynaktan bir sıra
    numarası (sequenceNo) istemez ya da uydurmaz — aynı timestamp'e sahip iki observation'ın
    gerçek temporal sırası bilinmiyorsa bunu `OrderingConfidence.LOW` ile açıkça işaretleriz,
    event_id'ye göre yapılan tie-break sahte bir kesinlik iddiası değildir, yalnızca
    deterministik (her çalıştırmada aynı) bir sonuç garantisidir (bölüm 33).
    """

    if not observations:
        return [], OrderingConfidence.HIGH

    ordered = sorted(observations, key=lambda o: (o.timestamp, o.event_id))
    has_ambiguous_tie = any(
        ordered[i].timestamp == ordered[i + 1].timestamp for i in range(len(ordered) - 1)
    )
    confidence = OrderingConfidence.LOW if has_ambiguous_tie else OrderingConfidence.HIGH
    return ordered, confidence
