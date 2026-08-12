# ADAPTIVE WORKFLOW ENGINE (AWE)

# SIFIRDAN PROFESYONEL MVP TASARIMI, IMPLEMENTASYONU, TESTİ VE DOĞRULAMASI

Bu repository'nin tamamen boş olduğunu ve Adaptive Workflow Engine hakkında daha önce hiçbir bilgiye sahip olmadığını varsay.

Bu projeyi sıfırdan tasarlayıp implement etmeni istiyorum.

Yalnızca çalışan bir demo istemiyorum.

İstediğim sistem:

* profesyonel mühendislik standartlarında,
* modüler,
* test edilebilir,
* açıklanabilir,
* deterministik,
* farklı müşterilerin farklı mobil uygulamalarına ayrı ayrı entegre edilebilir,
* domain-independent,
* gerçek ve karmaşık event loglarında çalışabilecek,
* yanlış alışkanlıkları mümkün olduğunca engelleyen,
* gerçek alışkanlıkları aşırı muhafazakârlık nedeniyle gereksiz kaçırmayan,
* güvenli NAVIGATE ve PREFILL shortcut önerileri üreten,
* kullanıcı adına final/geri alınamaz işlem yapmayan

bir MVP olmalıdır.

Ama önemli bir nokta var:

Bu dokümandaki her algoritmik önerinin kesinlikle doğru olduğunu varsayma.

Bu doküman ürün sınırlarını, mimari prensipleri, problem alanını ve beklenen davranışları tanımlar.

Sen senior software/data engineer gibi düşün.

Bir algoritmik önerinin:

* matematiksel problemi varsa,
* gerçek event loglarında kırılacağını düşünüyorsan,
* bilgi kaybı yaratıyorsa,
* gereksiz karmaşıksa,
* başka bir katmanın sorumluluğuna giriyorsa,
* yanlış pozitif/yanlış negatif üretme riski yüksekse,
* daha sade ve sağlam bir alternatifi varsa

kör şekilde implement etme.

Önce teknik olarak değerlendir.

Daha iyi bir çözüm varsa:

1. problemi belirt,
2. counterexample ver,
3. alternatif çözümü açıkla,
4. korunan invariantları belirt,
5. testle doğrula,
6. sonra daha doğru çözümü uygula.

Ancak aşağıda açıkça belirtilen ürün/mimari kırmızı çizgilerini kendi başına değiştirme.

---

# 1. PROJEYİ DOĞRU ANLA

AWE aynı anda farklı mobil uygulamalardan gelen event loglarını bir araya getirip analiz eden bir sistem değildir.

Her AWE analizi:

```text
TEK MÜŞTERİ
+
TEK UYGULAMA
+
O UYGULAMADAKİ KULLANICILARIN EVENT LOGLARI
```

üzerinde çalışır.

Örneğin:

```text
Müşteri A

E-Commerce Application
        ↓
Adapter / Mapping A
        ↓
AWE Core
```

Başka bir müşteride:

```text
Müşteri B

Education Application
        ↓
Adapter / Mapping B
        ↓
AYNI AWE CORE
```

Başka bir müşteride:

```text
Müşteri C

Productivity Application
        ↓
Adapter / Mapping C
        ↓
AYNI AWE CORE
```

Evrensellik:

```text
farklı uygulamaların verisini aynı analizde karıştırmak
```

DEĞİLDİR.

Evrensellik:

> Aynı AWE Core algoritmasının Adapter/Mapping ve gerekli client entegrasyonu değiştirilerek farklı müşterilerin farklı mobil uygulamalarına ayrı ayrı entegre edilebilmesidir.

Core engine uygulamaya özel olmamalıdır.

Örneğin aşağıdakiler yasaktır:

```python
if screen == "orders":
    ...

if action_key == "lesson_complete":
    ...

if project_type == "banking":
    ...
```

Test fixture'larında e-commerce, education vb. business isimleri kullanılabilir.

Ama engine implementation içerisinde domain-specific logic bulunmamalıdır.

---

# 2. PROJENİN TEMEL AMACI

AWE, entegre edildiği uygulamadan gelen event loglarını kullanarak her kullanıcıyı bağımsız analiz eder.

Amaç:

> Kullanıcının farklı sessionlarda ve zaman içinde tekrar tekrar gerçekleştirdiği gerçek davranışları bulmak, bu tekrarları Behavior Family altında toplamak, bunların gerçek Habit olup olmadığını değerlendirmek ve uygun Habitlerden kullanıcıya zaman/iş kazandıran güvenli shortcut önerileri üretmektir.

Shortcut türleri:

```text
NAVIGATE ✅
PREFILL ✅
EXECUTE ❌
```

AWE kullanıcının adına final işlem gerçekleştirmez.

Örneğin:

```text
purchase
confirm payment
send
delete
final submit
irreversible update
```

gibi işlemleri otomatik gerçekleştirme.

PREFILL yalnız güvenli state hazırlığıdır.

Final confirmation gerektiğinde kullanıcıda kalmalıdır.

---

# 3. MİMARİ KIRMIZI ÇİZGİLER

Aşağıdakileri koru:

1. Tek analysis scope = `projectId + subjectId`.
2. Farklı project/application verilerini aynı Behavior Family içinde karıştırma.
3. Core engine domain-independent olmalı.
4. Adapter sınırı korunmalı.
5. `destination` diye bir mimari kavram oluşturma.
6. Ağır capability manifest sistemi oluşturma.
7. NAVIGATE vardır.
8. PREFILL vardır.
9. EXECUTE yoktur.
10. Habit, Risk ve Benefit bağımsız kavramlardır.
11. Habit/Risk/Benefit tek final weighted score altında bilgi kaybettirilmemelidir.
12. Risk BLOCK yüksek Benefit ile override edilemez.
13. Shortcut kullanımı organic Habit evidence olarak sayılmamalıdır.
14. Engine-level sabit maksimum suggestion sayısı koyma.
15. Behavior Family exact path equality'ye bağımlı olmamalıdır.
16. TargetRef çoğunlukla family identity olmamalıdır.
17. Parameter value çoğunlukla family identity olmamalıdır.
18. PREFILL geçmiş eventleri replay etmek değildir.
19. Arbitrary metadata'dan kendi kendine business semantics çıkarma.
20. Common startup screen için hardcoded özel isim kullanma.
21. `screen` ve `widget` bilgisini erken birleştirip bilgi kaybettirme.
22. `widget` ana Behavior identity değildir.
23. `source` eventin business anlamı değildir.
24. Unknown evidence'i pozitif evidence gibi kullanma.
25. Şüpheli durumlarda `AMBIGUOUS`, `PENDING_EVIDENCE` veya güvenli downgrade kullanabil.

---

# 4. ANA PIPELINE

Sistem şu pipeline üzerinden ilerlemelidir:

```text
RAW EVENT
   ↓
ADAPTER / MAPPING
   ↓
CANONICAL OBSERVATION
   ↓
ORDERING / SESSION HANDLING
   ↓
O-SERIES EXTRACTION
   ↓
BEHAVIOR FAMILY
   ↓
HABIT
   ↓
SHORTCUT PLANNER
   ↓
RISK
   ↓
BENEFIT
   ↓
FINAL SELECTION / DEDUPE
   ↓
ELIGIBLE SUGGESTIONS
```

Her katmanın input/output modeli açık olmalıdır.

Katmanların görevlerini birbirine karıştırma.

---

# 5. KATMAN SORUMLULUKLARI

## Adapter

Müşteriye özel event yapısını canonical Observation'a dönüştürür.

## Ordering

Session içindeki eventlerin mümkün olduğunca doğru ve deterministik sırasını sağlar.

## O-Series Extraction

Bir session içindeki eventlerden behavior occurrence/attempt dizilerini çıkarır.

Habit bulmaz.

## Behavior Family

Farklı sessionlardaki benzer behavior occurrence'larını aynı davranış ailesinde toplar.

Habit hesaplamaz.

Shortcut seçmez.

## Habit

Behavior Family gerçekten tekrar eden kalıcı behavior mı değerlendirir.

Planner işi yapmaz.

## Shortcut Planner

Habit'ten hangi NAVIGATE/PREFILL PlanCandidate'ların üretilebileceğini bulur.

Risk veya Benefit kararı vermez.

## Risk

Her PlanCandidate'ın güvenli olup olmadığını değerlendirir.

## Benefit

Her PlanCandidate'ın kullanıcıdan gerçekten ne kadar işi kaldırdığını değerlendirir.

## Final Selection

Önceki katmanların hesaplarını tekrarlamaz.

Uygun planlar arasında dedupe/dominance/primary plan seçimi yapar.

---

# 6. MVP'DE OLMAYACAK TEKNOLOJİLER

Şunları gereksiz yere ekleme:

* LLM
* embeddings
* deep learning
* generative AI
* reinforcement learning
* opaque black-box classifier
* Kafka zorunluluğu
* microservices
* Kubernetes requirement
* distributed event processing zorunluluğu
* graph database zorunluluğu
* Redis zorunluluğu
* domain-specific NLP
* business action isimlerinden semantic inference

MVP için gerekmedikçe ekleme.

---

# 7. TEKNOLOJİ YIĞINI

Tercih edilen backend:

```text
Python 3.12+
FastAPI
Pydantic
SQLAlchemy 2.x
Alembic
SQLite development
PostgreSQL-compatible design

pytest
pytest-cov
Hypothesis

ruff
mypy
```

Gerekli görürsen başka küçük ve iyi gerekçelendirilmiş dependency ekleyebilirsin.

Ancak dependency sayısını gereksiz artırma.

---

# 8. PROJEYİ SIFIRDAN KUR

Repository'nin boş olduğunu varsay.

En az:

```text
pyproject.toml
README.md
.env.example
.gitignore
alembic.ini
```

oluştur.

Önerilen yapı:

```text
src/
  awe/
    api/
    config/
    domain/
    adapter/
    ordering/
    series/
    families/
    habit/
    planner/
    risk/
    benefit/
    selection/
    lifecycle/
    persistence/
    services/

tests/
  unit/
  scenarios/
  integration/
  property/
  regression/

scripts/
  generate_synthetic_logs.py
  evaluate_engine.py
  diagnose_failures.py

docs/
```

Bu birebir zorunlu değildir.

Daha temiz bir yapı önerirsen kullanabilirsin.

Ama separation of concerns korunmalıdır.

---

# 9. KURULUM

README içerisinde sıfırdan kurulum anlat.

Windows:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

Linux/macOS:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

Şunlar çalışabilmelidir:

```bash
pytest
ruff check .
mypy src
```

FastAPI:

```bash
uvicorn awe.api.main:app --reload
```

benzeri açık bir komutla çalışabilmelidir.

Alembic migration komutlarını README içerisinde göster.

Clean checkout yapan geliştirici ek bilgi istemeden projeyi ayağa kaldırabilmelidir.

---

# 10. RAW EVENT MODELİ

Temel ham event sözleşmesi:

```json
{
  "eventId": "evt_9812",
  "projectId": "demo-app",
  "subjectId": "sub_a81f",
  "sessionId": "sess_104",

  "timestamp": "2026-08-05T10:35:22+03:00",

  "source": "client",

  "actionKey": "open_password",
  "role": "action",
  "effect": "route",
  "trigger": "button",

  "screen": "settings",
  "widget": "password_row",

  "target": null,

  "status": "success",
  "breaksEpisode": false,

  "deviceId": "device_01",
  "deviceOS": "android",
  "appVersion": "1.4.2",

  "durationMs": 640,

  "metadata": {}
}
```

Müşterinin gerçek telemetry formatı bundan farklı olabilir.

Adapter/Mapping bunu canonical modele dönüştürür.

AWE Core müşterinin özel telemetry formatını bilmemelidir.

---

# 11. eventId

Unique event identifier.

Duplicate event ingestion idempotent olmalıdır.

Aynı `eventId` ikinci kez geldiğinde:

```text
support
occurrence
family
habit evidence
suggestion
```

artmamalıdır.

---

# 12. projectId

Tek müşteri/application integration scope.

Analiz isolation:

```text
projectId + subjectId
```

üzerinden olmalıdır.

Farklı projectlerin eventleri hiçbir zaman aynı user behavior analysis içerisinde birleştirilmemelidir.

---

# 13. subjectId

Anonim kullanıcı kimliği.

AWE Habit discovery kullanıcı bazında çalışır.

---

# 14. sessionId

Session kimliği.

Güvenilir olarak mevcutsa session sınırının temel source'u olmalıdır.

Farklı session Observation'larını tek O-Series'e bağlama.

SessionId eksikliği desteklenecekse ayrı fallback mekanizması oluştur.

Ama:

```text
5 dakika inactivity = kesin yeni session
```

gibi universal olmayan kör varsayım kullanma.

Video izleme, okuma, form doldurma veya başka uzun activity olabilir.

---

# 15. timestamp

Timezone-aware olmalıdır.

Naive ve aware datetime karıştırma.

Storage UTC normalize edilebilir.

Habit day-boundary için project/application timezone configurable olmalıdır.

Tek timezone hardcode etme.

---

# 16. source

`source`, event'in hangi teknik tarafta oluştuğunu belirtir.

Örnek canonical değerler:

```text
client
server
system
unknown
```

`source`, event'in business semantic'i değildir.

Örneğin:

```text
source=client
```

client telemetry/user interaction tarafından oluşan event olabilir.

```text
source=server
```

backend outcome/validation sonucu olabilir.

```text
source=system
```

uygulama/system tarafından otomatik oluşan lifecycle veya teknik event olabilir.

Ana kullanıcı davranış evidence'ı çoğunlukla client kaynaklı olabilir.

Ancak:

```text
source=server
```

eventlerini otomatik silme.

Bunlar:

```text
outcome
completion
failure
validation
```

evidence olabilir.

Reliable correlation olmadığı sürece server eventini rastgele bir client behavior'a bağlama.

---

# 17. actionKey

Canonical behavior/action identifier.

Ana behavior identity'nin en önemli sinyallerinden biri olmalıdır.

Engine string adına bakıp business semantics tahmin etmemelidir.

---

# 18. role

Canonical event role.

Örnek:

```text
context
action
outcome
noise
```

Role frequency'den tahmin edilmemelidir.

Adapter/Mapping tarafından sağlanmalıdır.

---

# 19. effect

Action'ın yapısal etkisi.

Örnek canonical sınıflar:

```text
route
open_modal
select
input
prepare
update
submit
confirm
```

Bunlar başlangıç örnekleridir.

Daha sağlam controlled vocabulary öneriyorsan kullanabilirsin.

Ancak domain-specific olmamalıdır.

---

# 20. trigger

Örnek:

```text
button
swipe
notification
deeplink
shortcut
system
```

Özellikle:

```text
trigger=shortcut
```

organic Habit evidence olarak sayılmamalıdır.

---

# 21. screen

Event'in gerçekleştiği ekran/context.

Screen korunmalıdır.

Ama:

```python
if screen == "home":
```

gibi hardcode yasaktır.

Bir uygulamada sessionların %95'i aynı ekrandan başlayabilir.

Bu durumda ilgili screen davranışı ayırt etmede düşük discriminative evidence taşıyabilir.

Ama raw veriden çıkarılmamalıdır.

---

# 22. widget

`widget`, event'i oluşturan UI elemanının opsiyonel ve mümkünse stabil teknik kimliğidir.

Örneğin:

```text
screen=settings
widget=password_row
```

Widget müşteriden aşırı detaylı istenmemelidir.

Gerekmeyen şeyler:

```text
coordinates
color
font
widget tree
layout structure
```

Sade identifier yeterlidir.

Örneğin:

```text
search_field
password_row
item_card
primary_button
```

Widget optional olmalıdır.

Widget olmayan eventler sistem tarafından reddedilmemelidir.

---

# 23. SCREEN VE WIDGET AYRI KALMALI

Şunu yapma:

```text
screen + ":" + widget
```

şeklinde erken flattening.

`screen`:

> context

`widget`:

> context içerisindeki UI source

bilgisidir.

Canonical modelde ayrı tutulmalıdır.

---

# 24. WIDGET ANA BEHAVIOR IDENTITY DEĞİLDİR

UI redesign sonrası widget değişebilir.

Örnek:

```text
v1:
widget=security_button
```

```text
v2:
widget=security_card
```

Ama:

```text
actionKey=open_security
effect=route
screen=settings
```

aynı olabilir.

Bu durumda gerçek Habit gereksiz fragment olmamalıdır.

Widget:

```text
contextual / disambiguating evidence
```

olmalıdır.

---

# 25. target

Örnek:

```json
{
  "type": "contact",
  "ref": "opaque_91"
}
```

veya null.

Canonical model:

```text
PRESENT
NONE
UNKNOWN
```

semantik ayrımını kaybetmemelidir.

`UNKNOWN != NONE`.

TargetRef çoğu zaman Behavior Family identity'si değildir.

Target stability Planner/PREFILL aşamasında değerlendirilir.

---

# 26. status

Örnek:

```text
success
fail
cancel
partial
unknown
```

Status behavior evidence olarak korunmalıdır.

---

# 27. breaksEpisode

Explicit behavior boundary evidence.

Örneğin entegrasyon:

```text
logout
cancel_flow
switch_account
```

gibi eventleri:

```text
breaksEpisode=true
```

map edebilir.

Engine action stringinden bunu tahmin etmemelidir.

---

# 28. durationMs

Secondary timing evidence.

Benefit için kullanılabilir.

Ancak idle time nedeniyle kirlenebileceğini düşün.

Ana Benefit metriğini kör şekilde duration üzerine kurma.

---

# 29. metadata

Core Engine arbitrary metadata taramamalıdır.

Örneğin:

```text
metadata.buttonText
metadata.color
metadata.description
```

gibi alanlardan kendi kendine behavior semantics veya PREFILL parameter çıkarma.

Gerekliyse Adapter/Mapping açık whitelisting ile canonical parameter üretir.

---

# 30. CANONICAL OBSERVATION

Adapter yaklaşık şöyle bir model üretmelidir:

```python
Observation(
    event_id=...,
    project_id=...,
    subject_id=...,
    session_id=...,
    timestamp=...,
    source=...,
    action_key=...,
    role=...,
    effect=...,
    trigger=...,
    screen=...,
    widget=...,
    target=...,
    target_state=...,
    parameters=...,
    status=...,
    breaks_episode=...,
    app_version=...,
    mapping_version=...,
    quality=...,
)
```

Bu exact Python schema olmak zorunda değildir.

Daha iyi bir model tasarlayabilirsin.

Ama canonicalization sırasında önemli bilgileri kaybetme.

---

# 31. ADAPTER

Adapter'ın görevi:

```text
customer raw telemetry
        ↓
canonical Observation
```

dönüşümüdür.

Adapter:

* field mapping,
* aliases,
* action normalization,
* role mapping,
* effect mapping,
* screen normalization,
* widget normalization,
* target extraction,
* explicit parameter extraction,
* status normalization,
* source normalization,
* data-quality normalization

yapabilir.

Core Engine müşteriye özel field pathlerini bilmemelidir.

Mapping versioned olmalıdır.

---

# 32. ADAPTER PORTABILITY

En az 2-3 farklı synthetic customer raw telemetry formatı oluştur.

Örnek A:

```json
{
  "event": "clicked",
  "page": "settings",
  "element": "security",
  "entity": "123"
}
```

Örnek B:

```json
{
  "eventType": "tap",
  "screenName": "settings",
  "widgetId": "security_card",
  "objectId": "123"
}
```

Bunlar farklı Adapter/Mapping ile canonical Observation'a çevrilebilmeli.

AWE Core değişmemeli.

---

# 33. ORDERING

Observation'ları:

```text
projectId
subjectId
sessionId
```

bazında ayır.

Event ordering deterministik olmalıdır.

Güvenilir sequence number varsa kullanabilirsin.

Yoksa timestamp.

Aynı timestamp ve belirsiz sıra varsa sahte kesinlik üretme.

Örneğin:

```text
orderingConfidence=LOW
```

evidence taşı.

Technical deterministic ordering kullanılabilir fakat gerçek temporal order olarak kabul edilmemelidir.

---

# 34. SESSION

SessionId güvenilir olduğunda hard session boundary.

Farklı session O-Series içinde birleşmemelidir.

Habit tam tersine farklı sessionlar üzerinden değerlendirilmelidir.

---

# 35. O-SERIES EXTRACTION

O-Series:

> Tek session içerisindeki anlamlı bir behavior attempt/occurrence.

O-Series Extraction'ın görevi:

```text
session event stream
→ behavior attempts
```

çıkarmaktır.

Bu katman:

```text
Habit hesaplamaz
Family clustering yapmaz
Shortcut seçmez
Risk hesaplamaz
Benefit hesaplamaz
```

---

# 36. RAW + NORMALIZED REPRESENTATION

O-Series raw Observation sequence'ini koru.

Ek olarak Family comparison için normalized projection üretilebilir.

Örneğin raw:

```text
A
B
X
back
B
C
D
```

comparison projection:

```text
A
B
C
D
```

olabilir.

Ama normalization raw kanıtı yok etmemelidir.

---

# 37. NOISE

`role=noise` comparison'dan çıkabilir.

Raw occurrence'tan silinmemelidir.

---

# 38. CONTEXT

`screen_view` veya context eventini kör şekilde noise yapma.

Bazı flowlarda yapısal kanıt olabilir.

---

# 39. BREAKS EPISODE

```text
breaksEpisode=true
```

strong boundary evidence.

---

# 40. BACK

`back` otomatik O-Series sonu değildir.

Örnek:

```text
A
B
C
back
B
D
```

aynı behavior içerisindeki correction olabilir.

---

# 41. DETOUR / MISCLICK

Örnek:

```text
A
B
X
back
B
C
D
```

X local reversible detour olabilir.

Bunu otomatik olarak her durumda misclick sayma.

Evidence gerekir.

Detour normalization bounded olmalıdır.

---

# 42. RETRY

Örnek:

```text
A
B
C_FAIL
C_SUCCESS
D
```

Raw korunur.

Comparison projection:

```text
A B C D
```

olabilir.

Retry statistics ayrıca tutulur.

---

# 43. FAILURE / CANCEL / PARTIAL

Başarılı, failed, cancelled ve partial attempts korunmalıdır.

Full occurrence ile aynı evidence ağırlığında değerlendirmek zorunda değilsin.

Ama tamamen çöpe atma.

Risk ve intent evidence için kullanılabilir.

---

# 44. SOURCE TESTLERİ

## Client behavior + server outcome

```text
CLIENT open_form
CLIENT select
CLIENT submit
SERVER success
```

Expected:

* client user actions behavior evidence,
* server success outcome evidence,
* server success user action değildir.

## Uncorrelated server event

Reliable correlation yoksa server event rastgele O-Series'e bağlanmamalıdır.

## System event arada

```text
CLIENT A
SYSTEM lifecycle
CLIENT B
CLIENT C
```

SYSTEM event Family core'u gereksiz bölmemelidir.

## Server retry

```text
CLIENT submit
SERVER fail
SERVER retry
SERVER success
```

Server retry user work Benefit'ini artırmamalıdır.

---

# 45. BEHAVIOR FAMILY

Behavior Family farklı sessionlardan gelen O-Series'lerin aynı underlying behavior olup olmadığını belirler.

Burası sistemin en kritik algoritmik katmanlarından biridir.

Exact path matching yeterli değildir.

Gerçek kullanıcılar aynı davranışı farklı şekillerde yapabilir.

---

# 46. PM4PY REFERANSI

Şu projeyi incele:

```text
https://github.com/process-intelligence-solutions/pm4py
```

Özellikle:

```text
trace variants
Directly-Follows Graph
alignment
conformance
sequence
branch
loop
optional paths
```

fikirlerini değerlendir.

Ancak AWE'yi generic process mining platformuna dönüştürme.

PM4Py dependency zorunlu değildir.

Core modelleri PM4Py'ye bağlama.

Gerekirse yalnız offline reference/benchmark olarak kullan.

---

# 47. EXACT VARIANT COMPRESSION

Aynı sequence 30 kere geldiyse structural hesapta:

```text
Variant ABCD
support=30
```

gibi sıkıştırılabilir.

Ama occurrence-level:

```text
timestamp
session
target
parameters
status
source
```

evidence kaybolmamalıdır.

---

# 48. BEHAVIOR TOKEN

Comparison için canonical token tasarla.

Örneğin şu evidence'lardan kontrollü yararlanılabilir:

```text
actionKey
effect
role
screen
widget
target.type
```

Hepsinin ağırlığı aynı olmak zorunda değildir.

Genel beklenti:

```text
actionKey
```

ana davranış kimliği.

```text
effect + screen
```

güçlü structural/context evidence.

```text
widget
```

yardımcı disambiguation evidence.

```text
target.type
```

gerektiğinde structural evidence.

```text
target.ref
```

çoğunlukla Family identity dışı.

```text
parameter values
```

çoğunlukla Family identity dışı.

Bundan daha sağlam bir token modelin varsa gerekçesiyle kullan.

---

# 49. DISCRIMINATIVE WEIGHTING

Bir token kullanıcının neredeyse bütün behaviorlarında bulunuyorsa ayırt ediciliği düşüktür.

Örneğin bütün sessionlar:

```text
START → A → B → C
START → X → Y → Z
START → M → N → K
```

ise `START` ortak olduğu için Family'leri merge etmemelidir.

`START` stringini hardcode etme.

IDF-benzeri discriminative weighting değerlendirilebilir.

Aynı prensip:

```text
screen
generic action
generic widget
```

için uygulanabilir.

---

# 50. WIDGET TESTLERİ

## Same action different screen

```text
screen=A
widget=item
actionKey=select
```

ve:

```text
screen=B
widget=item
actionKey=select
```

Context farklıysa matching bunu kullanabilmeli.

## Same screen different widget

```text
screen=settings
widget=privacy_row
actionKey=open_section
```

vs:

```text
screen=settings
widget=security_row
actionKey=open_section
```

Widget yardımcı evidence olabilir.

Ama yalnız widget farklı diye otomatik farklı Family yapma.

## Widget rename

AppVersion 1:

```text
widget=security_button
```

AppVersion 2:

```text
widget=security_card
```

actionKey/effect/context stable ise gerçek Habit parçalanmamalı.

## Missing widget

`widget=null` kabul edilmeli.

## Generic widget

`primary_button` her yerde varsa düşük discriminative value almalı.

---

# 51. FAMILY STRUCTURAL MODEL

Family sadece tek exact sequence olmamalıdır.

En az:

```text
representativeVariants
variantSupport
coreRelationships
optionalRelationships
loop/retry evidence
cohesion
```

gibi yapı düşün.

İlk occurrence seed'e aşırı bağımlı olma.

---

# 52. FAMILY MATCH

En az:

```text
MATCH
VARIANT_MATCH
AMBIGUOUS
NO_MATCH
```

sonuçlarını destekle.

Her occurrence'ı zorla Family'ye sokma.

---

# 53. FAMILY ÖRNEĞİ

Uygun evidence varsa:

```text
S1 A B C D
S2 A B C D
S3 A B X C D
S4 B C D
S5 A B C C D
```

aynı Family olabilir.

Burada:

```text
A = optional prefix olabilir
X = optional/detour olabilir
CC = retry olabilir
```

Core yaklaşık:

```text
B → C → D
```

olabilir.

Ama örneği hardcode etme.

---

# 54. SAME PREFIX ≠ SAME FAMILY

```text
A B C D
A B E F
```

sadece `A B` ortak diye merge edilmemeli.

---

# 55. SAME ENDING ≠ SAME FAMILY

```text
A B C REVIEW
X Y Z REVIEW
```

aynı son state/action nedeniyle merge edilmemeli.

---

# 56. DIFFERENT TARGET SAME BEHAVIOR

```text
FLOW target=A
FLOW target=B
FLOW target=C
```

aynı Family olabilir.

TargetRef nedeniyle support parçalanmamalıdır.

---

# 57. SAME TARGET DIFFERENT BEHAVIOR

```text
BEHAVIOR1 target=A
BEHAVIOR2 target=A
```

aynı target diye merge edilmemeli.

---

# 58. CHAINING EFFECT

Şuna izin verme:

```text
A B C D
A B X C D
X C D
X Y D
X Y Z
```

Her yeni trace yalnız bir önceki üyeye benzediği için tek dev Family olmamalıdır.

Yeni occurrence:

```text
representatives
+
family structural core
```

ile uyum sağlamalıdır.

---

# 59. SHORT AMBIGUOUS FRAGMENT

Family1:

```text
A B C D
```

Family2:

```text
X B C Y
```

Yeni:

```text
B C
```

Expected:

```text
AMBIGUOUS
```

---

# 60. FAMILY COHESION

Family zamanla heterojenleşebilir.

Cohesion ölç.

Gerekirse batch maintenance sırasında:

```text
split candidate
merge candidate
```

üret.

Ama gereksiz ağır continuous reclustering yapma.

---

# 61. HABIT LAYER

Habit yalnız Behavior Family seviyesinde hesaplanır.

Soru:

> Bu Family zaman içerisinde gerçekten tekrar eden bir kullanıcı behavior'ı mı?

---

# 62. HABIT HARD EVIDENCE

Configurable:

```text
minOccurrences
minDistinctSessions
minDistinctDays
```

gibi başlangıç gates olabilir.

Default değerleri evaluation ile belirle.

Magic number kullanma.

---

# 63. HABIT EVIDENCE

En az:

```text
organicOccurrences
distinctSessions
distinctDays
firstSeenAt
lastSeenAt
activeSpan
topDayShare
topSessionShare
medianGapDays
regularity
recency/liveness
```

üret.

---

# 64. SUPPORT SATURATION

Support sonsuza kadar büyüyüp diğer evidence'i ezmemelidir.

Bounded/saturating model değerlendir.

---

# 65. BURST

Eski tarz:

```text
1 - uniqueDays/support
```

kullanma.

Çünkü:

```text
her gün 5 kez kullanım
```

gerçek Habit olmasına rağmen burst gibi görünebilir.

Tek gün concentration için:

```text
topDayShare
```

gibi evidence daha uygun olabilir.

Ama bunu da eleştirel değerlendir.

Daha iyi çözüm varsa kullan.

---

# 66. REGULARITY

Regularity hard gate değildir.

Weekly/monthly/irregular recurring behaviors kaçırılmamalıdır.

Unknown regularity'ye:

```text
1.0
```

verme.

---

# 67. RECENCY / LIVENESS

Historical Habit strength ile current liveness gerektiğinde ayrı tutulmalıdır.

Örneğin:

```text
historically strong
currently stale
```

olabilir.

Monthly Habit'i daily Habit gibi stale yapma.

Observed cadence'i dikkate alabilecek daha sağlam yaklaşım varsa değerlendir.

---

# 68. SHORTCUT CONTAMINATION

`trigger=shortcut` organic occurrence değildir.

Örneğin:

```text
organic Habit oluştu
shortcut çıktı
kullanıcı 20 kez shortcut kullandı
```

Expected:

```text
organicHabitSupport aynı
shortcutUtilityEvidence +20
```

olabilir.

---

# 69. SHORTCUT PLANNER

Sadece Habit gate'ini geçen Family Planner'a girer.

Planner:

> Hangi güvenli mantıksal NAVIGATE/PREFILL adayları çıkarılabilir?

sorusunu cevaplar.

---

# 70. DESTINATION YOK

Sistemde `destination` veya `destinationKey` oluşturma.

Gerçekte gözlenmiş canonical action/state üzerinden çalış.

Internal:

```text
ShortcutAnchor
```

kullanılabilir.

---

# 71. ANCHOR INDEX OLMAMALI

Yanlış:

```text
anchor = sequence[4]
```

Doğru yaklaşım structural identity.

Çünkü optional adımlar index değiştirir.

---

# 72. MULTIPLE PLANS

Bir Family:

```text
NAVIGATE early
NAVIGATE deeper
PREFILL partial
PREFILL deeper
```

gibi birden fazla candidate üretebilir.

Planner erkenden tek winner seçmemelidir.

---

# 73. PREFILL EVENT REPLAY DEĞİLDİR

Observed:

```text
open_form
select_recipient A
select_account X
enter_amount 500
review
```

Yanlış:

```text
eventleri otomatik simulate et
```

Doğru:

```text
form/state initial values:
recipient=A
account=X
```

User devam eder.

---

# 74. STATE RECONSTRUCTION

Her occurrence'ta anchor öncesi canonical state çıkar.

Family seviyesinde field distribution oluştur.

---

# 75. FIELD STATES

Her binding:

```text
STABLE
VARIABLE
UNKNOWN
```

olmalı.

`UNKNOWN != VARIABLE`.

---

# 76. DOMINANCE + COVERAGE

Sadece dominant share yeterli değildir.

Her field için:

```text
dominance
coverage
sampleSize
recentDominance
```

gibi evidence kullan.

Örneğin:

```text
A
A
UNKNOWN
UNKNOWN
```

known dominance 1.0 olabilir.

Ama coverage 0.5.

Full confidence değildir.

---

# 77. CONCEPT DRIFT

Historical:

```text
A A A A A A A A A A
```

Recent:

```text
B B B B B
```

Engine historical dominance nedeniyle A'yı kör PREFILL etmemeli.

Basit last-K/recent window ile historical distribution karşılaştırması düşünülebilir.

Daha sağlam sade bir yöntem varsa kullan.

---

# 78. CLIENT RESOLVER

Backend geçmiş logdan uygulamanın belirli state'e gerçekten doğrudan gidebileceğini bilemez.

Minimal Resolver contract oluştur.

Örneğin:

```text
supportsNavigate
supportsPrefill
acceptedBindings
requiresReview
supportsRuntimeValidation
```

Ama ağır capability architecture oluşturma.

---

# 79. RISK

Risk `PlanCandidate` seviyesindedir.

Aynı Habit için:

```text
NAVIGATE LOW
PREFILL MODERATE
```

olabilir.

---

# 80. HARD SAFETY GATE

MVP execute yapmaz.

Irreversible/final action planlarını BLOCK et.

Canonical effect/policy kullan.

Business action stringlerine özel kod yazma.

---

# 81. RISK EVIDENCE

En az:

```text
effect safety
anchor coverage
state confidence
target dominance
target coverage
binding dominance
binding coverage
sample size
recent drift
completion
failure
cancel
resolver support
review support
runtime validation
data quality
family ambiguity/cohesion
```

gibi evidence değerlendir.

---

# 82. RISK DECISION

Örneğin:

```text
ALLOW
ALLOW_WITH_REVIEW
REDUCE_BINDINGS
DOWNGRADE_TO_NAVIGATE
BLOCK
```

---

# 83. SAFE FALLBACK

```text
FULL PREFILL
   ↓
PARTIAL PREFILL
   ↓
NAVIGATE
   ↓
BLOCK
```

Mümkün olmalıdır.

Habit tümüyle kaybolmamalıdır.

---

# 84. BENEFIT

Benefit PlanCandidate seviyesindedir.

Soru:

> Shortcut kullanıcının gerçek manuel işinden ne kadarını kaldırıyor?

---

# 85. USER WORK

Ham event count kullanma.

Örnek:

```text
button            USER
screen_view       CONTEXT
loading           SYSTEM
redirect          SYSTEM
select            USER
```

5 event vardır ama 2 meaningful user action vardır.

---

# 86. BENEFIT EVIDENCE

Occurrence bazında:

```text
savedUserActions
```

hesapla.

Sonra:

```text
median
p25
p75
benefitCoverage
```

gibi robust stats.

---

# 87. MISCLICK/RETRY BENEFIT INFLATION

```text
A X back A B C
```

X/back normal shortcut Benefit'ini yükseltmemelidir.

```text
A B_FAIL B_FAIL B C
```

technical retry da Benefit'i yükseltmemelidir.

---

# 88. TIME BENEFIT

Duration varsa secondary evidence olarak kullanılabilir.

Idle time temizlenmeden ana Benefit metric'i yapma.

---

# 89. MINIMUM BENEFIT

Configurable minimum belirle.

Başlangıç örneği:

```text
medianSavedUserActions >= 2
```

olabilir.

Ancak değerlendirme sonucuna göre değiştir.

---

# 90. RISK VETO

```text
Risk BLOCK
+
Benefit HIGH
```

sonucu:

```text
BLOCK
```

olmalıdır.

Tek weighted final score bu kuralı bozamaz.

---

# 91. FINAL SELECTION

Buraya gelen candidate'lar önceki katmanlardan geçmiştir.

Final Selection:

```text
Habit tekrar hesaplamaz
Risk tekrar hesaplamaz
Benefit tekrar hesaplamaz
```

Görevleri:

```text
within-family dominance
primary plan
fallback chain
cross-family dedupe
subsumption
ranking preparation
```

---

# 92. SABİT SUGGESTION SAYISI YOK

Engine-level:

```text
maxSuggestions=3
```

koyma.

4 güçlü bağımsız Habit varsa 4'ü de eligible olabilir.

UI kaçını göstereceğine ayrıca karar verebilir.

---

# 93. ÇOK SUGGESTION HEALTH SIGNAL

Bir kullanıcıdan 25 suggestion çıkıyorsa hard cap ile kapatma.

Araştır:

```text
fragmentation?
weak dedupe?
weak Habit gate?
weak Benefit?
candidate explosion?
```

---

# 94. LIFECYCLE

Minimum:

```text
PENDING_EVIDENCE
ELIGIBLE
ACTIVE
STALE
DISMISSED
INVALIDATED
```

---

# 95. REASON CODES

Reject/downgrade/pending nedenleri açık olmalıdır.

Örnek:

```text
INSUFFICIENT_OCCURRENCES
INSUFFICIENT_DISTINCT_SESSIONS
INSUFFICIENT_DISTINCT_DAYS
ONE_DAY_BURST
STALE_BEHAVIOR
AMBIGUOUS_FAMILY
LOW_COHESION
UNSTABLE_TARGET
UNKNOWN_TARGET
LOW_BINDING_COVERAGE
RECENT_PARAMETER_DRIFT
RESOLVER_UNSUPPORTED
RUNTIME_VALIDATION_FAILED
REVIEW_REQUIRED
PREFILL_REDUCED
PREFILL_DOWNGRADED
EXECUTE_BLOCKED
BENEFIT_TOO_LOW
DUPLICATE_PLAN
DOMINATED_PLAN
```

---

# 96. PERSISTENCE

SQLite dev.

PostgreSQL-compatible schema.

Alembic.

En az şu kavramların persistence ihtiyacını düşün:

```text
events
observations / reproducible canonicalization
O-Series evidence
families
variants
habit analysis
plan candidates
suggestions
lifecycle
```

Gereksiz tablo çoğaltma.

---

# 97. API

Minimum:

```text
POST events
POST event batch
run/request subject analysis
GET subject suggestions
dismiss suggestion
```

Project scope API'de açık olmalıdır.

Domain logic route içine yazılmamalıdır.

---

# 98. CONFIG

Thresholdlar centralized configuration olmalıdır.

Örneğin:

```text
minOccurrences
minDistinctSessions
minDistinctDays
supportSaturation
family thresholds
core coverage
detour tolerance
recency parameters
minBindingEvidence
minBindingCoverage
minBenefitActions
minBenefitCoverage
dismissCooldown
```

Sadece gerçekten gerekli configleri tut.

---

# 99. TEST STRATEJİSİ

Zorunlu:

```text
unit
scenario
integration
property
regression
large synthetic evaluation
```

Sadece birkaç happy-path testle bitirme.

---

# 100. HABIT USER PROFILES

Aşağıdakilerin TAMAMINI test et:

```text
daily_regular
daily_missing_days
daily_high_frequency
weekly_regular
biweekly_regular
monthly_regular
irregular_recurring
short_frequent
long_workflow
one_day_burst
two_day_burst
single_session_repeater
stale_habit
revived_habit
multi_habit_user
```

---

# 101. DAILY REGULAR

30 gün her gün.

Expected:

```text
Habit PASS
```

---

# 102. DAILY MISSING DAYS

30 günün 20-22 gününde.

Expected:

```text
PASS
```

---

# 103. HIGH-FREQUENCY DAILY

20 gün boyunca günde 5-10 session.

Expected:

```text
PASS
```

Burst sanma.

---

# 104. WEEKLY

8 hafta yaklaşık haftada bir.

Expected:

```text
PASS
```

Daily density nedeniyle reject etme.

---

# 105. BIWEEKLY

8-10 occurrence yaklaşık 14 günlük aralıklarla.

Evidence yeterliyse Habit olabilmeli.

---

# 106. MONTHLY

6+ ay ayda yaklaşık bir.

Expected:

```text
Habit possible/PASS
```

---

# 107. IRREGULAR

Örneğin aktif günler:

```text
1,4,11,18,29,43,55
```

Regularity düşük olsa bile gerçek repeated Habit tamamen reddedilmemelidir.

---

# 108. ONE-DAY BURST

Tek gün 30-50 kez.

Expected:

```text
Habit FAIL/PENDING
```

---

# 109. TWO-DAY BURST

İki gün yoğun sonra yok.

Expected:

```text
Habit değil/pending
```

---

# 110. SINGLE SESSION REPEATER

Tek session 50 tekrar.

Expected:

```text
Habit değil
```

---

# 111. SHORT FREQUENT

```text
A → B
```

30 gün tekrar.

Expected:

```text
Habit güçlü olabilir
```

Ama Benefit düşükse suggestion yok.

---

# 112. STALE / REVIVED

Geçmişte güçlü ancak uzun süre yok:

```text
STALE
```

Sonra yeniden organic tekrar:

```text
liveness recover
```

---

# 113. MULTI-HABIT USER

Aynı user:

```text
A daily
B weekly
C monthly
D irregular
```

Dördü birbirine karışmadan bulunabilmelidir.

---

# 114. FAMILY TEST MATRIX

Mutlaka test et:

```text
exact repeat
optional prefix
optional suffix if meaningful
optional middle
retry
repeated action
bounded detour
misclick/back
real branch
loop
partial
failure
cancel
same prefix different behavior
same ending different behavior
same startup screen
generic screen/action/widget
different target same behavior
same target different behavior
short ambiguous fragment
chaining attack
first seed outlier
interleaved unrelated event
ordering ambiguity
```

---

# 115. COMMON STARTUP SCREEN

```text
START A B C
START X Y Z
START M N K
```

Expected:

```text
3 different behaviors
```

START common diye merge olmasın.

No hardcoded START/home string.

---

# 116. NOTIFICATION/DEEPLINK VARIANTS

Bazı sessions normal common screen'den başlarken bazıları:

```text
trigger=notification
```

veya:

```text
trigger=deeplink
```

ile daha ileriden başlayabilir.

Yeni `EntryContext` modeli oluşturma.

Mevcut:

```text
trigger
screen
sequence
```

evidence ile ele al.

---

# 117. PREFILL TEST MATRIX

Mutlaka:

```text
stable target
variable target
unknown target
stable parameter
variable parameter
unknown parameter
partial prefill
low coverage
small sample
recent preference drift
target stable + amount variable
runtime invalid target
```

---

# 118. RISK TEST MATRIX

Mutlaka:

```text
safe navigate
unsupported navigate
prefill stable + review
prefill no review
one unstable binding
all unstable bindings
prefill to navigate downgrade
runtime target failure
high technical failure
high cancellation
execute-like block
high Benefit + blocked Risk
```

---

# 119. BENEFIT TEST MATRIX

Mutlaka:

```text
5→1
2→1
many system events low user work
misclick inflation
retry inflation
optional route
branch
real prefill reduction
default field no false benefit
duration outlier
high benefit blocked risk
```

---

# 120. FINAL SELECTION TEST MATRIX

Mutlaka:

```text
same family multiple navigate
navigate dominance
prefill dominance
navigate vs slightly better prefill
navigate vs significantly better prefill
cross-family duplicate
subsumed partial/full plan
0 suggestions
1 suggestion
4 independent suggestions
many candidates without artificial cap
```

---

# 121. DOMAIN PORTABILITY TEST

Aynı Core Engine'i ayrı ayrı test et:

```text
Project A: e-commerce-like
Project B: education-like
Project C: productivity-like
Project D: social-like
Project E: finance-like
Project F: health-like
Project G: travel-like
Project H: media-like
```

Her project ayrı dataset.

Eventleri aynı analysis'e karıştırma.

Adapter/Mapping değişebilir.

Resolver değişebilir.

AWE Core değişmemelidir.

---

# 122. DATA QUALITY TESTLERİ

Mutlaka:

```text
duplicate event
late event
out-of-order
same timestamp
invalid timestamp
missing screen
missing widget
missing target
unknown target
unknown role
unknown effect
server event without correlation
bad session
mapping version change
app version change
partial batch
```

---

# 123. PROPERTY-BASED INVARIANTS

Hypothesis ile en az:

1. Noise eklemek Family identity'yi kökten değiştirmemeli.
2. Duplicate batch support artırmamalı.
3. Input batch order değişimi deterministic sonucu bozmamalı.
4. Shortcut-trigger organic support artırmamalı.
5. Risk BLOCK Benefit tarafından açılamamalı.
6. 4 eligible Habit 3'e kesilmemeli.
7. TargetRef değişimi structural behavior aynıysa otomatik Family split yaratmamalı.
8. Common startup token eklemek farklı behaviorları merge etmemeli.
9. Widget rename semantic action sabitse Family'yi otomatik split etmemeli.
10. Server retry Benefit user action count artırmamalı.

---

# 124. REGRESSION

Her gerçek bug:

```text
tests/regression/
```

altında tekrar üretilebilen test oluşturmalıdır.

Bug fix testsiz kabul edilmemelidir.

---

# 125. SYNTHETIC GENERATOR

Deterministic synthetic generator oluştur.

En az:

```text
daily_regular
daily_missing_days
daily_high_frequency
weekly_regular
biweekly_regular
monthly_regular
irregular_recurring
short_frequent
long_workflow
one_day_burst
two_day_burst
single_session
stale
revived
multi_habit
target_stable
target_variable
parameter_stable
parameter_variable
parameter_drift
noisy
misclick_heavy
retry_heavy
branching
ambiguous
fragmented
common_start_screen
notification_variant
widget_rename
server_outcome
shortcut_active
```

profillerini destekle.

Ground truth olsun.

---

# 126. LARGE DATASET

Minimum:

```text
100+ subjects
10,000+ events
```

ile deterministic evaluation.

Mümkünse daha büyük ikinci run.

Raporla:

```text
events
subjects
series
families
variants
ambiguous series
habit candidates
accepted habits
plan candidates
risk blocked
benefit rejected
eligible suggestions
runtime
```

---

# 127. EVALUATION

Sadece pytest pass yeterli değil.

Ground truth ile:

```text
TP
FP
FN
TN
precision
recall
F1
```

gerektiği yerde hesapla.

Ancak tek global score altında hataları saklama.

Ayrı ölç:

```text
false Family merge
Family fragmentation
Habit false positive
Habit false negative
unsafe PREFILL
low-benefit suggestion
duplicate suggestion
ambiguous rate
prefill downgrade rate
```

---

# 128. FAILURE BUCKETS

Kaçırılan vakaları:

```text
O_SERIES_FRAGMENTATION
FAMILY_FRAGMENTATION
FAMILY_AMBIGUOUS
INSUFFICIENT_EVIDENCE
HABIT_GATE
STALE
PLANNER_NO_PLAN
RISK_BLOCK
BENEFIT_LOW
RESOLVER_UNSUPPORTED
DEDUPE
```

gibi stage-level bucketlara ayır.

FP'leri de nedenleriyle raporla.

---

# 129. MOTOR HEALTH

Raporla:

```text
seriesPerSubject
familiesPerSubject
variantsPerFamily
familyCohesion
ambiguousSeriesRate
fragmentationRate
eligibleHabitsPerSubject
plansPerHabit
prefillDowngradeRate
eligibleSuggestionsPerSubject
duplicateSuppressionRate
```

Bir userda anormal suggestion sayısı varsa nedenini incele.

---

# 130. THRESHOLD TUNING

Bir test fail ettiğinde doğrudan threshold değiştirme.

Önce:

```text
implementation bug?
modeling issue?
data problem?
ground-truth issue?
threshold calibration?
```

belirle.

Threshold değiştirirsen bütün scenario suite'i tekrar çalıştır.

Bir şeyi düzeltirken başka profilde Recall/Precision bozuluyor mu ölç.

---

# 131. EXPLAINABILITY

Her suggestion için cevaplanabilmeli:

```text
Hangi Family?
Hangi variants?
Kaç organic occurrence?
Kaç session?
Kaç gün?
Family neden match?
Cohesion ne?
Habit neden PASS?
Planner hangi candidates üretti?
Target/parameter stability ne?
Risk neden allow/block/downgrade?
Benefit kaç user action?
Hangi plan dominated?
Final neden bu?
```

---

# 132. STRUCTURED LOGGING

Örnek:

```text
analysis_started
series_extracted
series_ambiguous
family_created
family_matched
habit_passed
habit_pending
plan_generated
binding_reduced
plan_downgraded
risk_blocked
benefit_rejected
plan_deduped
suggestion_eligible
```

Sensitive değerleri loglama.

---

# 133. DOKÜMANTASYON

Üret:

```text
README.md
IMPLEMENTATION_PLAN.md
ARCHITECTURE.md
ENGINE_DECISIONS.md
TEST_REPORT.md
EVALUATION_REPORT.md
```

---

# 134. IMPLEMENTATION_PLAN'DE ELEŞTİREL İNCELEME

`IMPLEMENTATION_PLAN.md` içerisinde:

```text
Requirements I Would Change or Refine
```

başlığı olsun.

Bu prompttaki algoritmik önerileri teknik olarak değerlendir.

Gerçek problem görüyorsan:

```text
Requirement/Suggestion:
Problem:
Counterexample:
Proposed Refinement:
Invariant Preserved:
Decision: KEEP / MODIFY / REJECT
```

formatını kullan.

Her şeyi değiştirmeye çalışma.

Sadece gerçekten gerekliyse.

Ürün kırmızı çizgilerini değiştirme.

---

# 135. ARCHITECTURE.MD

Multi-session gerçekçi örnek üzerinden bütün pipeline'ı anlat.

Tek session örneğiyle yetinme.

---

# 136. ENGINE_DECISIONS.MD

Özellikle açıkla:

```text
neden tek application scope
neden Adapter
neden source tutuluyor
neden widget ayrı
neden widget Behavior identity değil
neden destination yok
neden capability manifest yok
neden exact path yok
neden discriminative weighting
neden targetRef family identity değil
neden regularity hard gate değil
neden old burst formula yok
neden PREFILL replay değil
neden Risk veto
neden no suggestion hard cap
neden shortcut organic evidence değil
```

---

# 137. TEST_REPORT.MD

Her kategori için:

```text
test count
scenario type
expected
actual
pass/fail
```

---

# 138. EVALUATION_REPORT.MD

Dürüstçe:

```text
successes
false positives
false negatives
wrong merges
fragmentation
unsafe candidates
low-benefit candidates
ambiguous unresolved
domain portability
large dataset metrics
```

raporla.

Mükemmel değilse mükemmelmiş gibi gösterme.

---

# 139. ADVERSARIAL REVIEW

İlk implementasyon tamamlandıktan sonra kendi kodunu bağımsız senior engineer gibi kırmaya çalış.

Yeni counterexample'lar üret.

Özellikle:

```text
common startup
generic widgets
widget rename
same action different context
same context different action
same ending
same prefix
target changes
parameter drift
daily high-frequency
weekly
monthly
irregular
bursts
loops
backtracking
misclick
retries
noise
server events
event ordering ambiguity
missing data
first seed outlier
chaining
shortcut feedback loop
cross-family duplicate
```

Bulduğun her gerçek bug için regression test ekle.

---

# 140. DONE KRİTERLERİ

Projeyi tamamlanmış kabul etmeden doğrula:

1. Clean install.
2. README installation.
3. FastAPI startup.
4. Alembic migrations.
5. SQLite works.
6. PostgreSQL-compatible.
7. Raw event validation.
8. `source` preserved.
9. `widget` preserved.
10. Screen/widget information loss yok.
11. Adapter mapping works.
12. Project isolation.
13. Subject isolation.
14. Duplicate idempotency.
15. Ordering deterministic.
16. O-Series boundaries tested.
17. Back handling tested.
18. Retry handling tested.
19. Detour handling tested.
20. Exact Family repeat.
21. Optional Family variant.
22. Branch handling.
23. Same prefix separation.
24. Same ending separation.
25. Common startup safe.
26. Widget rename safe.
27. Generic widget safe.
28. TargetRef unnecessary fragmentation yok.
29. Short ambiguity supported.
30. Chaining resisted.
31. Seed outlier resisted.
32. Daily Habit detected.
33. High-frequency daily detected.
34. Weekly detected.
35. Biweekly handled.
36. Monthly detected.
37. Irregular recurring handled.
38. One-day burst rejected/pending.
39. Two-day burst rejected/pending.
40. Single-session repeat not Habit.
41. Short frequent Habit possible.
42. Stale handled.
43. Revival handled.
44. Multi-Habit user handled.
45. Shortcut contamination prevented.
46. Multiple planner candidates.
47. NAVIGATE supported.
48. PREFILL supported.
49. EXECUTE forbidden.
50. Stable target.
51. Variable target.
52. Unknown target.
53. Stable parameter.
54. Variable parameter.
55. Unknown parameter.
56. Partial PREFILL.
57. Drift handling.
58. Resolver contract.
59. Risk hard blocks.
60. Risk downgrade.
61. Runtime validation.
62. Benefit user work based.
63. Retry not inflating Benefit.
64. Misclick not inflating Benefit.
65. System/server events not inflating Benefit.
66. Risk veto works.
67. Plan dominance.
68. Cross-family dedupe.
69. No hard suggestion cap.
70. Four independent suggestions remain eligible.
71. Lifecycle.
72. Dismiss cooldown.
73. Invalidated plan.
74. Reason codes.
75. Structured logs.
76. Unit tests.
77. Scenario tests.
78. Integration tests.
79. Property tests.
80. Regression tests.
81. Synthetic evaluation.
82. 100+ users / 10k+ events.
83. Failure bucket report.
84. Family fragmentation report.
85. False merge report.
86. Habit precision/recall.
87. Unsafe PREFILL count.
88. Domain portability.
89. At least several different Adapter examples.
90. Same AWE Core runs without domain-specific modification.

---

# 141. ÇALIŞMA SIRASI

Şimdi şu sırayla ilerle:

### Phase 1 — Engineering Design

* Repository'yi incele.
* Boşsa sıfırdan initialize et.
* `IMPLEMENTATION_PLAN.md` yaz.
* Domain models belirle.
* Layer interfaces belirle.
* Riskli noktaları ve alternatif algoritmaları değerlendir.
* Prompttaki teknik önerileri eleştirel incele.

### Phase 2 — Project Foundation

* pyproject
* config
* logging
* database
* Alembic
* domain models
* FastAPI skeleton
* test infrastructure

### Phase 3 — Adapter / Observation

* Raw event schemas
* Mapping
* Canonical Observation
* source
* widget
* target states
* parameters
* quality

### Phase 4 — Ordering / O-Series

* sorting
* session boundaries
* boundary logic
* retries
* detours
* partial/failure/cancel
* normalization projection

### Phase 5 — Behavior Family

* variant compression
* discriminative weighting
* candidate retrieval
* structural/alignment matching
* ambiguity
* chaining protection
* cohesion
* tests

### Phase 6 — Habit

* temporal evidence
* support
* days/sessions
* burst
* regularity
* recency/liveness
* organic vs shortcut usage
* tests

### Phase 7 — Planner

* structural anchors
* NAVIGATE candidates
* state reconstruction
* PREFILL candidates
* STABLE/VARIABLE/UNKNOWN
* target/parameter evidence
* drift
* tests

### Phase 8 — Risk

* resolver
* hard safety
* uncertainty
* review
* runtime validation
* binding reduction
* downgrade
* tests

### Phase 9 — Benefit

* user work
* normalized effort
* saved actions
* coverage
* robust statistics
* tests

### Phase 10 — Selection / Lifecycle

* dominance
* primary/fallback
* dedupe
* lifecycle
* reason codes

### Phase 11 — API / Persistence Integration

* endpoints
* repositories
* transactions
* idempotency

### Phase 12 — Evaluation

* synthetic users
* multi-Habit data
* domain portability
* data-quality stress
* large dataset
* metrics
* failure buckets

### Phase 13 — Adversarial Review

* sistemi kır
* yeni counterexample üret
* regression tests ekle
* kök nedenleri düzelt
* tüm evaluation'ı yeniden çalıştır

### Phase 14 — Documentation / Final Review

* README
* ARCHITECTURE
* ENGINE_DECISIONS
* TEST_REPORT
* EVALUATION_REPORT

---

# 142. SON PRENSİP

Bu promptu mekanik olarak kodlama.

Ama ürün hedefini de kendi kafana göre değiştirme.

Senden beklenen:

> Verilen tasarım sınırları içerisinde mümkün olan en sağlam ve sade mühendislik çözümünü bulmak.

Bir yerde bu dokümanın önerdiği algoritma hatalıysa bunu söyle ve daha iyisini kanıtlayarak uygula.

Bir yerde bu doküman gereğinden fazla karmaşıksa sadeleştir.

Bir yerde eksik bir edge case varsa ekle.

Ama sırf daha sofistike görünsün diye sistemi büyütme.

Ana öncelik sırası:

```text
CORRECTNESS
↓
SAFETY
↓
EXPLAINABILITY
↓
GENERALIZABILITY
↓
SIMPLICITY
↓
PERFORMANCE
```

Performans problemi gerçekten kanıtlanmadan doğruluğu feda etme.

Bir test geçirmek için domain-specific workaround yazma.

Bir threshold değişikliğiyle bir problemi çözerken başka kullanıcı profillerini bozma.

Yanlış PREFILL yerine NAVIGATE daha iyidir.

Evidence yetersizse PENDING_EVIDENCE daha iyidir.

Ambiguous behavior'ı yanlış Family'ye sokmaktansa AMBIGUOUS bırakmak daha iyidir.

Ancak aşırı muhafazakârlık nedeniyle weekly, monthly veya irregular gerçek Habitleri sürekli kaçırmadığını evaluation ile kanıtla.

Şimdi projeyi sıfırdan başlat.

Önce `IMPLEMENTATION_PLAN.md` oluştur ve bu promptu senior engineer gözüyle eleştirel değerlendir.

Ardından açık bir blocker olmadığı sürece implementasyona devam et.

Her fazın sonunda ilgili testleri çalıştır.

İlk implementasyon bittiğinde sistemi tamamlanmış sayma.

Adversarial evaluation yap, gerçek hataları regression testleriyle düzelt ve ancak final full-suite + evaluation sonuçlarından sonra projeyi tamamlanmış kabul et.




# KOD, DOKÜMANTASYON VE REPOSITORY SUNUM STANDARDI

Bu proje daha sonra public veya private bir GitHub repository'sinde gerçek bir mühendislik projesi olarak tutulacaktır.

Kod tabanının, dokümantasyonun veya commit'e girecek dosyaların herhangi bir yapay zeka aracının otomatik olarak oluşturduğu izlenimini vermemesine dikkat et.

Bu gereksinim kod kalitesini gizlemek veya yapay biçimde insan hataları eklemek anlamına gelmez.

Amaç:

> Temiz, doğal, tutarlı ve deneyimli bir yazılım mühendisi tarafından geliştirilmiş gibi okunabilen profesyonel bir repository oluşturmaktır.

## Dil

Kullanıcıya ve geliştiriciye yönelik bütün açıklamalar Türkçe olmalıdır.

Özellikle:

* README.md
* ARCHITECTURE.md
* IMPLEMENTATION_PLAN.md
* ENGINE_DECISIONS.md
* TEST_REPORT.md
* EVALUATION_REPORT.md
* kod içerisindeki gerekli açıklayıcı yorumlar
* docstring'ler
* hata açıklamaları ve reason-code dokümantasyonu

Türkçe yazılmalıdır.

Ancak teknik identifier'ları Türkçeleştirmeye çalışma.

Kod içerisinde aşağıdaki gibi İngilizce teknik isimlendirme kullan:

```python
BehaviorFamily
Observation
PlanCandidate
HabitEvidence
RiskDecision
BenefitEvidence

extract_series()
match_family()
evaluate_habit()
build_plan_candidates()
evaluate_risk()
evaluate_benefit()
```

Yani:

```text
Kod ve identifier'lar → İngilizce
Dokümantasyon ve açıklamalar → Türkçe
```

prensibini kullan.

---

# YAPAY ZEKA ARAÇLARINA REFERANS VERME

Repository içerisinde gereksiz şekilde:

```text
Generated by Claude
AI-generated
Claude suggested
ChatGPT
LLM generated
As an AI
automatically generated by AI
```

gibi ifadeler kullanma.

Kod yorumlarında, README'de veya dokümantasyonda geliştirme aracına referans verme.

Teknik kararları:

```text
Claude böyle önerdi
```

şeklinde değil:

```text
Bu yaklaşımın seçilme nedeni...
```

şeklinde mühendislik gerekçesiyle açıkla.

---

# DOĞAL REPOSITORY YAPISI

Repository'yi gereksiz miktarda belge ve klasörle doldurma.

Her dosyanın gerçek bir amacı olsun.

Örneğin:

```text
README.md
docs/architecture.md
docs/engine-decisions.md
docs/testing.md
```

gibi daha doğal bir yapı, aynı bilgiyi tekrar eden onlarca markdown dosyasından daha iyiyse bunu tercih edebilirsin.

Bu specification'da istenen dokümantasyon içerikleri korunmalıdır fakat gerekirse daha doğal bir dosya organizasyonu altında birleştirilebilir.

Örneğin:

```text
TEST_REPORT.md
EVALUATION_REPORT.md
```

ayrı dosyalar yerine gerçekten daha temizse:

```text
docs/evaluation.md
```

içerisinde iki ayrı bölüm olarak tutulabilir.

Bunu yaparsan hiçbir gerekli bilgiyi kaybetme.

---

# GEREKSİZ YORUM YAZMA

Kodun her satırını açıklayan yorumlar yazma.

Kötü örnek:

```python
# Kullanıcının kimliğini alıyoruz.
subject_id = event.subject_id

# Liste oluşturuyoruz.
families = []

# Döngüye giriyoruz.
for family in families:
    ...
```

Bu tür yorumlar kodu profesyonel değil, otomatik üretilmiş gösterir.

Yorum yalnızca:

* algoritmanın nedenini,
* beklenmeyen bir edge case'i,
* önemli bir invariant'ı,
* matematiksel bir tercihi,
* güvenlik kararını,
* kolay anlaşılmayan davranışı

açıklamak gerektiğinde kullanılmalıdır.

Örneğin:

```python
# Shortcut üzerinden oluşan occurrence'lar organic support'a dahil edilmez.
# Aksi halde öneri kendi Habit kanıtını yapay olarak büyütür.
```

gibi yorum anlamlıdır.

---

# DOCSTRING STANDARDI

Her trivial fonksiyona uzun docstring yazma.

Özellikle şu tarz yapay dokümantasyon üretme:

```python
def get_user(...):
    """
    Gets a user.

    Args:
        ...
    Returns:
        ...
    """
```

Eğer fonksiyon adı ve type hint zaten yeterince açıksa docstring gerekmeyebilir.

Docstring:

* domain kuralı,
* algoritmik varsayım,
* önemli side effect,
* normal olmayan input/output davranışı

varsa kullanılmalıdır.

---

# İSİMLENDİRME

Değişken ve fonksiyon isimleri kısa ama anlamsız olmamalıdır.

Kaçın:

```python
data1
temp2
result_final_new
process_data
do_stuff
helper
utils2
manager_new
```

Tercih et:

```python
organic_occurrences
family_match
binding_coverage
normalized_trace
candidate_plan
```

`utils.py` gibi her şeyin atıldığı büyük dosyalar oluşturma.

Domain sorumluluğuna göre modüllere ayır.

---

# AŞIRI ABSTRACTION YAPMA

Bir fonksiyon için interface + abstract base class + factory + manager + service oluşturma.

Gerçek ihtiyaç olmadıkça:

```text
Factory
Builder
Manager
Provider
Handler
Processor
Strategy
Facade
```

gibi katmanları çoğaltma.

MVP için sade Python tasarımını tercih et.

Örneğin bir family matcher gerçekten değiştirilebilir algoritmalara ihtiyaç duyuyorsa interface mantıklı olabilir.

Ama sırf “clean architecture” görünsün diye abstraction üretme.

---

# AŞIRI KÜÇÜK FONKSİYONLAR ÜRETME

Sadece 1-2 satırlık anlamsız wrapper fonksiyonlarla kodu parçalama.

Fonksiyon sınırları domain sorumluluğunu temsil etsin.

Kod:

> kolay test edilebilir ve okunabilir

olmalı.

Ama:

> yüzlerce anlamsız küçük wrapper

içermemeli.

---

# DEVASA FONKSİYONLAR DA YAZMA

Tam tersi şekilde 300-500 satırlık engine fonksiyonları oluşturma.

Özellikle:

```text
O-Series
Behavior Family
Habit
Planner
Risk
Benefit
```

algoritmaları kendi sorumluluklarına göre bölünmelidir.

---

# README DOĞAL OLMALI

README akademik tez veya pazarlama metni gibi yazılmamalıdır.

Başlangıçta kısa şekilde:

```text
AWE nedir?
Ne problemi çözüyor?
Nasıl çalışıyor?
Nasıl kurulur?
Nasıl test edilir?
```

cevaplanmalıdır.

Örneğin yapı:

```text
# Adaptive Workflow Engine

Kısa açıklama

## Mimari

## Kurulum

## Çalıştırma

## Testler

## Proje Yapısı

## Tasarım Notları
```

gibi sade olabilir.

README içerisinde her sınıfın veya fonksiyonun uzun açıklamasını verme.

Derin teknik açıklamaları `docs/` altında tut.

---

# PAZARLAMA DİLİ KULLANMA

Şu tür ifadelerden kaçın:

```text
revolutionary
cutting-edge
powerful AI-powered system
highly sophisticated
state-of-the-art
seamlessly
robust and scalable solution
```

Somut teknik ifadeler kullan.

Örneğin:

```text
Motor, farklı sessionlarda tekrar eden canonical davranış dizilerini
Behavior Family altında toplar ve zaman dağılımını Habit katmanında değerlendirir.
```

---

# GEREKSİZ EMOJI VE GÖRSEL SÜSLEME YOK

Repository dokümanlarında gereksiz:

```text
🚀
✨
🔥
✅
🎯
```

kullanma.

Normal teknik dokümantasyon biçiminde yaz.

---

# TEST İSİMLERİ PROFESYONEL OLMALI

Kötü:

```python
test_it_works()
test_test()
test_correct_result()
```

İyi:

```python
test_daily_high_frequency_behavior_is_not_classified_as_burst()
test_same_terminal_action_does_not_force_family_merge()
test_shortcut_trigger_does_not_increase_organic_support()
```

Test isimleri İngilizce kalabilir.

Test içerisinde açıklama gerekiyorsa Türkçe yorum kullanılabilir.

---

# SENTETİK VERİLER GERÇEKÇİ OLMALI

Fixture'ları:

```text
foo
bar
test1
test2
```

ile doldurma.

Test edilen davranışı anlamayı kolaylaştıran gerçekçi fakat tamamen sentetik örnekler kullan.

Domain portability testlerinde farklı uygulama hikâyeleri kullanılabilir.

Ama production algoritma bu isimlere bağımlı olmamalıdır.

---

# COMMIT'E GİRMEMESİ GEREKEN DOSYALAR

`.gitignore` içerisinde en az:

```text
.venv/
__pycache__/
.pytest_cache/
.mypy_cache/
.ruff_cache/
.coverage
htmlcov/
.env
*.db
*.sqlite
*.sqlite3
dist/
build/
*.egg-info/
```

gibi local/generated artefact'ları uygun şekilde dışarıda bırak.

Test için özellikle gereken fixture/database varsa bunu bilinçli şekilde ayrı değerlendir.

---

# DEBUG VE GEÇİCİ DOSYALARI TEMİZLE

Final review sırasında:

```text
debug.py
temp.py
test2.py
try_new.py
old_version.py
backup.py
final_final.py
```

gibi geçici dosyaları repository'de bırakma.

Aynı şekilde:

```text
print(...)
```

debug ifadelerini production code içerisinde bırakma.

Structured logging kullan.

---

# TODO TEMİZLİĞİ

Gereksiz:

```text
TODO
FIXME
HACK
TEMP
```

yorumlarını final repository'de bırakma.

Gerçekten çözülmemiş ve bilinçli olarak ertelenmiş bir konu varsa açık teknik gerekçeyle dokümante et.

---

# ÖLÜ KOD

Final review sırasında:

* kullanılmayan imports,
* kullanılmayan fonksiyonlar,
* unreachable branchler,
* eski algoritma implementasyonları,
* comment-out edilmiş büyük kod blokları

temizlenmelidir.

Git geçmişi eski kodu saklamak için yeterlidir.

---

# TESTLER IMPLEMENTASYONU KOPYALAMAMALI

Testler mevcut kodu tekrar ederek aynı algoritmayı ikinci kez yazıp sonucu karşılaştırmamalıdır.

Testler:

> dışarıdan beklenen davranışı

doğrulamalıdır.

Özellikle ground-truth scenario testleri business expectation üzerinden kurulmalıdır.

---

# TASARIM KARARLARI DOĞAL BİÇİMDE BELGELENMELİ

Örneğin kötü:

```text
Requirement #57 gereği target ref family identity değildir.
```

Daha doğal:

```text
Target referansı family kimliğine dahil edilmez. Aynı davranış farklı
hedeflerle gerçekleştirilebildiği için target ref üzerinden ayrım yapmak
support'un gereksiz parçalanmasına neden olur.
```

Yani final dokümantasyon bu specification'ın maddelerini kopyalayan bir checklist gibi görünmemelidir.

Specification implementation rehberidir.

Final dokümantasyon gerçek projenin dokümantasyonu olmalıdır.

---

# SPECIFICATION DOSYASI VE GITHUB

`AWE_MASTER_SPEC.md` geliştirme sürecinde internal engineering specification olarak kullanılmaktadır.

Final repository hazırlanırken bunun GitHub'da tutulmasının gerçekten gerekli olup olmadığını değerlendir.

Eğer proje dokümantasyonu:

```text
README
architecture
engine decisions
testing/evaluation
```

dosyalarında yeterince temsil ediliyorsa development-only specification dosyasını production/public repository yapısının parçası yapmak zorunda değilsin.

Ancak hiçbir önemli mimari karar kaybolmamalıdır.

Ben özellikle istersem specification dosyasını koru.

Kendi başına önemli gereksinimleri silme.

---

# FINAL REPOSITORY REVIEW

Implementasyon ve bütün testler bittikten sonra ayrıca bir repository-quality review yap.

Şunları kontrol et:

1. Kod isimlendirmeleri doğal mı?
2. AI aracına referans var mı?
3. Gereksiz yorum var mı?
4. Aşırı docstring var mı?
5. Aşırı abstraction var mı?
6. Devasa fonksiyonlar var mı?
7. Dead code var mı?
8. Debug print var mı?
9. Temporary file var mı?
10. README gereksiz uzun mu?
11. README gerçek geliştirici tarafından yazılmış gibi doğal mı?
12. Dokümantasyon Türkçe mi?
13. Kod identifier'ları tutarlı İngilizce mi?
14. Test isimleri açıklayıcı mı?
15. Dosya yapısı gereksiz şişirilmiş mi?
16. Aynı bilgi birçok markdown dosyasında tekrar ediyor mu?
17. Public repository'ye gitmemesi gereken local artifact var mı?
18. `.gitignore` yeterli mi?
19. Configuration veya test fixture içinde secret/kişisel veri var mı?
20. Proje yeni bir mühendisin okuyup anlayabileceği durumda mı?

Bulduğun repository-quality sorunlarını düzelt.

Final kod tabanı:

> temiz, sade, açıklanabilir ve profesyonel bir mühendislik repository'si

olmalıdır.
