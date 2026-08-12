# AWE — Implementasyon Planı

Bu doküman, `AWE_MASTER_SPEC.md` içerisindeki gereksinimlerin mühendislik değerlendirmesini
ve sıfırdan geliştirme planını içerir. Spesifikasyondaki ürün ve mimari kırmızı çizgiler
(bölüm 3) değiştirilmemiştir. Aşağıdaki değerlendirme yalnızca algoritmik önerilere,
yani spesifikasyonun kendisinin de "kör şekilde uygulama, önce değerlendir" dediği
kısımlara yöneliktir.

## 1. Repository Durumu

Geliştirmeye başlarken repository'de yalnızca `AWE_MASTER_SPEC.md` bulunuyordu. Önceki bir
implementasyon, veritabanı veya kod tabanı yok. Proje git ile initialize edildi ve aşağıdaki
plan doğrultusunda sıfırdan kuruluyor.

## 2. Requirements I Would Change or Refine

Spesifikasyonun kendisi bazı algoritmik önerileri "değerlendir, gerekirse değiştir" şeklinde
açık bırakıyor (burst formülü, family matching stratejisi, recency modeli, support saturation).
Aşağıda bu açık noktalarda alınan kararlar ve spesifikasyondaki bir önerinin doğrudan
değiştirildiği durumlar listelenmiştir. Ürün/mimari kırmızı çizgilerine (bölüm 3) dokunulmamıştır.

### 2.1 Behavior Family eşleştirme: tam alignment/conformance yerine sınırlı model

**Requirement/Suggestion:** Bölüm 46-51, PM4Py'deki trace variant, Directly-Follows Graph,
alignment ve conformance checking fikirlerinin değerlendirilmesini, ardından "representative
variants + core/optional relationships + cohesion" temelli bir Family modeli kurulmasını istiyor.

**Problem:** "Alignment" kelimesi literatürde genellikle Petri net tabanlı optimal alignment
(edit-distance üzerinden en iyi model-log eşleşmesini bulma) anlamına gelir. Bu, loop ve
optional path içeren gerçek kullanıcı akışlarında NP-zor bir arama problemidir ve birden fazla
eşit-maliyetli alignment bulunduğunda hangi alignment'ın seçildiği implementasyon detayına
bağlı hale gelir. Bu da "deterministik" ve "explainable" kırmızı çizgileriyle çelişir: aynı
occurrence, kütüphane/versiyon değişiminde farklı şekilde açıklanabilir.

**Counterexample:** `B C C D` (retry) ile `B C D` iki kez tekrarlanmış bir occurrence
(`B C D B C D`) arasında tam conformance checking birden fazla eşit maliyetli eşleştirme
üretebilir (C'nin retry mi yoksa D'nin loop'u mu olduğu). Hangi yorumun seçildiği aynı günlük
üzerinde çalıştırma sırasına/kütüphane iç sıralamasına bağlı kalabilir.

**Proposed Refinement:** Family eşleştirmesi için sınırlı, deterministik bir model kullanılır:
- Karşılaştırma sembolü `(action_key, effect)` ikilisidir; `screen` ve `widget` sembolün parçası
  değil, ayrıştırıcı (discriminative) bağlam kanıtıdır (bkz. 2.3).
- Family, sınırlı sayıda (`max_representative_variants`, varsayılan 8) temsilci normalize
  dizi tutar (bölüm 47'deki variant compression).
- Family, ardışık sembol çiftleri (bigram, "directly-follows") üzerinden bir "core" ilişki
  tablosu tutar; bir çift, temsilci variant'ların en az `core_coverage_threshold` kadarında
  görülüyorsa core, daha azında görülüyorsa optional kabul edilir.
- Yeni bir occurrence, ayrıştırıcı-ağırlıklı LCS benzerliği (en iyi temsilci variant'a göre)
  ve core-bigram kapsama oranı üzerinden `MATCH / VARIANT_MATCH / AMBIGUOUS / NO_MATCH`
  olarak sınıflandırılır. Core-bigram kapsama kontrolü sıraya-duyarlı ama bitişikliğe duyarsız
  çalışır (predecessor, successor'dan önce geçiyor mu) — böylece opsiyonel ara adımlar core
  eşleşmesini bozmaz. Belirsiz aralıkta veya birden fazla family'ye yakın skorda ise
  `AMBIGUOUS` döner (bölüm 59).
- Core tablo, bir occurrence kabul edildikten sonra ailenin BİRİKMİŞ tüm temsilci
  variant'ları üzerinden yeniden hesaplanır (yalnızca en son eklenen üyeye göre değil). Bu,
  bölüm 58'deki "chaining" saldırısını önler: bir çift sembolün "core" sayılması ailenin tüm
  üyeleri arasındaki çoğunluk kapsamına bağlıdır, bu yüzden art arda yalnızca bir önceki üyeye
  benzeyen occurrence'lar zamanla ailenin gerçek çekirdeğini karşılayamaz hale gelir (bkz.
  `docs/architecture.md` içindeki sayısal örnek). Periyodik bakım adımı (bölüm 60) ayrıca
  cohesion trendini izleyerek split/merge adaylarını raporlar; bu, çekirdek güncellemesinin
  kendisinden bağımsız, tamamlayıcı bir sağlık kontrolüdür.

**Invariant Preserved:** MATCH/VARIANT_MATCH/AMBIGUOUS/NO_MATCH sonuçlarının tamamı korunur;
aynı prefix/aynı ending tek başına merge sebebi olmaz (core, tüm ilişkiler üzerinden
tanımlanır); widget rename Family'yi bölmez (widget sembolün parçası değildir); TargetRef ve
parameter value sembolün parçası değildir; sonuç tamamen deterministiktir (aynı veri her
çalıştırmada aynı sonucu üretir) ve her adım (hangi bigram core, hangi variant en yakın, hangi
skor) loglanabilir/açıklanabilir.

**Decision:** MODIFY.

### 2.2 Burst formülü: topDayShare tek başına değil, gün/session sayısı hard gate ile birlikte

**Requirement/Suggestion:** Bölüm 65, klasik `1 - uniqueDays/support` formülünü reddediyor ve
`topDayShare` gibi bir kanıt öneriyor, ancak "bunu da eleştirel değerlendir" diyor.

**Problem:** `topDayShare` tek başına yeterli bir gate değildir. İki günlük yoğun kullanım
sonrası tamamen sessizlik (bölüm 109, "two-day burst") senaryosunda `topDayShare` görece düşük
olabilir (aktivite iki güne dağılmıştır), ama bu davranış hâlâ gerçek bir Habit değildir.
`topDayShare`'i tek gate yaparsak two-day burst'ü yanlışlıkla PASS edebiliriz.

**Counterexample:** Gün 1: 15 occurrence, gün 2: 15 occurrence, sonraki 28 gün: 0. `topDayShare
= 0.5`, yüksek bir eşik kullanılmadıkça bu değer "burst değil" gibi görünebilir; oysa
`distinctDays=2` ve davranış hiç tekrar etmiyor.

**Proposed Refinement:** Burst reddi, `minDistinctDays` (varsayılan 3) ve `minDistinctSessions`
(varsayılan 2) hard evidence gate'leri ile yapılır — bu gate'ler doğrudan gün/session
sayımına dayanır, herhangi bir oran formülüne değil, bu yüzden "günde 5-10 kullanım" gibi
yoğun ama gerçek Habit'leri (bölüm 103) yanlışlıkla cezalandırmaz. `topDayShare` ve
`topSessionShare` hard gate olarak kullanılmaz; yalnızca gate'i geçen Family'ler için
açıklanabilirlik ve Habit gücü (soft skor) amacıyla evidence olarak taşınır.

**Invariant Preserved:** One-day burst (`distinctDays=1`) ve two-day burst (`distinctDays=2`)
`minDistinctDays=3` gate'i ile reddedilir; high-frequency daily (`distinctDays=20`) ve
short_frequent (`distinctDays≈30`) etkilenmez; single-session repeater ayrıca
`minDistinctSessions` gate'i ile reddedilir. Regularity hâlâ hard gate değildir (bölüm 66).

**Decision:** MODIFY.

### 2.3 Family sembol modeli: screen/widget sembolün değil, bağlamın parçası

**Requirement/Suggestion:** Bölüm 48, `actionKey`, `effect`, `screen`, `widget`, `target.type`
alanlarının "kontrollü" biçimde karşılaştırma token'ına dahil edilebileceğini söylüyor, kesin
bir birleştirme şekli vermiyor.

**Problem:** Spesifikasyon burada bilinçli olarak açık bırakılmış ("Bundan daha sağlam bir
token modelin varsa gerekçesiyle kullan"); bu nedenle bu bir "reject" değil, açık bırakılan bir
tasarım kararının somutlaştırılmasıdır.

**Counterexample:** Widget rename testinde (bölüm 50) `widget` sembolün parçası olsaydı,
`security_button → security_card` geçişi otomatik olarak yeni bir Family'ye yol açardı; bu
doğrudan bölüm 24'ü ("widget ana Behavior identity değildir") ihlal eder.

**Proposed Refinement:** Karşılaştırma sembolü `(action_key, effect)`. `screen`, ayrıştırıcı
ağırlıklandırmaya tabi bağlamsal kanıttır (bölüm 49 ve 50'deki "same action different screen"
senaryosunu, sembolün bir parçası olmadan, bağlam benzerliği skoru üzerinden destekler).
`widget`, yardımcı/opsiyonel ayrıştırma kanıtıdır; ne core sembolün ne de core-bigram kimliğinin
parçasıdır. `target.type` gerektiğinde yapısal kanıt olarak taşınır, `target.ref` ve parametre
değerleri hiçbir zaman kimlik hesabına girmez.

**Invariant Preserved:** Bölüm 22-24 (widget ana identity değil), bölüm 50 (same action
different screen ayrımı, aynı screen farklı widget'ın otomatik split yaratmaması), bölüm 56-57
(target ile ilgili invariant'lar).

**Decision:** MODIFY (spesifikasyonun bilinçli olarak açık bıraktığı noktayı somutlaştırma).

### 2.4 Recency/liveness: cadence-relative model

**Requirement/Suggestion:** Bölüm 67, "monthly Habit'i daily Habit gibi stale yapma" diyor ve
"observed cadence'i dikkate alabilecek daha sağlam bir yaklaşım varsa değerlendir" şeklinde
açıkça bir öneri istiyor.

**Problem:** Sabit bir "N gün kullanılmadıysa STALE" kuralı, farklı doğal periyotlardaki
Habit'ler için aynı anlama gelmez. Aylık bir Habit için 20 gün sessizlik normalken, günlük bir
Habit için aynı süre gerçek bir terk edilmeyi gösterir.

**Counterexample:** Sabit eşik 14 gün olsun. Aylık kira ödemesi hatırlatma Habit'i (ayda bir,
6 ay boyunca gözlenmiş) her ay 14. günden sonra STALE'e düşer ve suggestion kaybolur, sonraki
ay tekrar organik olarak kullanılana kadar gereksiz yere pending'e geri döner.

**Proposed Refinement:** `expectedGap`, Family'nin kendi gözlenmiş medyan gün-arası boşluğundan
(`medianGapDays`) hesaplanır (yetersiz örneklemde toplam aktif aralığın occurrence sayısına
bölümü kullanılır). `stalenessRatio = daysSinceLastOccurrence / expectedGap`. Liveness,
sabit gün sayısı yerine bu orana göre `LIVE / WATCH / STALE` olarak sınıflandırılır (varsayılan
eşikler: ≤2× → LIVE, ≤4× → WATCH, üzeri → STALE). Bu eşikler config'de tutulur.

**Invariant Preserved:** Historical strength ile current liveness ayrı tutulur (bölüm 67);
weekly/monthly/irregular Habit'ler günlük Habit'lerle aynı mutlak eşikle cezalandırılmaz.

**Decision:** MODIFY (spesifikasyonun davet ettiği somutlaştırma).

### 2.5 Support saturation formülü

**Requirement/Suggestion:** Bölüm 64, support'un sınırsız büyüyüp diğer kanıtları ezmemesi için
"bounded/saturating model değerlendir" diyor, formül vermiyor.

**Problem/Not:** Bu bir hata değil, doldurulması istenen açık bir noktadır.

**Proposed Refinement:** `supportScore = organicOccurrences / (organicOccurrences +
saturationK)`, `saturationK` config'de (varsayılan 5). 5 occurrence'da 0.5'e, 20'de 0.8'e
ulaşır ve 1.0'a asimptotik yaklaşır. Bu skor yalnızca Habit gücünün (soft, açıklanabilir bir
alt bileşen) hesaplanmasında kullanılır; hiçbir hard gate bu skora dayanmaz.

**Invariant Preserved:** Support hiçbir zaman tek başına gate belirlemez; minOccurrences hâlâ
ayrı, açık bir hard gate'tir.

**Decision:** MODIFY (açık noktanın somutlaştırılması).

### 2.6 Ayrıştırıcı ağırlıklandırma: düşük örneklemde smoothing

**Requirement/Suggestion:** Bölüm 49, IDF-benzeri bir discriminative weighting öneriyor.

**Problem:** Ham IDF, bir subject'in çok az sayıda (örn. 2-3) O-Series'i olduğunda anlamsız
ağırlıklar üretir (bir token ya %0 ya %100 dokümanda görülür, ara değer yoktur).

**Counterexample:** Subject'in yalnızca 2 O-Series'i varsa ve her ikisi de `open_app` ile
başlıyorsa, ham IDF `open_app` için ağırlığı sıfıra iter; ama bu erken aşamada henüz bunun
gerçekten ayrıştırıcılığı düşük ortak bir adım mı yoksa tesadüf mü olduğu bilinemez.

**Proposed Refinement:** Ağırlıklandırma add-one smoothing ile hesaplanır
(`weight = -log((df + 1) / (N + 1))`, normalize edilmiş) ve subject'in toplam O-Series sayısı
bir `minSeriesForWeighting` (varsayılan 5) eşiğinin altındaysa uniform ağırlığa (tüm tokenlar
eşit) düşülür. Bu, `AMBIGUOUS`/`PENDING_EVIDENCE` yönünde güvenli bir davranıştır.

**Invariant Preserved:** Bölüm 25 (şüpheli durumlarda güvenli downgrade); yetersiz veri erken
yanlış ayrıştırıcılık kararına yol açmaz.

**Decision:** MODIFY (küçük ölçekli, açık noktanın somutlaştırılması).

## 3. Katmanlar ve Sorumluluk Sınırları

Spesifikasyondaki pipeline (bölüm 4-5) birebir korunur:

```
RAW EVENT → ADAPTER → OBSERVATION → ORDERING → O-SERIES → FAMILY → HABIT
→ PLANNER → RISK → BENEFIT → FINAL SELECTION → ELIGIBLE SUGGESTIONS
```

Her katman kendi paketinde (`src/awe/<layer>`) yaşar, yalnızca bir önceki katmanın çıktı
modelini girdi olarak alır. Katmanlar birbirinin hesaplamasını tekrar etmez (bölüm 91).

Domain modelleri (`src/awe/domain`) tüm katmanlarca paylaşılan, uygulamadan bağımsız
dataclass/Pydantic modelleridir: `Observation`, `BehaviorToken`, `Occurrence`, `OSeries`,
`BehaviorFamily`, `FamilyVariant`, `HabitEvidence`, `ShortcutAnchor`, `PlanCandidate`,
`FieldBinding`, `RiskDecision`, `BenefitEvidence`, `Suggestion`. Bu modül hiçbir application-
specific isim (order, course, lesson, product vb.) içermez; bu otomatik bir testle
(`tests/scenarios/test_domain_universality.py`) korunur.

`ShortcutAnchor`, bölüm 71 gereği bir index değil, bir yapısal kimliktir: family core
sırasındaki bir sembol referansı (`(action_key, effect)` + core'daki konumu) olarak temsil
edilir ve her occurrence'ta kendi normalize dizisi içinde symbol eşleştirmesiyle çözülür.

## 4. Teknoloji ve Proje Yapısı

Bölüm 7-8'deki öneriler aynen kullanılıyor: Python 3.12+ (geliştirme ortamında 3.13 mevcut),
FastAPI, Pydantic v2, SQLAlchemy 2.x, Alembic, SQLite (geliştirme) + PostgreSQL-uyumlu şema,
pytest/pytest-cov/Hypothesis, ruff, mypy. Ek olarak yalnızca `python-dateutil` (timezone/gap
hesapları) ve `httpx` (test client) gibi küçük, gerekçeli bağımlılıklar eklenebilir.

Bu geliştirme ortamında yerel PostgreSQL/Docker mevcut değildir; test ve geliştirme SQLite
üzerinden yürütülür. Şema yalnızca portable SQLAlchemy tipleri (`String`, `Integer`, `Float`,
`Boolean`, `DateTime(timezone=True)`, `JSON`) kullanacak şekilde tasarlanır; Postgres'e özgü
tipler (ör. `ARRAY`, `JSONB`) kullanılmaz. Bu, gerçek bir kısıt olarak `docs/architecture.md`
içinde açıkça belirtilir.

Klasör yapısı bölüm 8'deki öneriyle birebir aynıdır (`src/awe/<layer>`, `tests/{unit,
scenarios,integration,property,regression}`, `scripts/`, `docs/`).

## 5. Test Stratejisi

- **unit**: her katmanın saf fonksiyonları (token üretimi, similarity skorları, saturation
  formülü, timezone/gün sınırı hesapları) izole test edilir.
- **scenarios**: bölüm 100-121'deki tüm kullanıcı/family/prefill/risk/benefit profilleri,
  gerçekçi (ama sentetik) event log fixture'ları üzerinden business-expectation odaklı test
  edilir (implementasyonu tekrar etmez, yalnızca dışarıdan beklenen sonucu doğrular).
- **integration**: API üzerinden event ingestion → analysis → suggestion tam döngüsü,
  idempotency, proje/subject izolasyonu.
- **property**: Hypothesis ile bölüm 123'teki 10 invariant.
- **regression**: adversarial review sırasında bulunan her gerçek bug için ayrı test.
- **evaluation**: `scripts/generate_synthetic_logs.py` + `scripts/evaluate_engine.py` ile
  100+ subject / 10.000+ event üzerinde precision/recall/F1 ve motor sağlık metrikleri
  (bölüm 126-129).

## 6. Faz Planı

Bölüm 141'deki faz sırası aynen izlenir (Faz 1 bu doküman ve repo temeliyle tamamlanır):

Faz 2 proje temeli → Faz 3 Adapter/Observation → Faz 4 Ordering/O-Series → Faz 5 Behavior
Family → Faz 6 Habit → Faz 7 Planner → Faz 8 Risk → Faz 9 Benefit → Faz 10 Selection/Lifecycle
→ Faz 11 API/Persistence → Faz 12 Evaluation → Faz 13 Adversarial Review → Faz 14
Dokümantasyon + final repository-quality review.

Her fazın sonunda ilgili test grubu çalıştırılır; bir sonraki faza yeşil testler olmadan
geçilmez.

## 7. Konfigürasyon Yaklaşımı

Bölüm 98'deki eşikler `src/awe/config` altında tek bir `EngineConfig` (Pydantic) modelinde
toplanır, proje bazında override edilebilir (`ProjectConfig`, timezone dahil). Varsayılan
değerler bu planda gerekçelendirilmiştir; `scripts/evaluate_engine.py` ile kalibre edilip
`docs/evaluation.md` içinde raporlanır. Yalnızca gerçekten kullanılan config alanları tutulur.

## 8. Çok-kiracılı (multi-project) config kapsamı

Spesifikasyon (bölüm 97) proje bazlı bir config-upload API'si tanımlamıyor. MVP kapsamında her
`projectId` için adapter mapping ve threshold override'ları, dosya tabanlı bir `ProjectRegistry`
üzerinden (`config_examples/` altında örnek konfigürasyonlarla) yüklenir. Gerçek bir çok-kiracılı
sistemde bu bir config-upload/yönetim API'sine dönüşür; bu MVP sınırlaması `docs/architecture.md`
içinde açıkça belirtilir ve genişletme noktası olarak işaretlenir.
