# Motor Tasarım Kararları

Bu doküman, kod okunduğunda hemen belli olmayan tasarım kararlarının gerekçelerini toplar.
Özellikle spesifikasyonun (`AWE_MVP_TASARIMI_BAGIMSIZ_INCELEME.md`) açıkça bırakmadığı boşlukları
nasıl doldurduğumuzu ve önceki tasarımdan bilinçli olarak nerede ayrıldığımızı belgeler.

## 1. Kullanıcı talebiyle yapılan bilinçli spesifikasyon sapması: sıra-korumalı ortak alt dizi

Bölüm 6.4 açıkça "Fuzzy merge yoktur. Optional step toleransı yoktur." der ve Episode
Candidate Builder'ı yalnızca **ardışık (contiguous)** ortak alt diziler bulacak şekilde
tanımlar. İlk uygulama bunu harfiyen uyguladı, ancak gerçek kullanım geri bildiriminde bu
kuralın pratikte aşırı parçalanmaya yol açtığı görüldü: gerçek kullanıcılar bir davranışı
neredeyse hiçbir zaman birebir aynı, kesintisiz adım dizisiyle tekrar etmez (araya bir
bildirim kontrolü, yanlış tıklama, retry vb. girer) — yalnızca tam ardışıklık arayan bir
algoritma bu yüzden gerçek alışkanlıkları sistematik olarak kaçırıyordu.

Bunun üzerine `awe.episodes.candidates` bilinçli olarak spesifikasyonun bu tek maddesinden
sapacak şekilde güçlendirildi: iki chunk arasındaki ortak desen artık **sıra-korumalı ama
ardışık olması gerekmeyen** bir alt dizi (klasik LCS — longest common subsequence) olarak
aranıyor. Değerlendirilen ve reddedilen alternatifler:

- **Eski core/optional adım modeli** (fuzzy benzerlik eşiği + ambiguity margin, önceki
  tasarımdan) — en esnek ama "fuzzy merge yoktur" ilkesinden en uzağı; benzerlik skoru ve
  eşik kalibrasyonu gerektirir, bu motorun tam olarak kaçınmaya çalıştığı türden bir
  karmaşıklıktır.
- **Sabit K-adıma kadar atlama toleransı** — daha basit/öngörülebilir ama keyfi bir sabit
  gerektirir ve LCS'in kendiliğinden sağladığı "en uzun ortak deseni bul" garantisini vermez.
- **Seçilen: LCS tabanlı sıra-korumalı eşleşme** — eşleşen HER adım hâlâ tam (exact) değer
  eşitliği taşır; yalnızca aralarındaki "boşluk" toleransı gevşetilir. Yeni bir benzerlik
  skoru veya eşik eklemez, yalnızca contiguity zorunluluğunu kaldırır. Bir chunk çiftinin
  birden fazla bağımsız ortak deseni olabileceğinden, tek LCS bulunduktan sonra eşleşen
  pozisyonlar maskelenip arama tekrarlanır ("iterative peeling").

Bu değişiklik `EpisodeCandidateKind.COMMON_RUN`'ı `COMMON_SUBSEQUENCE` olarak yeniden
adlandırdı ve `EpisodeCandidate.start_index: int` alanını (yalnızca ardışık aralıklar için
anlamlıydı) `step_indices: tuple[int, ...]` ile değiştirdi (ardışık olmayan pozisyon
kümelerini de taşıyabilir). Downstream katmanların hiçbiri (Target Resolver, Habit, Anchor,
Screen Transition Evidence) bu değişiklikten etkilenmedi çünkü hepsi `candidate.steps`
tuple'ının kendi iç sırasına göre çalışır, kaynak dizideki fiziksel ardışıklığa değil.

## 2. Önceki tasarıma göre bilinçli tersine dönüşler

Bu motor bir önceki oturumda yeniden tasarlanmış bir sınıflandırma katmanının üzerine inşa
edildi. Yeni spesifikasyon iki noktada o tasarımın **tam tersini** söylüyor; ikisi de burada
harfiyen uygulandı:

- **`source`**: Önceki tasarım "source hiçbir zaman gerçek bir kullanıcı ACTION'ını dışlamak
  için kullanılmaz" diyordu. Yeni spesifikasyon (bölüm 6.2) `source != "client" → CONTEXT`
  der — yani server/system kaynaklı bir event artık asla ACTION olamaz, trigger ne olursa
  olsun.
- **`status`**: Önceki tasarım `status != success → IGNORE` idi (ilk kontrol). Yeni
  spesifikasyon (bölüm 3 kural 4, bölüm 6.2) `status`u sınıflandırmadan tamamen çıkarır —
  fail/cancel bir ACTION'ı diziden atmaz. Bunun yerine bir occurrence'ın `RESOLVED` mü
  `ATTEMPT_ONLY` mi olduğu Anchor Resolver'da (bölüm 6.9) en az bir success var mı diye
  kontrol edilerek belirlenir — status artık "bu bir action mı" sorusuna değil "bu action
  başarılı oldu mu" sorusuna cevap verir.

## 3. Spesifikasyonun boş bıraktığı, burada doldurulan noktalar

- **`USER_TRIGGERS` tanımı** (bölüm 6.2): Classifier sözde kodu `trigger in USER_TRIGGERS`
  der ama bu kümeyi hiçbir yerde tanımlamaz. Bölüm 4'ün trigger sözlüğünden `automatic` ve
  `unknown` çıkarılarak türetildi — geri kalan tüm değerler kullanıcının doğrudan girdisidir
  (bkz. `awe.adapter.classification.USER_TRIGGERS`).
- **`shortcut` trigger değeri**: Bölüm 4'ün trigger sözlüğünde yok. Olmadan, bir kısayolun
  kendi tetiklediği event'in organik kullanım kanıtı olarak sayılmasını engelleyecek hiçbir
  mekanizma kalmıyordu (eski tasarımın red line #13'üne karşılık gelen bir kendini-besleme
  riski). `shortcut` kasıtlı bir superset eki olarak eklendi; sınıflandırma kurallarını
  etkilemez (`USER_TRIGGERS`'a dahildir, ACTION üretir), yalnızca
  `awe.habit.assessment.evaluate_habit`'in organik kanıt sayımını etkiler.
- **Anchor STRONG/MEDIUM/WEAK ayrımı** (bölüm 6.9): Belge yalnızca WEAK'i formülle tanımlar
  (route/open-only iz + stabil post-view). STRONG/MEDIUM ayrımı, belgenin üç kanıt
  kaynağından türetildi: pozisyon exact target taşıyorsa STRONG, yalnızca outcome-evidence
  effect taşıyorsa MEDIUM.
- **`TargetVariantKind.VARIABLE_TARGET` yorumu** (bölüm 6.6): Belge dört durumu net bir eksen
  üzerinde tanımlamaz. Burada bir fingerprint'in kendi İÇİNDEKİ distinct non-null değer
  sayısına bakılır — bir occurrence'ın kendi adımları birden fazla farklı hedefe değiniyorsa
  (ör. "workspace_1" ve "report_9" aynı occurrence içinde) bu VARIABLE_TARGET'tır ve Shortcut
  Intent Builder'ın compound-identity reddiyle (bölüm 6.12) doğrudan örtüşür. İki AYRI
  occurrence farklı ama kendi içinde tutarlı hedeflere sahipse (course_42 vs course_17), bunlar
  zaten farklı fingerprint'ler oldukları için ayrı ayrı FIXED_TARGET variant'lara ayrılır.
- **Risk vektörünün yorumlanması** (bölüm 6.13): Belge yalnızca alan adlarını verir
  (`policy, plan_surface, execution_exposure, interaction_guard, observed_goal_sensitivity,
  reliability, data_quality, reasons`), tiplerini/formüllerini vermez. Burada:
  - `policy` = anchor'ın effect'inin proje konfigürasyonundaki güvenlik sınıfı.
  - `observed_goal_sensitivity` = Scope'a dahil OLMAYAN, anchor'dan sonra gözlenen adımların
    en hassas policy'si — kısayolun neyi kasıtlı olarak dışarıda bıraktığını gösteren, salt
    açıklanabilirlik amaçlı bir alan (BLOCK nedeni değildir; bu rol zaten `policy`'de).
  - `execution_exposure` her zaman `NONE`'dır (EXECUTE modu hiç yoktur).
  - `reliability` = anchor pozisyonundaki gözlenen success/fail/cancel oranları.
- **Episode Candidate azami uzunluğu** (bölüm 6.4): Belge açıkça "implementer kararı" olarak
  bırakır ("Eski MVP'deki max=8 korunacaksa..."). `EpisodeConfig.max_symbols=8` olarak
  sabitlendi, konfigüre edilebilir bırakıldı.
- **Risk'in `mixed_outcome_rate_threshold`, `min_data_quality_for_allow` eşikleri**: Belge bu
  eşiklerin var olması gerektiğini ima eder (`MIXED_OBSERVED_OUTCOMES`, "kritik quality flag")
  ama sayı vermez. Sırasıyla `0.3` ve `0.5` olarak seçildi; `RiskConfig` üzerinden proje
  başına override edilebilir.

## 4. Eski tasarımdan kalan, artık anlamsızlaşan kavramların kaldırılması

- **Fuzzy family matching** (weighted-LCS benzerlik, IDF ayrıştırıcı ağırlıklandırma,
  ambiguity margin, core/optional bigram ilişkileri, cohesion skoru): Bölüm 6.5 "Fuzzy merge
  yoktur" der. Family artık deterministik exact-equality gruplamasıdır; bu makine tamamen
  kaldırıldı (`families/similarity.py`, `families/weighting.py` silindi).
- **Retry/detour normalizasyonu** (`series/normalization.py`): Aynı gerekçeyle kaldırıldı —
  yeni O-Series Builder (bölüm 6.3) tekrarlanan adımları veya geri-navigasyonu sıkıştırmaz;
  bunlar exact sembol dizisine oldukları gibi girer ve gerekirse family'yi böler (bölüm 9.3).
- **Çok alanlı PREFILL binding'leri** (`FieldBinding`, `planner/state_reconstruction.py`,
  `planner/candidates.py`): Yeni Shortcut Intent yalnızca tek bir `target: str | None` taşır
  (bölüm 6.12); "workspace_1 + report_9" gibi bileşik kimlikler taşınamaz, `UNSUPPORTED`
  olur. `ResolverContract` (client capability sözleşmesi, `accepted_bindings` dahil) bu
  yüzden anlamını yitirdi ve kaldırıldı — yeni belge zaten böyle bir kavramdan hiç bahsetmez.
- **Fallback plan**: Bir `TargetVariant`'ın en fazla bir Anchor'ı (dolayısıyla en fazla bir
  Shortcut Intent'i) olabildiği için "birincil + fallback plan" kavramı da anlamsızlaştı;
  `Suggestion.fallback_intent_ids` kaldırıldı.
- **`SuggestionState.ELIGIBLE`**: Eski `lifecycle/transitions.py` bu durumu hiçbir zaman
  üretmiyordu (kod incelemesiyle doğrulandı) — tanımlı ama ölü bir enum değeriydi. Yeni
  tasarımda hiç yok.
- **İki günlük burst artık Habit sayılıyor**: Eski `min_distinct_days` varsayılanı 3'tü; yeni
  spesifikasyonun (bölüm 6.7) kapısı `distinct day >= 2`. Bu, "iki farklı günde, session
  sayısı ne olursa olsun, artık HABIT_DETECTED üretir" sonucunu doğurur — belge yalnızca
  tek-gün burst'ü açıkça reddeder (bölüm 9.8); iki-gün durumu için implementer'a bırakılmış
  bir eşik gevşemesidir, sessizce geri alınmadı.
- **`widget_rename`/`parameter_drift` sentetik profilleri** (`awe.testing.generators`)
  kaldırıldı: `widget` alanı artık yok (test ettikleri "kimlikten hariç tutulan alan" kavramının
  analogu kalmadı — tam tersine `screen` artık kimliğin PARÇASI); `parameter_drift`'in test
  ettiği `FieldBinding` recent-drift kavramı yeni tasarımda yok, `target_variable` zaten aynı
  temel senaryoyu (hedef değişkenliği) kapsıyor.

## 5. Korunan altyapı (spesifikasyonun ele almadığı alanlar)

Spesifikasyon yalnızca Adapter→Selector zincirini tanımlar; persistence şeması, API sözleşmesi,
config-yükleme mekanizması, structured logging ve suggestion lifecycle'ı ele almaz (bölüm 9.10,
9.11). Bu alanlarda mevcut, çalışan mekanizma korunmuş, yalnızca yeni veri şekline uyarlanmıştır:

- Persistence hâlâ yalnızca portable SQLAlchemy tipleri kullanır; tek migration dosyası yerinde
  düzenlenir (gerçek dağıtılmış bir veritabanı yoktur).
- `ProjectRegistry` hâlâ dosya tabanlıdır (`config_examples/`); config-upload API'si yoktur.
- Suggestion lifecycle (`dismiss`/cooldown/revive) aynı state machine'i kullanır; yalnızca
  girdi şekli (artık `HabitEvidence.last_seen_at` üzerinden kendi basit staleness eşiğini
  hesaplar) yeni pipeline'a uyarlanmıştır — `LifecycleConfig.stale_after_days` (varsayılan 30)
  bu amaçla eklendi; eski `stale_after_missed_cycles` alanı zaten hiç tüketilmiyordu (ölü
  konfigürasyon alanıydı, kod incelemesiyle doğrulandı) ve kaldırıldı.
- API'de hâlâ hiçbir kimlik doğrulama/yetkilendirme mekanizması yoktur — bu, önceki
  incelemede de flagged edilmiş, henüz kapatılmamış bir MVP açığıdır.

## 7. Kullanıcı talebiyle eklenen regularity/support istatistik katmanı

Bölüm 6.7 açıkça "Bu katman regularity/entropy/lift gibi gelişmiş istatistikler kullanmaz ...
MVP dışında bırakılmıştır" der ve Habit Evaluator'ı yalnızca `distinct session >= 3 AND
distinct calendar day >= 2` hard kapısına indirger. Kullanıcı, bu kapıyı DEĞİŞTİRMEDEN, üzerine
gerçek bir düzenlilik/destek ölçümü eklenmesini talep etti — amaç, kapıyı az farkla geçen bir
örüntüyle gerçekten tekrarlayan günlük/haftalık bir alışkanlığı ayırt edebilmek.

Bu, spesifikasyonun MVP sınırının kasıtlı, kapsamı sınırlı bir aşımıdır; yine de MVP-uygun
sayılır çünkü: (a) yeni bir hard gate DEĞİLDİR — HABIT_DETECTED kararı hâlâ yalnızca mevcut
sayımlara bakar; (b) Selector sıralamasına (`selection.selector._ranking_key`) GİRMEZ — bu da
kullanıcıyla netleştirilen bir kapsam kararı, gerçek veriyle rakamlar görülmeden sıralama
mantığına dokunulmadı (bkz. bu bölümün altındaki #6'daki `saved_actions` sıralama kararına
paralel bir temkinlilik); (c) deterministiktir — ML/inference yoktur, yalnızca ortalama/
popülasyon-stdev/sabit eşik; (d) var olan `distinct_days` tarih-kümesi idiyomunu birebir
yeniden kullanır. Legacy spesifikasyonun (artık geçersiz `docs/legacy/AWE_MASTER_SPEC.md`
§64-66) iki uyarısı bu tasarımı doğrudan şekillendirdi: regularity asla hard gate olmamalı
(weekly/monthly alışkanlıklar kaçırılmamalı) ve support sınırsız büyüyüp diğer kanıtı
ezmemeli — ikisi de "sadece ölç, gate etme" kararıyla karşılanmış oluyor.

**Cadence (5 kova):** `mean_gap_days` + `gap_regularity` (`= max(0, 1 - CV)`) üzerinden
türetilir. Düzenlilik önce kontrol edilir — `gap_regularity < min_gap_regularity_for_named_cadence`
(varsayılan 0.7, yani CV > 0.3) ise sonuç ortalamadan bağımsız IRREGULAR'dır
(`irregular_recurring` sentetik profiliyle doğrulandı: günler `(1,4,11,18,29,43,55)`, ortalama
9.0 gün WEEKLY aralığına düşerdi ama CV≈0.41 diskalifiye eder — bu, düzenlilik kontrolünün
gerçekten işe yaradığını kanıtlayan senaryo). Değerlendirilen ve reddedilen alternatif: her kova
için bağımsız [min,max] çifti — ilk tasarım böyleydi ama kovalar arası KAPSANMAYAN aralıklar
bırakıyordu (ör. ortalama 3 veya 22 gün hiçbir kovaya düşmüyordu). Seçilen: dört artan üst-sınır
eşiği (yalnızca üst sınır, komşu kovanın alt sınırı örtük — `daily<=2.0`, `weekly<=10.0`,
`biweekly<=20.0`, `monthly<=45.0`, ötesi IRREGULAR) — boşluk kalmaz VE her eşik `HabitConfig`
üzerinde bağımsız override edilebilir tek bir `float` alanıdır. Sınır durumu bilerek kabul
edildi: sabit 2 günlük bir boşluk (`long_workflow` sentetik profili) DAILY'ye düşer — "gün aşırı"
bir örüntüyü "günlük" etiketlemek tartışılabilir ama yeni bir kova eklemeyi gerektirmeyen, MVP
lehine küçük bir ödünleşim.

**Support (pencereli payda):** `active_days_total` = subject'in TÜM session'larından gelen,
ama YALNIZCA bu variant'ın kendi `[first_seen_at, last_seen_at]` penceresi içindeki distinct
gün sayısı. Değerlendirilen ve reddedilen alternatif: whole-history payda — reddedildi
(kullanıcı kararı) çünkü eski bir alışkanlığın yakın zamanda yoğun tekrarını "düşük destek"
olarak cezalandırırdı. Trade-off: yeni/kısa ömürlü bir pattern küçük ve gürültüye duyarlı bir
paydaya sahip olur — bu bir gate DEĞİL, yalnızca kanıt alanı olduğu için kabul edilebilir, ama
görünürlük amaçlı gelecekteki her tüketici bunu küçük `active_days_total` değerlerinde
düşük-güven olarak ele almalıdır. `active_days_total >= distinct_days` değişmezi HER ZAMAN
geçerlidir (payda asla sıfır olamaz): pencere bu pattern'in kendi tarihlerinden türer ve
`EpisodeCandidate.observed_at` her zaman kaynak `OSeries.started_at`'a eşittir (bkz.
`awe.episodes.candidates._candidate_from_indices`) — bu `awe.habit.assessment.evaluate_habit`
içinde bir `assert` ile de belgelenir (`selection.selector._ranking_key`'deki
`assert evidence is not None` presedansıyla tutarlı bir stil).

**İki-gün kenar durumu:** kapı tam `distinct_days=2` iken tek bir gap ölçülür; popülasyon
stdev'i (`statistics.pstdev`, `statistics.stdev` DEĞİL) tek örnekte matematiksel olarak 0'dır
(istatistiksel olarak "tanımsız" değil) — bu yüzden `gap_regularity=1.0` özel kod
GEREKTİRMEDEN çıkar. Sonuç: kapıyı az farkla geçen bir örüntü (`two_day_burst`) DAILY
etiketlenir — savunulabilir ama düşük-güven; cadence'in neden bir gate OLMADIĞININ tam
gerekçesi budur. Ayrıca: `min_distinct_days` proje bazında 1'e (veya 0'a) çekilirse
`distinct_days=1` teorik olarak kapıdan geçebilir — bu durumda ölçülebilir hiçbir gap yoktur;
`_gap_statistics` bunu `(0.0, 0.0)` (→ IRREGULAR) döndürerek ele alır, crash etmez.

## 6. Kullanıcı talebiyle yapılan bilinçli tasarım kararı: Selector sıralama sırası

Bölüm 6.15 Selector'ın lexicographic sıralama alanlarını sayar
(`strength, saved_actions, distinct_days, distinct_sessions, occurrence_count, intent_id`)
ama bunların hangi öncelik SIRASIYLA uygulanacağını belirtmez. İlk uygulama belgedeki listeleme
sırasını harfiyen izledi: `saved_actions` (`strength`'ten hemen sonra), `distinct_days` ve
`distinct_sessions`'tan ÖNCE geliyordu.

Gerçekçi (uydurulmamış) bir LearnLoop veri setiyle test edilince bunun somut bir sorun
doğurduğu görüldü: aynı runtime intent'e (aynı `mode`/`destination`/`target`) iki farklı exact
family düşüyordu — biri temiz, 12-occurrence'lık ana yol (`saved_actions=2`), diğeri nadir,
3-occurrence'lık bir "bildirim kontrolü" dolambacı (araya bir adım daha girdiği için
`saved_actions=3`). `saved_actions` önce sıralanınca Selector, 12 kat daha az gözlenen dolambaç
varyantını "kazanan" seçip asıl temsilci alışkanlığı `DEDUPED` ile eliyordu.

Değerlendirilen ve reddedilen alternatifler:

- **Mevcut sırayı koru** — reddedildi: nadir bir path'in tek occurrence'ının tesadüfen bir adım
  fazla tasarruf etmesi, o path'i "temsilci" ilan etmek için zayıf bir gerekçe; Habit
  Evaluator'ın kendisi zaten HABIT_DETECTED kararını `distinct_days`/`distinct_sessions`
  üzerinden veriyor (bölüm 6.7) — sıralamanın bu felsefeyle çelişmesi tutarsız.
- **Deduped family'lerin evidence'ını birleştir** (occurrence/day/session sayılarını topla,
  `saved_actions`'ı ağırlıklı ortalama veya en yaygın path'in değeri yap) — daha "doğru" ama
  Benefit/Habit şu an yalnızca TEK bir family'nin kendi occurrence'larından hesaplanıyor;
  birleştirme, Selector'dan önce ayrı bir evidence-merge adımı gerektirir. Daha büyük bir
  mimari değişiklik olduğu için MVP kapsamında ertelendi.
- **Seçilen: `distinct_days`/`distinct_sessions`'ı `saved_actions`'ın ÖNÜNE al** — sıralama
  anahtarı artık `(-strength, -distinct_days, -distinct_sessions, -saved_actions,
  -occurrence_count, intent_id)`. Evidence/support kazananı belirler; `saved_actions` yalnızca
  eşit destekli adaylar arasında ince ayırıcı (tie-break) olarak kalır. Habit Evaluator'ın
  kendi kapısıyla tutarlı, ek mimari değişiklik gerektirmiyor (bkz.
  `awe.selection.selector._ranking_key`).

## 8. Kullanıcı talebiyle kaldırılan O-Series chunk-bölme kuralı + sınırsız `max_symbols`

O-Series Builder (`awe.series.extraction`), ambiguity barrier'a ek olarak ikinci bir yapısal
kural taşıyordu: `navigation`/`notification`/`deeplink` tetikleyicili bir ACTION, mevcut chunk
zaten en az bir step içeriyorsa ("akışın ortasında" geliyorsa) yeni bir chunk başlatıyordu.
Kullanıcı bunun gerçek davranışları gereksiz parçaladığını belirtti ve kaldırılmasını istedi.

Kaldırmadan önce doğrulanan gerekçe: bu kural, bu dosyadaki BAŞKA hiçbir karar gibi
gerekçelendirilmemişti — kod docstring'i yalnızca mekanik tanım veriyordu, "neden" sorusuna
cevap yoktu (governing spec dosyası zaten repoda mevcut değil, doğrulanamıyor). Daha önemlisi,
bu kural Episode Candidate Builder'ın §1'de belgelenen sıra-korumalı LCS eşleştirmesiyle
çakışıyordu: LCS iki chunk arasındaki araya girmiş alakasız adımları (ör. bir bildirim
kontrolü) zaten tolere ediyor — bu kural ise LCS hiç devreye girmeden, TEK bir session'ın
akışını erkenden ve kabaca ikiye bölerek bu toleransın önüne geçiyordu. Sentetik test
üreticisi (`awe.testing.generators`) bu kuralı hiçbir profilde hiç tetiklemiyordu (trigger hep
`button`) — kaldırmanın doğrulanmış sentetik davranış beklentilerine sıfır etkisi oldu; yalnızca
kuralın kendisini doğrudan test eden 2 dar unit test güncellendi.

Dolaylı bir etki: `awe.screen_evidence.evidence._occurrence_post_view_screen`'in "stabil
post-view ekranı" için ileri tarama penceresi, `BehaviorStep.observation_index`'in yalnızca
chunk-içi bir pozisyon olması nedeniyle zaten dolaylı olarak chunk sınırıyla sınırlıydı. Bu
kuralın kaldırılması bu pencereyi doğal olarak daha cömert hale getirir (chunk'lar artık daha
uzun) — bu, bu oturumda daha önce düzeltilen Screen Transition Evidence penceresi bug'ıyla AYNI
yönde bir etki, yeni bir risk değil.

Aynı kararla birlikte `EpisodeConfig.max_symbols` de kaldırıldı (varsayılan artık `None` /
sınırsız, önceden 8). Teknik gerekçe: `episodes/candidates.py` içindeki LCS araması zaten bu
değere hiç bakmadan chunk'ın TAM sembol dizisi üzerinde çalışıyordu — `max_symbols` yalnızca
bulunan eşleşmenin SONUÇ adayına ne kadarının yazılacağını kırpıyordu, arama maliyetini hiç
etkilemiyordu. Yani sınırı kaldırmak algoritmanın karmaşıklık sınıfını değiştirmez, yalnızca
gerçekten uzun bir alışkanlık bulunduğunda onu eksiksiz kaydetmeyi sağlar. Alan tamamen
silinmek yerine `int | None` yapıldı (silmek yerine `None`): kullanıcının kendi ifadesiyle
sınırsızlık "şuanlık" — ileride bir projede gerekirse `engine_overrides.episode.max_symbols`
ile kod değişikliği olmadan tekrar bir sayı olarak ayarlanabilir. Hiçbir `config_examples/*.yaml`
dosyası bunu hiç override etmiyordu, değişiklik hepsine otomatik yansıdı.

## 10. §8'in dolaylı sonucu: strong pozisyonlar "endpoint hypothesis" olarak ele alınır

§8'deki değişiklik (chunk-bölme kuralının kaldırılması + sınırsız `max_symbols`) doğruydu ama
bir yan etkisi vardı: tek bir `OSeries` chunk artık birbiriyle alakasız birden fazla davranışı
içerebilecek şekilde sınırsız uzunlukta olabiliyor. `episodes/candidates.py`'nin `FULL_CHUNK`
üretimi hâlâ "chunk'ın tamamı = TEK atomik aday" varsayımını koşulsuz yapıyordu. Kod izlenerek
doğrulanmış 8 downstream risk bulundu: Anchor Resolver'ın `AMBIGUOUS` tuzağının çok daha sık
tetiklenmesi (strong pozisyon sonrası saf route/open kuyruk), "en son strong pozisyon kazanır"
sezgisinin bir session'daki İKİNCİ, alakasız bir strong action'ı sessizce görmezden gelmesi,
"bir session = bir amaç" varsayımının artık geçersiz olması, değişken trailing içeriğin aynı
family'yi parçalaması, Target Resolver'ın alakasız iki tekil-hedefli action'ı yanlışlıkla
`VARIABLE_TARGET` (compound identity) sayması, `EpisodeCandidate.final_status`/
`has_shortcut_trigger`'ın alakasız trailing içerikle kirlenmesi.

**Denenip REDDEDİLEN ilk tasarım**: chunk'ı strong pozisyonlarda AYRIK span'lara bölmek (her
strong pozisyon kendinden önceki strong pozisyondan bu yana olan kısmı "sahiplenir"). Bu,
kullanıcı tarafından reddedildi — haklı bir gerekçeyle, iki gerçek veri kaynağına karşı elle
doğrulanmış somut kanıtla: gerçekçi LearnLoop `_PATTERN_A`'da (`open_course(target=X)` hemen
ardından `continue_lesson(AYNI target=X)`, bu projenin 18+ kez tekrarlanan ASIL referans
alışkanlığı) ve sentetik test üreticisinin `_STANDARD_FLOW`'unda (`select_option(target=X)`
hemen ardından `confirm_action`, target'sız) ardışık strong pozisyonlar arasında kesim, gerçek
alışkanlığı temsil eden adımı `min_symbols` altında tek başına bırakıp TAMAMEN kaybediyordu.

**Seçilen tasarım — "endpoint hypothesis"**: strong pozisyonlar span SINIRI değil, bağımsız
"bitiş noktası varsayımı"dır. Her strong pozisyon için, dizinin (ya da eşleşmenin) BAŞINDAN o
pozisyona kadarki önek, ayrı ve ÇAKIŞAN bir aday olarak üretilir; hiçbiri diğerini yutmaz ya da
geçersiz kılmaz. Son strong pozisyondan sonra kalan (kendi içinde strong pozisyonu olmayan bir
kuyruk) varsa, o da ayrı, WEAK-anchor'a uygun bir aday olur:

```python
def _endpoint_hypotheses(indices, steps):
    strong = [i for i in indices if _is_strong_position(steps[i])]
    if not strong:
        return [list(indices)]
    hypotheses = [[i for i in indices if i <= boundary] for boundary in strong]
    remainder = [i for i in indices if i > strong[-1]]
    if remainder:
        hypotheses.append(remainder)
    return hypotheses
```

Kanıt (kind etiketleme için): `len(hypotheses) == 1` ANCAK VE ANCAK sıfır strong pozisyon
varsa geçerlidir (bu durumda hipotez `indices`in birebir kendisidir); aksi halde en az bir
GERÇEK önek üretilir. Bu yüzden `kind = FULL_CHUNK if len(hypotheses) == 1 else EPISODE_SPAN`
eksiksizdir (`grep -rn "EpisodeCandidateKind\."` doğrulaması: bu alan hiçbir yerde downstream
dallanma için kullanılmıyor, etiketleme kararının sıfır davranışsal riski var).

**`COMMON_SUBSEQUENCE` ERTELENMEDİ**: ilk planda ertelenmesi düşünülmüştü ama kullanıcı bunun
yanlış olduğunu gösterdi — `_iterative_common_subsequences`, `series.symbols`in TAM, ham
halinde çalışır ve Anchor Resolver yalnızca `family.symbols`e bakar (hangi candidate türünden
geldiğini hiç bilmez). Yani `FULL_CHUNK` mükemmel düzeltilse bile, aynı "strong + route
kuyruğu" şekli iki session arasında birebir tekrarlarsa (EN SIK rastlanan tekrar biçimi —
iki session'da birebir aynı davranış) `COMMON_SUBSEQUENCE` üzerinden AYNI `AMBIGUOUS` tuzağına
düşmeye devam ederdi. Çözüm: hem `FULL_CHUNK` hem `COMMON_SUBSEQUENCE`, ham indeks listesini
(sırasıyla "chunk'ın tamamı" ve "LCS eşleşmesi") AYNI `_endpoint_hypotheses`'ten geçirir.
`tests/unit/test_episode_candidates.py::test_two_identical_sessions_shaped_strong_then_
route_tail_never_produce_a_combined_candidate` bunun doğrudan kanıtıdır.

**`max_symbols` kırpma yönü**: bir hipotez KENDİ son adımında strong bir pozisyonda bitiyorsa
(önek hipotezi), kırpma BAŞTAN yapılır — bitiş noktası (asıl kanıt) korunur. Bitmiyorsa (sıfır
strong pozisyonlu bütün blok YA DA kuyruk), kırpma SONDAN yapılır — `max_symbols` bu katmana
eklenmeden ÖNCEKİ davranışla birebir aynı.

**Taşınan sabit**: `_OUTCOME_EVIDENCE_EFFECTS`, `awe.planner.anchors`ten (aşama 9)
`awe.domain.enums.OUTCOME_EVIDENCE_EFFECTS` olarak (artık private değil) taşındı —
`awe.episodes.candidates` aşama 4, aşama 9'dan import etmek geriye katman ihlali olurdu.
`ROUTE_OPEN_EFFECTS` bilerek taşınmadı (episodes/candidates.py'ye gerekmiyor).

**Gerçekçi doğrulama** (`scripts/realistic_learnloop_probe.py`, `_PATTERN_A_THEN_CERTIFICATE`
+ `_PATTERN_CERTIFICATE_DIRECT` eklendi): sonuç ÖNCEDEN TAHMİN EDİLMEDEN çalıştırılıp gözlendi.
Bulgular:
- Ana referans alışkanlık (`continue_lesson`/`course_ds301`) TAMAMEN ETKİLENMEDİ — aynı aktif
  öneri (`destination=lesson_player`, `saved=2`), aynı düzeltme öncesi/sonrası. Asıl amaç
  doğrulandı.
- `_PATTERN_A_THEN_CERTIFICATE`'in TAM 5 adımlık öneki (`course_ds301` + `cert_ds301` ikisini
  birden içeren) doğru şekilde `VARIABLE_TARGET` → `UNSUPPORTED_COMPOUND_TARGET` ile reddedildi
  — ne yanlış bir öneri üretti ne bir şeyi bozdu.
- `download_certificate`/`cert_ds301`, KENDİ bağımsız giriş yolundan (`_PATTERN_CERTIFICATE_
  DIRECT`, continue_lesson'dan hiç geçmeden) `HABIT_DETECTED` oldu — iki bağımsız amacın
  gerçekten ayırt edilebildiğinin kanıtı. Bir öneriye DÖNÜŞMEDİ ama bunun nedeni bu turun
  kapsamı dışında: 2 adımlık action-surface bir akışın Benefit formülünde (`planned=2`) hiçbir
  zaman pozitif tasarruf üretememesi (`saved=0`) — segmentasyonla ilgisiz, önceden var olan bir
  mekanik.
- **Beklenmeyen ama geçerli bir bulgu**: segmentasyon, ÖNCEDEN VAR OLAN `_PATTERN_A_NOTIF_
  DETOUR`'u da güçlendirdi — kendi 3 adımlık `open_course` önekini (check_notifications →
  open_my_courses → open_course, `course_ds301`) artık BAĞIMSIZ bir aday olarak üretip
  `HABIT_DETECTED` + CLEAR benefit (`saved=2`, bildirim kontrolü fazladan adım sayıyor)
  yapıyor — bu, ikinci bir aktif öneri (`destination=course_detail`) olarak yüzeye çıkıyor.
  Bu YANLIŞ değil (farklı `destination`, Selector'da asıl öneriyle dedupe olmuyor, ikisi de
  gerçek, geçerli hedefler) ama dikkat çekici: çok daha yaygın (18 occurrence), temiz 2 adımlık
  eşdeğeri (`open_my_courses→open_course`, `fam_ee9fcab62da3`) hâlâ yalnızca LIMITED benefit
  (`saved=1`) taşıyor, hiç öneriye dönüşmüyor — nadir ama fazladan adımlı bir varyantın CLEAR'a
  ulaşıp yaygın, temiz varyantın ulaşamaması, §6'da Selector sıralaması için çözülen dinamiğin
  AYNISI, burada Benefit eşiği seviyesinde. Bu turun kapsamı dışında bırakıldı (Benefit
  formülü/eşiği, bu turun konusu olan segmentasyon tasarımından ayrı, önceden var olan bir
  karar) — kullanıcıya ayrıca raporlandı.

**Açıkça kapsam dışı bırakılan**: sıfır-strong-pozisyonlu chunk'larda (tamamı route/open)
birden fazla ayrı navigasyon-only yolculuğun hâlâ ayırt edilememesi (ör. "ayarlara bak, geri
dön" + tamamen ayrı "katalog gez, geri dön" tek chunk'ta) — hiç strong sinyal yokken hangi
pozisyonların "hipotez" sayılacağına dair bir kıstas yok, bu daha zor ve farklı bir problem,
bilerek gelecek bir tura bırakıldı.

## 11. Kullanıcı talebiyle kaldırılan regularity/support istatistik katmanı (§7'nin geri alınması)

§7'de eklenen `HabitEvidence.cadence`/`mean_gap_days`/`gap_regularity`/`active_days_total`/
`support_ratio`/`status_vector` katmanı, kendi tasarım gerekçesinde de açıkça belirtildiği gibi
("yalnızca kalıcı kanıt vektörüne eklenip görünürlük/gelecekteki kullanım için taşınır") hiçbir
gate'e, Selector sıralamasına ya da API yanıtına hiç bağlanmadı. Suggestion explainability
turunda (`GET .../suggestions/{suggestion_key}/explanation`) yeni bir "neden önerildi" yüzeyi
eklenirken bu fark edildi: kod izlenerek doğrulandı — `selection/selector.py::_ranking_key`
yalnızca `distinct_days`/`distinct_sessions`'a bakıyor (bunlar §7'nin DEĞİL, orijinal hard
gate'in alanları); hiçbir karar mantığı bu altı alana dokunmuyor; `api/schemas.py`/route'larda
hiçbiri geçmiyor; tek tüketicisi kendi round-trip serialization testiydi. Kullanıcı, hiç
kullanılmayacaksa kaldırılmasını istedi.

Kaldırılanlar: `domain/habit.py`'den `StatusVector` sınıfı ve `HabitEvidence`'ın altı alanı
(`HabitEvidence` artık yalnızca `organic_occurrences`/`distinct_sessions`/`distinct_days`/
`first_seen_at`/`last_seen_at` taşıyor — orijinal MVP hard-gate alanları); `domain/enums.py`'den
`HabitCadence`; `config/engine_config.py`'den beş cadence eşiği alanı; `habit/assessment.py`'den
`_gap_statistics`/`_cadence_of`/`_active_days_total` yardımcı fonksiyonları (hesaplama artık
`distinct_sessions`/`distinct_days`/`first_seen_at`/`last_seen_at`'ta duruyor, `status`/gap/
pencere hesabı tamamen kalktı); `persistence/serialization.py`'nin encode/decode'undan ilgili
alanlar. Bu zincirleme olarak `evaluate_habit`'in artık kullanılmayan `all_series` parametresini
de gereksizleştirdi — `services/analysis.py::_evaluate_variant` ve `analyze_subject`'teki çağrı
siteleri buna göre sadeleştirildi (kendi `all_series` yerel değişkeni `series_by_id`/log/episode
inşası için hâlâ gerekli, yalnızca artık `evaluate_habit`'e taşınmıyor).

Test tarafında: `HabitCadence`/`StatusVector`/kaldırılan alanlara özgü sekiz test tamamen
silindi (`test_habit_assessment.py`); iki test kısmen budandı (`support_ratio`/`status_vector`
assertion'ları çıkarıldı, asıl test ettikleri `HABIT_DETECTED`/`distinct_*` assertion'ları
korundu); `test_habit_serialization.py`/`test_selector.py`'deki fixture kurulumları yeni,
sadeleşmiş `HabitEvidence` imzasına göre güncellendi.

§7'nin kendisi silinmedi — o dönemki ekleme gerekçesi (spesifikasyonun kasıtlı olarak boş
bıraktığı bir alanı, kullanıcı talebiyle, hiçbir gate'i etkilemeden doldurma denemesi) tarihsel
kayıt olarak duruyor; bu bölüm yalnızca sonucun (hiç bağlanmadı, kaldırıldı) kaydıdır.
