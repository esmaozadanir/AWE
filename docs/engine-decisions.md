# Motor Tasarım Kararları

Bu doküman, kod okunduğunda hemen belli olmayan tasarım kararlarının gerekçelerini toplar.
Özellikle spesifikasyonun (`AWE_MVP_TASARIMI_BAGIMSIZ_INCELEME.md`) açıkça bırakmadığı boşlukları
nasıl doldurduğumuzu ve önceki tasarımdan bilinçli olarak nerede ayrıldığımızı belgeler.

## 1. Önceki tasarıma göre bilinçli tersine dönüşler

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

## 2. Spesifikasyonun boş bıraktığı, burada doldurulan noktalar

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

## 3. Eski tasarımdan kalan, artık anlamsızlaşan kavramların kaldırılması

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

## 4. Korunan altyapı (spesifikasyonun ele almadığı alanlar)

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
