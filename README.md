# Adaptive Workflow Engine

AWE, bir mobil uygulamadan gelen event log'larını kullanarak her kullanıcının farklı
session'larda ve zaman içinde tekrar ettiği gerçek davranışları bulan, gerçek bir alışkanlık
olup olmadığını değerlendiren ve uygun olanlar için güvenli navigasyon/ön-doldurma kısayolları
öneren bir backend motorudur.

Motor kullanıcı adına hiçbir nihai veya geri alınamaz işlem yapmaz. Yalnızca iki tür öneri
üretir: **NAVIGATE** (kullanıcıyı doğrudan ilgili ekrana götürme) ve **PREFILL** (bir formu
kullanıcının tipik olarak girdiği tek bir değerle önceden doldurma, son onay her zaman
kullanıcıda kalır). **EXECUTE** modu yoktur.

## Motor ne yapmaz

* Kullanıcı adına satın alma, ödeme onayı, silme gibi nihai işlemler gerçekleştirmez.
* LLM, embedding veya başka bir black-box modele dayanmaz; tüm kararlar açıklanabilir, kural ve
  istatistik tabanlı kanıtlarla verilir.
* Bir müşterinin ham telemetry formatını veya iş alanlarını (ör. "sipariş", "ders") core motor
  kodunda hiçbir zaman bilmez — bu bilgi yalnızca proje bazlı Adapter konfigürasyonunda yaşar.

## Mimari

Sistem tek bir doğrusal pipeline üzerinden çalışır:

```
raw event → Adapter → Classifier → O-Series Builder → Episode Candidate Builder
→ Exact Base Family → Target Resolver → Habit Evaluator → Screen Transition Evidence
→ Anchor Resolver → Scope Projector → Destination Resolver → Shortcut Intent Builder
→ (Risk ‖ Benefit) → Selector → Suggestion (lifecycle)
```

Her katman kendi paketinde yaşar (`src/awe/<layer>`) ve yalnızca bir önceki katmanın çıktısını
girdi alır. Motor, artımlı state tutmaz — her analiz çağrısı subject'in tüm event geçmişini
sıfırdan yeniden işler (bkz. `docs/architecture.md` bölüm 2). Detaylı anlatım için
[`docs/architecture.md`](docs/architecture.md)'ye, tasarım kararlarının gerekçeleri için
[`docs/engine-decisions.md`](docs/engine-decisions.md)'ye bakın.

## Kurulum

Python 3.12+ gerekir.

**Windows (PowerShell):**

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

**Linux/macOS:**

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

`.env.example` dosyasını `.env` olarak kopyalayın; varsayılan ayarlar geliştirme için
(dosya tabanlı SQLite) hazırdır:

```bash
cp .env.example .env
```

Veritabanı şemasını oluşturun:

```bash
alembic upgrade head
```

## Çalıştırma

```bash
uvicorn awe.api.main:app --reload
```

API `http://127.0.0.1:8000/docs` altında etkileşimli dokümantasyonla birlikte ayağa kalkar.
Uç noktalar:

`project_id`/`subject_id`/`suggestion_key` her yerde query parametresidir (path'te değil):

```
POST /events?project_id=X                                      tek event
POST /events/batch?project_id=X                                 event batch
POST /analyze?project_id=X&subject_id=Y                          subject analizi çalıştır
POST /pull?project_id=X&subject_id=Y                             dış sunucudan çek + besle + analiz et
GET  /suggestions?project_id=X&subject_id=Y                       aktif önerileri listele
GET  /patterns?project_id=X&subject_id=Y                          her variant için tespit edilen davranışı listele
POST /dismiss?project_id=X&subject_id=Y&suggestion_key=Z
GET  /explanation?project_id=X&subject_id=Y&suggestion_key=Z
POST /push?project_id=X&subject_id=Y                              bekleyen önerileri dış sunucuya gönder
GET  /health
```

`project_id`, `config_examples/` altındaki bir YAML dosyasına karşılık gelmelidir (ör.
`shopwave`, `learnloop`, `taskflow`). Yeni bir müşteri entegrasyonu, yeni bir Python modülü değil
yeni bir YAML dosyasıdır — mevcut dosyalar hem farklı ham telemetry biçimlerine (bkz.
`shopwave.yaml` vs `learnloop.yaml` vs `taskflow.yaml`) hem farklı iş sözlüklerine örnek
oluşturur.

API'de şu anda hiçbir kimlik doğrulama/yetkilendirme mekanizması yoktur — bilinen bir MVP
açığıdır, bkz. `docs/architecture.md` bölüm 6.

### Veritabanı migration'ları

```bash
alembic upgrade head                              # şemayı güncel sürüme getir
alembic revision --autogenerate -m "açıklama"      # model değişikliğinden yeni migration üret
alembic downgrade -1                               # bir önceki sürüme geri dön
```

## Testler

```bash
pytest                  # tüm test paketi (unit, scenario, integration, property, regression)
ruff check .
mypy src
```

Test paketinin kapsamı ve büyük ölçekli sentetik değerlendirme sonuçları için
[`docs/evaluation.md`](docs/evaluation.md)'ye bakın.

### Sentetik değerlendirmeyi çalıştırma

```bash
python scripts/generate_synthetic_logs.py --output events.jsonl --subjects-per-profile 5
python scripts/evaluate_engine.py --subjects-per-profile 6 --multi-habit-subjects 10
```

İkinci komut, 17 farklı davranış profili için sentetik kullanıcılar üretir, bunları gerçek
ingestion → analiz pipeline'ından geçirir, Habit kararlarını ground truth ile karşılaştırıp
precision/recall/F1 hesaplar ve motor sağlık metriklerini raporlar.

## Proje yapısı

```
src/awe/
  domain/          katmanlar arası paylaşılan, uygulamadan bağımsız veri modelleri
  adapter/         ham event -> canonical Observation dönüşümü + ACTION/CONTEXT/IGNORE sınıflandırması
  ordering/        session içi deterministik sıralama
  series/          O-Series Builder (structural chunking, ambiguity barrier)
  episodes/        Episode Candidate Builder (full-chunk + pairwise-maximal ortak koşu çıkarımı)
  families/        Exact Base Family (deterministik, exact-equality gruplama)
  targeting/        Target Resolver (target fingerprint'e göre variant bölme)
  habit/           Habit kanıtı ve karar
  screen_evidence/ Screen Transition Evidence (post-action ekran tutarlılığı)
  planner/         Anchor Resolver, Scope Projector, Destination Resolver, Shortcut Intent Builder
  risk/            açıklanabilir Risk vektörü + ALLOW/BLOCK kapısı
  benefit/         deterministik saved-actions hesabı
  selection/       Selector (eligibility, weak-anchor istisnası, exact-intent dedupe, sıralama)
  lifecycle/       suggestion durum geçişleri (dismiss/cooldown/revive)
  persistence/     SQLAlchemy modelleri, repository, serialization
  services/        katmanları bağlayan orkestrasyon (ingestion, analiz, suggestion sorgulama)
  api/             FastAPI uç noktaları
  config/          merkezi eşik konfigürasyonu, proje registry, logging
  testing/         sentetik veri üreticileri (test ve evaluation script'leri için)

tests/
  unit/          izole katman testleri
  scenarios/     iş beklentisi odaklı senaryo testleri (habit profilleri, uçtan uca worked example)
  integration/   gerçek veritabanı + gerçek HTTP istekleriyle uçtan uca testler
  property/      Hypothesis ile invariant testleri
  regression/    adversarial edge case'lerin kalıcı kanıtı

scripts/         sentetik log üretici ve büyük ölçekli değerlendirme
config_examples/ proje bazlı Adapter mapping + eşik override örnekleri
docs/            mimari, tasarım kararları, test/değerlendirme raporu
docs/legacy/     önceki tasarımın spesifikasyon ve karar belgeleri (artık geçerli değil, yalnızca tarihsel referans)
```

## Tasarım notları

`docs/engine-decisions.md`, kod okunduğunda hemen belli olmayan kararların — spesifikasyonun
açıkça bırakmadığı boşlukların nasıl doldurulduğu, önceki tasarımdan hangi noktalarda ve neden
bilinçli olarak ayrıldığı dahil — kısa gerekçelerini toplar. `docs/legacy/` altındaki belgeler
önceki mimarinin (fuzzy family matching, çok alanlı PREFILL binding'leri, artımlı state) kayıtlı
tarihidir; mevcut motor onların yerini almıştır ve bu belgeler artık uygulanmaz.
