# Adaptive Workflow Engine

AWE, bir mobil uygulamadan gelen event log'larını kullanarak her kullanıcının farklı
session'larda ve zaman içinde tekrar ettiği gerçek davranışları bulan, bu tekrarları bir
davranış ailesi altında toplayan, gerçek bir alışkanlık olup olmadığını değerlendiren ve uygun
olanlar için güvenli navigasyon/ön-doldurma kısayolları öneren bir backend motorudur.

Motor kullanıcı adına hiçbir nihai veya geri alınamaz işlem yapmaz. Yalnızca iki tür öneri
üretir: **NAVIGATE** (kullanıcıyı doğrudan ilgili ekrana götürme) ve **PREFILL** (bir formu
kullanıcının tipik olarak girdiği değerlerle önceden doldurma, son onay her zaman kullanıcıda
kalır).

## Motor ne yapmaz

* Kullanıcı adına satın alma, ödeme onayı, silme gibi nihai işlemler gerçekleştirmez.
* LLM, embedding veya başka bir black-box modele dayanmaz; tüm kararlar açıklanabilir, kural ve
  istatistik tabanlı kanıtlarla verilir.
* Bir müşterinin ham telemetry formatını veya iş alanlarını (ör. "sipariş", "ders") core motor
  kodunda hiçbir zaman bilmez — bu bilgi yalnızca proje bazlı Adapter konfigürasyonunda yaşar.

## Mimari

Sistem tek bir doğrusal pipeline üzerinden çalışır:

```
raw event → Adapter → Observation → Ordering → O-Series → Behavior Family
→ Habit → Shortcut Planner → Risk → Benefit → Final Selection → Suggestion
```

Her katman kendi paketinde yaşar (`src/awe/<layer>`) ve yalnızca bir önceki katmanın çıktısını
girdi alır. Detaylı anlatım ve gerçekçi bir çoklu-session örneği için
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
Minimum uç noktalar:

```
POST /projects/{project_id}/events                                    tek event
POST /projects/{project_id}/events/batch                               event batch
POST /projects/{project_id}/subjects/{subject_id}/analyze              subject analizi çalıştır
GET  /projects/{project_id}/subjects/{subject_id}/suggestions          aktif önerileri listele
POST /projects/{project_id}/subjects/{subject_id}/suggestions/{key}/dismiss
GET  /health
```

`{project_id}`, `config_examples/` altındaki bir YAML dosyasına karşılık gelmelidir (ör.
`shopwave`, `learnloop`, `taskflow`). Yeni bir müşteri entegrasyonu, yeni bir Python modülü değil
yeni bir YAML dosyasıdır — mevcut dosyalar hem farklı ham telemetry biçimlerine (bkz.
`shopwave.yaml` vs `learnloop.yaml` vs `taskflow.yaml`) hem farklı iş sözlüklerine örnek
oluşturur.

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

İkinci komut, 20 farklı davranış profili için sentetik kullanıcılar üretir, bunları gerçek
ingestion → analiz pipeline'ından geçirir, Habit kararlarını ground truth ile karşılaştırıp
precision/recall/F1 hesaplar ve motor sağlık metriklerini (family fragmentation, ambiguous
series oranı, prefill downgrade oranı, vb.) raporlar.

## Proje yapısı

```
src/awe/
  domain/        katmanlar arası paylaşılan, uygulamadan bağımsız veri modelleri
  adapter/       ham event -> canonical Observation dönüşümü (deklaratif mapping)
  ordering/      session içi deterministik sıralama
  series/        O-Series extraction, retry/detour normalizasyonu
  families/      Behavior Family eşleştirme, discriminative weighting
  habit/         Habit kanıtı ve karar
  planner/       NAVIGATE/PREFILL aday üretimi, state reconstruction
  risk/          güvenlik değerlendirmesi
  benefit/       kullanıcı işi tasarrufu değerlendirmesi
  selection/     dominance, dedupe, fallback zinciri
  lifecycle/     suggestion durum geçişleri
  persistence/   SQLAlchemy modelleri, repository, serialization
  services/      katmanları bağlayan orkestrasyon (ingestion, analiz, suggestion sorgulama)
  api/           FastAPI uç noktaları
  config/        merkezi eşik konfigürasyonu, proje registry, logging
  testing/       sentetik veri üreticileri (test ve evaluation script'leri için)

tests/
  unit/          izole katman testleri
  scenarios/     iş beklentisi odaklı senaryo testleri (habit profilleri, risk/benefit matrisleri)
  integration/   gerçek veritabanı + gerçek HTTP istekleriyle uçtan uca testler
  property/      Hypothesis ile invariant testleri
  regression/    bulunan gerçek hataların kalıcı kanıtı

scripts/         sentetik log üretici ve büyük ölçekli değerlendirme
config_examples/ proje bazlı Adapter mapping + eşik override örnekleri
docs/            mimari, tasarım kararları, test/değerlendirme raporu
```

## Tasarım notları

`IMPLEMENTATION_PLAN.md`, spesifikasyondaki algoritmik önerilerin hangilerinin olduğu gibi
uygulandığını, hangilerinin somut bir tasarım kararına dönüştürüldüğünü ve gerekçesini
içerir. `docs/engine-decisions.md`, kod okunduğunda hemen belli olmayan kararların (ör. neden
`widget` davranış kimliğinin parçası değil, neden Risk kararı Benefit tarafından geçersiz
kılınamıyor) kısa gerekçelerini toplar.
