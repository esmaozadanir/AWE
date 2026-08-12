# AWE Mimarisi

Bu belge, `AWE_MVP_TASARIMI_BAGIMSIZ_INCELEME.md` spesifikasyonuna göre uygulanan mevcut motor
mimarisini açıklar. Motor, uygulamaya özel hiçbir iş kavramı içermez; yalnızca canonical
`(action, effect, screen, mapping_version, target, status, trigger, source)` alanları üzerinden
çalışır.

## 1. Uçtan uca katman sırası

```text
Raw Event
  ↓
1. Adapter                    (src/awe/adapter/)
  ↓
2. Classifier                 (src/awe/adapter/classification.py)
  ↓
3. O-Series Builder            (src/awe/series/, src/awe/ordering/)
  ↓
4. Episode Candidate Builder   (src/awe/episodes/)
  ↓
5. Exact Base Family           (src/awe/families/)
  ↓
6. Target Resolver             (src/awe/targeting/)
  ↓
7. Habit Evaluator             (src/awe/habit/)
  ↓
8. Screen Transition Evidence  (src/awe/screen_evidence/)
  ↓
9. Anchor Resolver             (src/awe/planner/anchors.py)
  ↓
10. Scope Projector            (src/awe/planner/scope.py)
  ↓
11. Destination Resolver       (src/awe/planner/destination.py)
  ↓
12. Shortcut Intent Builder    (src/awe/planner/intent.py)
  ↓                ↓
13. Risk           14. Benefit  (src/awe/risk/, src/awe/benefit/)
  ↓                ↓
15. Selector                   (src/awe/selection/)
  ↓
16. Lifecycle (suggestion state) (src/awe/lifecycle/) — spesifikasyonun kapsamı dışında,
    mevcut mekanizma korunmuştur (bkz. bölüm 9.11)
```

`src/awe/services/analysis.py::analyze_subject` bu zinciri uçtan uca bağlar.
`src/awe/services/ingestion.py::ingest_event` yalnızca raw event kabulünü yapar (Adapter'a
kadar), analiz ayrı bir çağrıdır.

## 2. Batch/recompute modeli — kasıtlı bir mimari karar

Eski tasarımdan farklı olarak bu motor **artımlı state tutmaz**. Her `analyze_subject` çağrısı:

1. Subject'in **tüm** `observations` satırlarını okur (yalnızca "işlenmemiş" olanları değil).
2. O-Series Builder'ı her session için sıfırdan çalıştırır.
3. Episode Candidate Builder'ı **tüm** O-Series'ler üzerinde sıfırdan çalıştırır (O(n²)
   pairwise ortak-koşu karşılaştırması dahil).
4. Family/TargetVariant/Habit/Anchor/Scope/Destination/Intent/Risk/Benefit/Selector'ı sıfırdan
   hesaplar.
5. `habit_evaluations` ve `shortcut_intents` tablolarını tamamen siler ve yeniden yazar.
6. Yalnızca `suggestions` tablosu gerçek kalıcı state taşır (dismiss/cooldown) ve bu yüzden
   upsert edilir.

Bu, bilinçli bir sadeleştirmedir: Family/TargetVariant kimlikleri artık **deterministiktir**
(exact sembol dizisinden türetilen hash — bkz. `awe.families.matching.compute_family_id`),
yani "hangi family'ye ait" sorusu artımlı bir eşleştirme kararı değil, saf bir hesaplamadır.
Spesifikasyon bölüm 9.10 incremental/online state yönetimini açıkça bu prototipin kapsamı
dışında bırakır — bu motor o sınırı bilerek kabul eder. Gerçek zamanlı/yüksek hacimli bir
üretim dağıtımı, Episode Candidate Builder'ın O(n²) maliyetini sınırlamak için bir sonraki
adım olarak artımlı hesaplama katmanına ihtiyaç duyacaktır; bu tasarımın kapsamı dışıdır.

## 3. Canonical Observation

```python
@dataclass(frozen=True, slots=True)
class Observation:
    event_id: str
    project_id: str
    subject_id: str
    session_id: str
    timestamp: datetime
    action: str
    source: ObservationSource
    trigger: ObservationTrigger
    effect: ObservationEffect
    status: ObservationStatus
    screen: str | None
    target: str | None
    duration_ms: int | None
    mapping_version: str
    quality: ObservationQuality
```

`role`, `widget`, `parameters`, `breaksEpisode`, `appVersion` kasıtlı olarak yoktur — bunlar
eski tasarımın kalıntılarıydı; yeni sözleşme (bölüm 4) bunları tanımamaz.

`target` tri-state semantiği: `None` = raw event'te `target` açıkça `null` gönderildi ("açıkça
hedef yok"); raw payload'da `target` anahtarı hiç yoksa değer yine `None` olur ama
`quality.missing_target_field=True` ile işaretlenir ("hedef verisi bilinmiyor").

## 4. Canonical sözlükler (`src/awe/domain/enums.py`)

| Sözlük | Değerler |
|---|---|
| `ObservationSource` | client, server, system, unknown |
| `ObservationTrigger` | button, keyboard, voice, long_press, hardware, biometric, swipe, drag, navigation, notification, deeplink, automatic, **shortcut** (bölüm 4'te yok, kasıtlı ek — bkz. `docs/engine-decisions.md`), unknown |
| `ObservationEffect` | submit, create, delete, confirm, update, toggle, route, request, open, download, input, select, filter, sort, focus, view, none, unknown |
| `ObservationStatus` | success, fail, cancel, unknown |
| `EventClassification` | action, context, ignore (hesaplanan, kalıcı olmayan) |

## 5. Sembol ve exact eşleşme

```text
Symbol = (action, effect, screen, mapping_version)
```

`screen` sembolün parçasıdır — eski tasarımdan farklı olarak fuzzy benzerlik veya ayrıştırıcı
ağırlıklandırma yoktur (bölüm 6.4-6.5). Exact Base Family, tamamen aynı sembol dizisini
paylaşan `EpisodeCandidate`'ları hash-tabanlı olarak gruplar; bir family = bir exact dizi.

## 6. Bilinen sınırlamalar

1. **Artımlı state yok** (yukarıda bölüm 2) — büyük event geçmişlerinde Episode Candidate
   Builder'ın O(n²) maliyeti her analiz çağrısında tekrar ödenir.
2. **Exact fragmentation** (bölüm 9.3): fuzzy tolerans olmadığı için varyasyonlu gerçek
   alışkanlıklar (ör. ara adım eklenmiş/çıkarılmış akışlar) ayrı family'lere bölünebilir.
   Precision lehine bilinçli kabul edilmiş bir ödünleşim.
3. **PostgreSQL hiç test edilmedi** — yalnızca portable SQLAlchemy tipleri kullanılır ama bu
   ortamda gerçek Postgres'e karşı test edilmemiştir.
4. **Suggestion lifecycle spesifikasyon dışı** (bölüm 9.11) — gösterim zamanlaması, aynı anda
   kaç öneri gösterileceği, runtime target/screen validasyonu ayrı bir katman olarak
   tasarlanmamıştır; mevcut basit dismiss/cooldown mekanizması korunmuştur.
5. **Çok-kiracılı config hâlâ dosya tabanlı** (`ProjectRegistry`, `config_examples/`) — bir
   config-upload API'si yoktur; bu MVP sınırlamasıdır.
6. **Kimlik doğrulama yok** — API'de hiçbir auth/authorization mekanizması yoktur; herhangi bir
   çağıran, bildiği bir `project_id`/`subject_id` için event gönderebilir ve öneri okuyabilir.
