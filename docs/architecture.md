# Mimari

Bu doküman AWE'nin (Adaptive Workflow Engine) iç mimarisini, katmanlar arası veri akışını ve
gerçek bir kullanım senaryosu üzerinden pipeline'ın uçtan uca nasıl işlediğini anlatır.

## Genel bakış

AWE, bir mobil uygulamadan gelen event log'larını kullanarak her kullanıcıyı (subject)
`projectId + subjectId` kapsamında bağımsız analiz eder. Amaç, kullanıcının farklı
session'larda ve zaman içinde tekrar ettiği gerçek davranışları bulmak, bunları bir davranış
ailesi (Behavior Family) altında toplamak, gerçek bir alışkanlık (Habit) olup olmadığına karar
vermek ve uygun olanlar için güvenli NAVIGATE/PREFILL kısayolları önermektir. Motor hiçbir
zaman kullanıcı adına nihai/geri alınamaz bir işlem yapmaz (EXECUTE yoktur).

Pipeline sırayla şu katmanlardan geçer:

```
RAW EVENT
   → ADAPTER (canonical Observation)
   → ORDERING (session içi deterministik sıra)
   → O-SERIES EXTRACTION (behavior attempt'lere bölme)
   → BEHAVIOR FAMILY (session'lar arası kümeleme)
   → HABIT (gerçek tekrar mı?)
   → SHORTCUT PLANNER (NAVIGATE/PREFILL adayları)
   → RISK (güvenli mi?)
   → BENEFIT (ne kadar iş kaldırıyor?)
   → FINAL SELECTION (dominance, dedupe, fallback)
   → SUGGESTION (lifecycle ile kalıcı)
```

Her katman yalnızca bir önceki katmanın çıktı modelini girdi alır ve kendi sorumluluğu
dışındaki hesabı tekrar etmez — örneğin Final Selection, Risk veya Benefit'i yeniden
hesaplamaz; yalnızca önceden hesaplanmış sonuçlar arasında seçim yapar.

Kod organizasyonu bu katmanlarla birebir örtüşür: `src/awe/<layer>` altında her katmanın kendi
paketi vardır (`adapter`, `ordering`, `series`, `families`, `habit`, `planner`, `risk`,
`benefit`, `selection`, `lifecycle`). `src/awe/domain` bu katmanların paylaştığı, uygulamadan
bağımsız veri modellerini taşır; `src/awe/services` katmanları birbirine bağlayan orkestrasyon
mantığını, `src/awe/persistence` ise veritabanı şemasını ve domain nesneleri ile satırlar
arasındaki dönüşümü içerir.

## Uçtan uca örnek: şifre sıfırlama alışkanlığı

ShopWave adlı bir e-ticaret uygulamasının kullanıcısı `user_42`, ayda bir kez şifresini
değiştiriyor. Aşağıda bu davranışın altı farklı session'da nasıl işlendiğini adım adım
izliyoruz.

### 1. Raw event → Adapter → Observation

Kullanıcının bir session'ında ürettiği ham event'lerden biri:

```json
{
  "eventId": "evt_9812",
  "projectId": "shopwave",
  "subjectId": "user_42",
  "sessionId": "sess_104",
  "timestamp": "2026-08-05T10:35:22+03:00",
  "source": "client",
  "actionKey": "open_security",
  "role": "action",
  "effect": "route",
  "trigger": "button",
  "screen": "settings",
  "widget": "security_row",
  "target": null,
  "status": "success",
  "breaksEpisode": false
}
```

`config_examples/shopwave.yaml` içindeki mapping bu alanları doğrudan canonical isimlere
eşler (`eventId → event_id`, `actionKey → action`, ...). Aynı davranış LearnLoop gibi
tamamen farklı alan adları kullanan bir müşteride de (`eventUid`, `learnerId`, `actionName`,
...) aynı canonical `Observation` modeline dönüşür — AWE Core bu iki müşteri arasındaki farkı
hiçbir zaman görmez. `AdapterMapping` bu dönüşümü tamamen deklaratif (path + value_map)
tanımlar; yeni bir müşteri entegrasyonu yeni kod değil, yeni bir YAML dosyası demektir.

### 2. Ordering ve O-Series extraction

`user_42`'nin bu session'daki tam akışı şöyle:

```
open_settings (route)
open_security (route)
select_change_password (select)
enter_current_password (input)
enter_new_password (input)
confirm_password_reset (confirm, status=success)
```

`order_session`, event'leri yalnızca timestamp + `event_id` tie-break'i ile sıralar (motor
hiçbir zaman kaynaktan bir sıra numarası istemez ya da uydurmaz); bu sıralama girdi batch
sırasından tamamen bağımsızdır.
`extract_series`, bu sıralı akışı iki sınıra göre böler: açık `breaksEpisode=true` işaretine
(ör. `logout`) ve `role=outcome` ya da `effect ∈ {submit, confirm}` olan bir adımın
`status=success` olmasına (doğal tamamlanma noktası). Bu örnekte akışın tamamı tek bir O-Series
olarak çıkar, çünkü tek tamamlanma noktası (`confirm_password_reset`) dizinin sonundadır.

Başka bir session'da kullanıcı önce yanlışlıkla "bildirim ayarları"na girip geri dönüyor:

```
open_settings → open_notifications → back → open_security → select_change_password → ...
```

`back` adımı canonical `effect=navigate_back` ile işaretlendiğinde (bölüm 40-41), normalizasyon
bunu ve `open_notifications`'ı karşılaştırma projeksiyonundan bounded biçimde çıkarır — ham
kanıt (`raw_observations`) korunur, yalnızca Family karşılaştırması için kullanılan
`normalized_steps` etkilenir. Sonuç, "temiz" session ile aynı sembol dizisidir.

### 3. Behavior Family

Altı session'ın normalize edilmiş sembol dizileri (`(action, effect)` çiftleri) hemen hemen
aynıdır; küçük farklar (detour, bir yeniden deneme) normalizasyonla giderilir. İlk occurrence
family'yi tohumlar; sonraki beşi `match_series` ile karşılaştırılır. Karşılaştırma, ayrıştırıcı
ağırlıklı bir LCS benzerliği (yaygın semboller düşük ağırlık alır — ör. `open_settings` bu
kullanıcının neredeyse her davranışında görülüyorsa ayırt ediciliği düşüktür) ve family'nin
temsilci variant'ları üzerinden hesaplanan core-bigram kapsamasının birlikte sağlanmasını
gerektirir. Sonuç `MATCH`, `VARIANT_MATCH`, `AMBIGUOUS` veya `NO_MATCH` olabilir.

Bu örnekte family şu duruma ulaşır:

```
representative_variants:
  - (open_settings, open_security, select_change_password, enter_current_password,
     enter_new_password, confirm_password_reset)  support=5
  - (open_settings, open_security, select_change_password, enter_new_password,
     confirm_password_reset)  support=1   # kullanıcı bir seferinde mevcut şifreyi atladı
cohesion: 0.93
```

Core ilişki tablosu, her iki variant'ta da görülen ardışık çiftleri ("core") ile yalnızca
birinde görülenleri ("optional") ayırt eder; `enter_current_password` opsiyonel bir adım olarak
işaretlenir, family bu yüzden gereksiz yere bölünmez.

### 4. Habit

Family, altı occurrence'ının hepsi organik (`trigger != shortcut`) olduğu için Habit
katmanına girer. Gerçek gün/session sayıları hard gate'leri karşılıyorsa (`min_occurrences=3`,
`min_distinct_sessions=2`, `min_distinct_days=3`), aşağıdaki gibi bir kanıt üretilir:

```
organic_occurrences: 6
distinct_days: 6
distinct_sessions: 6
median_gap_days: ~30
regularity: 0.81
liveness: LIVE (son kullanım, gözlenen medyan boşluğun ~1.2 katı önce)
decision: PASS
```

Aylık bir davranış olduğu için `median_gap_days` büyük olsa da, "liveness" mutlak bir gün
sayısına değil bu Habit'in KENDİ gözlenen periyoduna göre değerlendirilir — bu yüzden aylık bir
Habit, günlük bir Habit'le aynı mutlak eşikle "stale" sayılmaz (bkz.
`docs/engine-decisions.md`).

### 5. Shortcut Planner

Family core'u üzerinde, terminal olmayan (submit/confirm dışı) her pozisyon bir aday anchor
olabilir. Bu örnekte:

* **NAVIGATE** — `open_security` (family core'undaki ilk `route` pozisyonu): kullanıcıyı
  doğrudan güvenlik ekranına götürür.
* **PREFILL (partial)** — `select_change_password` sonrası: henüz hiçbir alan doldurulmamış,
  yalnızca doğru alt-ekrana konumlandırma.
* **PREFILL (deep)** — `enter_new_password` sonrası: `target` bu akışta hiç gözlenmediği için
  (şifre değiştirme bir target taşımaz) yalnızca "buraya kadar ilerlemiş" durumu temsil eder.

PREFILL, gözlenen eventleri yeniden oynatmaz; yalnızca "kullanıcı bu noktaya kadar tipik olarak
hangi state'i kurmuş" sorusunun istatistiksel cevabını taşır.

### 6. Risk

`confirm_password_reset` adımının kendisi `effect=confirm` taşıdığı için canonical güvenlik
politikasına göre `BLOCKED`'dır — Planner zaten bu adımı anchor olarak seçmez, Risk katmanı
bunu bağımsız olarak da doğrular (defense in depth). NAVIGATE ve PREFILL adayları için:

```
sample_size: 6         (>= min_sample_size_for_confidence)
failure_rate: 0.0
data_quality_score: 1.0
family_cohesion: 0.93  (>= min_family_cohesion_for_allow)
decision: ALLOW
```

### 7. Benefit

NAVIGATE için "kaydedilen eylem" yalnızca `role=action` olan adımlardır — `open_security`
adayı, kullanıcının o noktaya erişmek için attığı `open_settings` ve `open_security` adımlarının
ikisini de kapsar (medyan 2 kaydedilen eylem). Derin PREFILL adayı `enter_current_password` ve
`enter_new_password` dahil daha fazla adımı kapsadığından medyan kaydedilen eylem sayısı daha
yüksektir.

### 8. Final Selection ve lifecycle

Aynı family içinde NAVIGATE ve PREFILL adayları hayatta kaldığında, PREFILL birincil öneri,
NAVIGATE ise güvenli fallback olarak seçilir (bölüm 83'teki "FULL PREFILL → PARTIAL PREFILL →
NAVIGATE → BLOCK" zincirinin bir örneği). Suggestion ilk kez `ACTIVE` durumunda oluşturulur;
kullanıcı reddederse `DISMISSED` olur ve `dismiss_cooldown_days` süresi dolup davranış organik
olarak devam ederse otomatik olarak `ACTIVE`'e geri döner.

## Artımlı analiz

Bir subject için `POST /analyze` her çağrıldığında motor, o subject'in **yalnızca henüz bir
O-Series'e atanmamış** observation'larını işler; mevcut family'ler veritabanından
(`family_key` — sabit, opak bir string) yüklenip artımlı olarak genişletilir. Bu tasarım iki
nedenle tercih edilmiştir:

1. **Kimlik kararlılığı** — bir family'nin `family_key`'i, üzerine yeni occurrence eklendikçe
   asla değişmez; API tüketicileri (ör. dismiss edilmiş bir suggestion'ın anahtarı) kalıcı
   kalır.
2. **Basitlik** — tüm geçmişi her seferinde yeniden işlemek yerine yalnızca yeni kanıtı işlemek,
   incremental-state tutarlılık hatalarının en büyük kaynağı olan "hangi family'nin hangi
   occurrence'ı ne zaman gördüğü" karmaşasını ortadan kaldırır.

Buna karşılık, bir family'ye dokunulduğunda o family'nin Habit/Planner/Risk/Benefit/Selection
zinciri **baştan** hesaplanır (artımlı güncellenmez). Bu bilinçli bir tercihtir: bu katmanların
girdisi (bir family'nin üye occurrence sayısı, tipik olarak onlarca-yüzlerce) küçüktür, tam
yeniden hesaplama ölçüm yapılabilir bir maliyet artışı yaratmaz (bkz. `docs/evaluation.md` —
130 subject / 15.000+ event tüm pipeline'dan ~13 saniyede geçiyor), buna karşılık artımlı
delta-güncelleme (ör. "yeni bir occurrence geldiğinde median_gap_days'i nasıl güncellerim")
kolayca tutarsızlığa yol açabilecek bir sınıf hataya kapı açar.

Normalize edilmiş O-Series adımları ayrı bir tabloda **tutulmaz**: veritabanı yalnızca ham
`observations` satırlarını saklar, `normalized_steps` her okumada aynı deterministik
normalizasyon fonksiyonuyla yeniden hesaplanır. Bu, normalizasyon mantığının iki yerde (yazma
ve okuma) bakımsız kalma riskini ortadan kaldırır.

## Bilinen sınırlamalar

* **Tek session içinde birden fazla bağımsız davranış.** O-Series sınırları yalnızca
  `breaksEpisode` ve doğal tamamlanma noktalarına (submit/confirm başarı) dayanır. Bir
  kullanıcı aynı session içinde tamamlanma sinyali üretmeden konu değiştirirse (ör. ayarları
  gezip sonra ürün aramaya geçerse), bu iki davranış tek bir uzun O-Series içinde kalabilir.
  Family eşleştirmesinin LCS tabanlı benzerlik ölçütü araya giren yabancı adımlara karşı büyük
  ölçüde toleranslı olsa da, bu MVP kapsamında bilinçli bir basitleştirmedir; yeni bir
  segmentasyon sinyali (ör. uzun bir `role=context` boşluğu) gerektiğinde eklenebilir.
* **PostgreSQL üzerinde gerçek doğrulama yapılmadı.** Şema yalnızca portable SQLAlchemy
  tipleriyle yazılmıştır ve SQLite üzerinde kapsamlı test edilmiştir; geliştirme ortamında
  yerel bir PostgreSQL kurulumu bulunmuyordu.
* **Çok-kiracılı proje konfigürasyonu dosya tabanlıdır.** `ProjectRegistry`,
  `config_examples/` altındaki YAML dosyalarını okur; gerçek bir üretim sisteminde bu bir
  config-upload/yönetim API'sine dönüşür. Bu MVP sınırlaması `_build_mapping`/
  `_build_engine_overrides` (`awe.config.project_config`) değiştirilerek genişletilebilir.
* **Resolver yetenekleri istek başına beyan edilir.** Backend, istemci uygulamanın belirli bir
  state'e gerçekten programatik olarak gidip gidemeyeceğini bilemez (bölüm 78); bu bilgi
  `POST /analyze` gövdesinde `ResolverCapabilities` olarak taşınır ve proje düzeyinde kalıcı bir
  varsayılana bağlanmamıştır.
* **Split/merge candidate üretimi yok.** Her family'nin cohesion'ı her occurrence kabulünde
  güncel tutulur ve dışarıya açıktır, ama düşük cohesion'lı family'leri "split adayı" ya da
  birbirine çok benzeyen iki family'yi "merge adayı" olarak işaretleyen ayrı bir batch
  bakım işi yoktur. Değerlendirme veri kümesinde (`docs/evaluation.md`) gözlenen cohesion
  her zaman 1.0 çıktığı için bu eksikliğin pratik etkisi ölçülememiştir; gerçek, uzun
  ömürlü kullanıcı verisiyle cohesion zamanla düşerse bu bilinçli bir genişletme noktasıdır.
