# Motor Tasarım Kararları

Bu doküman, AWE'nin kod okunduğunda hemen belli olmayan tasarım kararlarının gerekçelerini
toplar. Amaç, gelecekte bu koda dokunacak birinin "neden böyle yapılmış" sorusuna spesifikasyon
maddesi numarası aramadan cevap bulabilmesidir.

## Tek analiz kapsamı: projectId + subjectId

AWE aynı anda farklı uygulamalardan gelen event'leri birleştirip analiz eden bir sistem
değildir. Her analiz `projectId + subjectId` kapsamında çalışır ve iki farklı projenin
event'leri hiçbir zaman aynı Behavior Family içinde karışmaz. Bunun nedeni teknik değil
üründür: iki farklı uygulamadaki davranışların "aynı alışkanlık" sayılması anlamsızdır.
Evrensellik burada "farklı uygulamaların verisini karıştırmak" değil, "aynı Core algoritmasının
farklı Adapter'larla farklı uygulamalara ayrı ayrı uygulanabilmesi" anlamına gelir.

## Adapter sınırı neden var

Core Engine, hiçbir zaman bir müşterinin ham telemetry alan adlarını (`eventId` mi `evtId` mi,
`actionKey` mi `event_type` mı) bilmemelidir. Bu ayrım olmadan, her yeni müşteri entegrasyonu
motor koduna dokunmayı gerektirir ve "domain-independent core" iddiası kağıt üzerinde kalır.
`AdapterMapping`, alan eşlemesini ve değer normalizasyonunu (`value_map`) tamamen deklaratif
tutarak bunu zorunlu kılar: yeni bir müşteri, yeni bir YAML dosyasıdır, yeni bir Python modülü
değil. `config_examples/` altındaki üç farklı ham format (ShopWave'in canonical-benzeri
yapısı, LearnLoop'un `eventUid`/`learnerId` yapısı, TaskFlow'un düz `id`/`workspace` yapısı) bu
ayrımın gerçekten çalıştığını gösterir.

## `source` neden korunuyor

`source` (client/server/system), bir event'in hangi teknik taraftan geldiğini söyler; iş
anlamı taşımaz. Bunu atmak cazip görünebilir ama iki gerçek kanıt sınıfını kaybettirir:
sunucu tarafından üretilen `outcome`/`failure` event'leri (kullanıcının kendisi tetiklemedi
ama davranışın sonucunu gösterir) ve sistem tarafından üretilen lifecycle event'leri (gerçek
kullanıcı niyeti taşımaz, Family core'unu gereksiz bölmemeli). `source=server` event'lerini
körü körüne atmak yerine, güvenilir bir korelasyon yoksa (ör. sessionId eşleşmiyor) bu
event'ler zaten kendi tekil "sentetik" session'larına düşer ve hiçbir client behavior'a
rastgele bağlanmaz — bkz. `awe.adapter.observation_builder`'daki `synthetic:{event_id}`
fallback'i.

## `widget` neden ayrı tutuluyor ve neden Behavior kimliği değil

`screen` ve `widget`'ı erken birleştirmek (`screen + ":" + widget`) hem bilgi kaybettirir hem
de widget'ı fiilen kimliğin bir parçası yapar. Oysa widget, bir UI redesign'ında sıkça değişir
(`security_button` → `security_card`); aynı davranış aynı kalır. Bu yüzden Family
karşılaştırmasının atomik birimi (`Symbol`) yalnızca `(action, effect)` çiftidir — `screen`
ve `widget` ayrı, yardımcı bağlamsal kanıt olarak taşınır (`BehaviorStep` üzerinde), ama
karşılaştırma sembolünün parçası değildir. Bu tek karar, widget rename testinin geçmesini,
generic widget'ların (`primary_button`) yanlışlıkla ayırt edici sayılmamasını ve aynı zamanda
`target.ref`/parametre değerlerinin de kimliğe karışmamasını aynı anda sağlar.

## `destination` ve ağır capability manifest neden yok

`destination` bir mimari kavram olarak asla oluşturulmadı; bunun yerine dahili olarak
`ShortcutAnchor` kullanılır — family core sırasındaki bir **sembol** referansı, bir index değil
(bkz. aşağıda). Benzer şekilde, istemcinin neyi destekleyip desteklemediğini bilmek için ağır
bir capability-manifest sistemi kurulmadı; `ResolverContract` yalnızca beş alanlı minimal bir
sözleşmedir (`supports_navigate`, `supports_prefill`, `accepted_bindings`, `requires_review`,
`supports_runtime_validation`). Backend geçmiş loglardan istemcinin belirli bir state'e
gerçekten gidebileceğini bilemez; bu bilgiyi tahmin etmeye çalışmak yerine istemciden açıkça
istenir.

## Anchor neden bir index değil

Optional adımlar (bölüm 41'deki detour, bölüm 47'deki opsiyonel prefix) bir occurrence'ın uzun
diğerinin kısa olmasına yol açar; sabit bir index (`sequence[4]`) occurrence'lar arasında farklı
şeylere işaret eder. Bunun yerine `ShortcutAnchor.symbol`, family core'undaki bir `(action,
effect)` referansıdır; her occurrence'ta kendi normalize dizisi içinde bu sembol aranarak
çözülür (`resolve_anchor_step_index`). Sembol birden fazla kez görülüyorsa (loop), İLK görülme
noktası "bu yapısal adıma ilk ulaşım" anı olarak alınır.

## Family eşleştirmesi neden tam alignment/conformance değil

PM4Py'nin trace variant ve Directly-Follows Graph fikirleri değerlendirildi, ama tam Petri-net
tabanlı alignment/conformance checking kasıtlı olarak kullanılmadı. Loop içeren gerçek
kullanıcı akışlarında birden fazla eşit-maliyetli alignment bulunabilir; hangisinin seçildiği
implementasyon detayına bağlı hale gelir ve bu da "deterministik" ve "açıklanabilir" ilkeleriyle
çelişir. Bunun yerine sınırlı, deterministik bir model kullanılır: family, sınırlı sayıda temsilci
variant tutar (`FamilyVariant`, exact-sequence compression); bu variant'lar arasındaki
ardışık sembol çiftlerinden (bigram) bir "core/optional" ilişki tablosu türetilir
(`compute_relationships`). Yeni bir occurrence, ayrıştırıcı-ağırlıklı LCS benzerliği VE
core-bigram kapsaması birlikte sağlandığında kabul edilir. Core tablo her kabulden sonra
ailenin BİRİKMİŞ tüm variant'ları üzerinden yeniden hesaplanır — yalnızca en son eklenen üyeye
göre değil. Bu, "chaining" sürüklenmesini (art arda yalnızca bir önceki üyeye benzeyen
occurrence'ların zamanla alakasız bir davranışa doğru kaymasını) önler: bir sembol çiftinin
"core" sayılması ailenin tüm üyeleri arasındaki çoğunluk kapsamına bağlıdır.

## Discriminative weighting neden gerekli, ve nereye kadar

Bir token subject'in neredeyse bütün davranışlarında görülüyorsa (ortak bir başlangıç ekranı
gibi), benzerlik skorunu şişirmemesi için düşük ağırlık alır (IDF-benzeri, add-one smoothing
ile). Ancak adversarial test sırasında şu gerçek kusur bulundu: bir subject'in gözlenen
davranışının TAMAMI tek bir Habit'e aitse (çok yaygın durum), o Habit'in kendi çekirdek
sembolleri de "her yerde görülüyor" sayılıp ham IDF tarafından sıfıra çekiliyor — bu da nadir
görülen tek seferlik bir sapmayı (ör. bir kerelik detour) asıl çekirdekten daha "ayırt edici"
gösterip benzerlik hesabını tersine çeviriyordu (bkz. `tests/regression/
test_adversarial_edge_cases.py::test_first_seed_outlier_does_not_prevent_later_normal_occurrences_from_joining`).
Düzeltme iki parçalıdır: (1) ağırlık asla `min_symbol_weight` alt sınırının altına inmez, (2)
bir family'nin henüz tek bir (doğrulanmamış) temsilci variant'ı varsa VE yeni aday o tek
variant'ın sırayı-koruyan gerçek bir alt dizisiyse (yeni sembol getirmiyor), kapsama ve
benzerlik eşiği o tek örnek için gevşetilir. Bu gevşetme kasıtlı olarak dar tutulmuştur: aday
tohuma yeni semboller getiriyorsa (gerçek bir sapma, bölüm 58'deki chaining senaryosu gibi)
gevşetme uygulanmaz — aksi halde chaining ve ortak-başlangıç-sembolü korumaları yeniden açılırdı
(ilk düzeltme denemesi tam olarak bu hataya düştü ve regresyon testleriyle yakalandı).

## `target.ref` ve parametre değerleri neden family kimliğinin dışında

Aynı davranış farklı hedeflerle gerçekleştirilebilir (`FLOW target=A`, `FLOW target=B`, `FLOW
target=C` hepsi aynı family olmalı); target üzerinden ayrım yapmak support'un gereksiz
parçalanmasına yol açar. Target'ın kararlılığı (stabil mi, değişken mi) Family katmanının değil
Planner/PREFILL katmanının sorusudur — `FieldBinding` üzerinden, yalnızca bir plan adayı için
"bu alanı prefill etmek güvenli mi" sorusuna cevap verirken devreye girer.

## Regularity neden hard gate değil, eski burst formülü neden kullanılmadı

Klasik `1 - uniqueDays/support` formülü günde birden fazla kez kullanılan gerçek bir Habit'i
(ör. günde 5-10 session) burst sanabilir. Bunun yerine burst reddi tamamen `minDistinctDays` ve
`minDistinctSessions` sayımına dayanır — bir oran formülüne değil. Bu ayrım şunu sağlar: bir
gate'in kendi boyutu (gün/session sayısı) yetersizken toplam occurrence sayısı zaten eşiği
geçmişse ("zaten yoğun biçimde denendi ama yalnızca bir/iki günde yoğunlaştı"), bu NOT_HABIT
sayılır; occurrence sayısı da eşiğin altındaysa aile henüz gençtir ve PENDING_EVIDENCE'ta kalır.
Regularity ise haftalık/aylık/düzensiz-ama-gerçek Habit'leri reddetmemesi için hiçbir zaman
sert bir eşik olarak kullanılmaz; yalnızca açıklanabilirlik amaçlı bir "habit_strength" alt
bileşenidir ve anlamlı örneklem yoksa (yetersiz gün sayısı) `None` kalır — asla `1.0`'a
düşürülmez.

## Liveness neden mutlak gün sayısına değil gözlenen periyoda göre

Sabit bir "N gün kullanılmadıysa STALE" kuralı, aylık bir Habit için normal olan bir sessizliği
günlük bir Habit için gerçek bir terk edilme ile aynı kefeye koyar. Bunun yerine
`stalenessRatio = son_kullanımdan_bu_yana_geçen_gün / beklenen_boşluk` hesaplanır;
`beklenen_boşluk` bu Habit'in kendi gözlenen medyan gün-arası boşluğundan türetilir. Böylece
aylık bir Habit ancak gerçekten aylık periyodunun birkaç katı sessiz kaldığında stale sayılır.

## PREFILL neden event replay değil

PREFILL, gözlenen event'leri otomatik olarak simüle etmez. Her occurrence'ta anchor öncesi
canonical state (target + whitelist'lenmiş parametreler) çıkarılır, family seviyesinde bu
alanların dominance/coverage/sample_size istatistiği tutulur (`FieldBinding`) ve yalnızca
yeterince kararlı olanlar (STABLE) prefill önerisine dahil edilir. Kullanıcı, form önceden
doldurulmuş halde devam eder ve son onayı yine kendisi verir.

## Risk veto neden tek bir ağırlıklı skora indirgenmiyor

Habit, Risk ve Benefit kasıtlı olarak bağımsız kavramlardır ve tek bir final skorda
birleştirilmez. `evaluate_risk`, Benefit'i hiçbir zaman görmez; bir plan `BLOCK` aldığında bu
karar Benefit ne kadar yüksek olursa olsun geçersiz kılınamaz — `select_family_plan` bu kararı
sabit bir öncelik sırasıyla (`BLOCK > DOWNGRADE_TO_NAVIGATE > REDUCE_BINDINGS >
ALLOW_WITH_REVIEW > ALLOW`) uygular. Bu invariant hem birim testleriyle hem de
`tests/property/test_selection_invariants.py` içinde rastgele (Hypothesis ile üretilen, 0'dan
10.000'e kadar) Benefit değerleriyle doğrulanır.

## Motor seviyesinde sabit bir suggestion üst sınırı neden yok

Bir kullanıcının dört bağımsız, gerçek Habit'i varsa dördü de eligible kalmalıdır; motor
"en fazla 3 öneri göster" gibi keyfi bir üst sınır koymaz — kaç tanesinin gösterileceği bir UI
kararıdır. Anormal derecede yüksek bir suggestion sayısı (ör. 25+) motor sağlığı açısından bir
uyarı sinyalidir (fragmentation, zayıf dedupe) ve `scripts/evaluate_engine.py`'nin ürettiği
sağlık metrikleriyle (families_per_subject, eligible_suggestions_per_subject) izlenir — sert
bir kesme ile değil.

## Shortcut kullanımı neden organic kanıt sayılmıyor

Bir Habit'ten üretilen shortcut kullanılmaya başlandığında (`trigger=shortcut`), bu kullanım
organik tekrar kanıtına eklenirse öneri kendi kanıtını yapay olarak büyütür — bir geri besleme
döngüsü oluşur. Bu yüzden `has_shortcut_trigger=true` olan occurrence'lar
`organic_occurrences`'a hiçbir zaman dahil edilmez; ayrı bir `shortcut_utility_occurrences`
sayacında tutulur (açıklanabilirlik için, ama Habit kararını hiç etkilemez).

## Bulunan ve düzeltilen gerçek hatalar

Adversarial review sırasında (bölüm 139) implementasyonun kendisini kırmaya çalışırken iki
gerçek hata bulundu; ikisi de `tests/regression/` altında kalıcı test olarak eklendi:

1. **Aşırı "back" basışları uydurma sembol sızdırıyordu.** Bounded detour normalizasyonu, geri
   dönülecek bir state kalmadığında (yığın boşaldığında) fazladan `navigate_back` event'ini
   literal bir adım olarak normalize edilmiş diziye ekliyordu. `back` kendi başına anlamlı bir
   davranış adımı değildir; düzeltme bu durumda event'i sessizce (ama `detour_step_count`'a
   yansıyacak şekilde) yutar.
2. **İlk occurrence atipikse (bölüm 51 yukarıda anlatılan discriminative weighting kusuruyla
   birleşince) sonraki gerçek occurrence'lar reddediliyordu.** Yukarıda anlatıldı.

Ayrıca geliştirme sırasında (adversarial review'dan önce) şu ikisi de bulunup düzeltildi:

3. **`seed_family`, ilk occurrence'ı `member_series_ids`'e eklemiyordu.** Bu, family'nin
   ilk üyesinin Risk katmanındaki `anchor_coverage` gibi hesaplarda sayılmamasına yol açardı.
   `seed_family` artık `accept_series` ile aynı iç mekanizmayı kullanır.
4. **SQLite, `DateTime(timezone=True)` sütunlarında dahi timezone bilgisini kalıcı saklamaz.**
   Okuma sırasında naive bir datetime dönebilir, bu da aware/naive karşılaştırmalarında
   `TypeError` üretir. Çözüm, hem yazarken UTC'ye normalize eden hem de okurken eksik tzinfo'yu
   tamamlayan bir `UTCDateTime` tip dekoratörüdür (`awe.persistence.types`) — kod tabanının geri
   kalanı asla naive bir datetime görmez.
