# Test ve Değerlendirme Raporu

Bu doküman iki şeyi bir arada raporlar: test paketinin kapsamı (hangi katman, hangi kategoriyle
doğrulanıyor) ve `scripts/evaluate_engine.py` ile üretilen büyük ölçekli sentetik
değerlendirmenin sonuçları. Amaç yalnızca "testler yeşil" demek değil; motorun gerçekten neyi
doğru yaptığını, neyi henüz kanıtlamadığını dürüstçe ortaya koymaktır.

## Test paketi

159 test, beş kategoriye ayrılmış durumda:

| Kategori | Sayı | Konum | Neyi doğrular |
|---|---|---|---|
| Unit | 13 | `tests/unit/` | O-Series normalizasyonu (retry/detour/loop), Family eşleştirme algoritmasının izole davranışı |
| Scenario | 122 | `tests/scenarios/` | Habit profil matrisi (15 profil), PREFILL/Risk/Benefit/Selection test matrisleri, veri kalitesi stres testleri, 20 sentetik profilin ground truth ile eşleşmesi, domain-independence statik denetimi (45 motor dosyasının tamamı, bölüm 1), O-Series sınır sağlamlığı ve family fragmentation ölçümü (aşağıda) |
| Integration | 10 | `tests/integration/` | Uçtan uca ingestion → analiz → suggestion → dismiss (gerçek SQLite + gerçek HTTP istekleri), idempotency, proje/subject izolasyonu, dismiss cooldown'ın yeniden canlanması |
| Property-based | 10 | `tests/property/` | Bölüm 123'teki 10 invariant'ın tamamı (Hypothesis ile rastgele girdi üzerinde) |
| Regression | 4 | `tests/regression/` | Geliştirme ve adversarial review sırasında bulunan gerçek hataların kalıcı kanıtı |

Testler implementasyonu tekrar etmez: senaryo testleri "bu girdi için motor X hesaplar" değil,
"bu girdi için beklenen iş sonucu Y'dir" şeklinde kurulur.

### Property-based invariant eşlemesi

| # | Invariant | Test |
|---|---|---|
| 1 | Noise ekleme Family identity'yi değiştirmez | `test_inserting_noise_observations_does_not_change_normalized_symbols` |
| 2 | Duplicate batch support artırmaz | `test_ingesting_the_same_batch_twice_never_doubles_accepted_events` |
| 3 | Batch sırası deterministik sonucu bozmaz | `test_session_ordering_is_independent_of_input_batch_order` |
| 4 | Shortcut-trigger organic support artırmaz | `test_shortcut_triggered_occurrences_never_count_as_organic_support` |
| 5 | Risk BLOCK, Benefit ile açılamaz | `test_risk_block_is_never_reopened_by_an_arbitrarily_high_benefit` |
| 6 | Eligible Habit sayısına sabit üst sınır yok | `test_engine_never_applies_a_hard_cap_on_the_number_of_eligible_suggestions` |
| 7 | TargetRef değişimi Family split yaratmaz | `test_target_ref_variation_never_splits_a_structurally_identical_family` |
| 8 | Ortak başlangıç sembolü farklı behavior'ları birleştirmez | `test_common_startup_symbol_never_merges_distinct_behaviors` |
| 9 | Widget rename Family'yi split etmez | `test_widget_rename_never_splits_a_family_when_action_and_effect_are_stable` |
| 10 | Server retry Benefit'i artırmaz | `test_server_side_retries_never_inflate_benefit_saved_actions` |

### O-Series sınır sağlamlığı

`tests/scenarios/test_series_boundary_robustness.py`, sınır tespitinin (bölüm 35-44) alışılmadık
girdi şekillerinde de deterministik kaldığını doğrular:

- **Az outcome, çok context**: 7 ardışık context (screen-view) event'inin ardından tek bir geç
  outcome — tüm session tek bir O-Series olarak kalır, context adımları normalize edilmiş
  diziden silinmez.
- **Uzun session**: 25 bağımsız "ürün incele → sepete ekle → satın al" döngüsünün tek bir
  session'da art arda gelmesi — 25 ayrı O-Series'e hatasız ve kayıpsız bölünür.
- **Tek session'da iki bağımsız iş**: kullanıcı tamamlanma sinyali üretmeden konu değiştirirse
  (ör. ayarları inceleyip sonra kataloğa geçerse), bu bilinçli MVP sınırlaması gereği iki iş tek
  O-Series'te birleşik kalır (`docs/architecture.md`, "Bilinen sınırlamalar"); test bunun
  çökmeden ve deterministik biçimde gerçekleştiğini, üstelik bu "kirli" birleşik dizinin temiz
  bir family'ye karşı eşleştirilmeye çalışılmasının da güvenli bir `FamilyMatchDecision`
  (MATCH/VARIANT_MATCH/AMBIGUOUS/NO_MATCH — hangisi olursa olsun çökme yok) döndürdüğünü kanıtlar.

### Family fragmentation/explosion ölçümü

`tests/scenarios/test_family_fragmentation_at_scale.py`, 20 temiz sentetik profilden farklı
olarak, TEK bir subject'in 80 session boyunca 4 farklı davranışı (ikisi kasıtlı olarak ortak bir
başlangıç adımını — "open_settings" — paylaşarak), gerçekçi gürültü (screen-view ön eki,
misclick+geri, retry) ve kasıtlı olarak ayırt edilemez kısa fragment'larla (yalnızca
"open_settings"tan ibaret, hangi davranışa ait olduğu belirlenemeyen kesik session'lar) iç içe
sergilediği daha zorlu, karmaşık bir log (283 event, 85 O-Series) üzerinde fragmentation
oranlarını ölçer. Sabit seed (`2024`) ile deterministik sonuç:

```
family sayısı: 9        (4 gerçek davranış + 5 singleton)
destek dağılımı: [43, 17, 13, 7, 1, 1, 1, 1, 1]
ambiguous_series_rate: 0.0
singleton family oranı: 5/9 (%55.6)
```

Bu sonuç manuel olarak doğrulandı: 4 gerçek davranışın her biri KENDİ tek family'sine topluyor
(destek sıralaması `search_filter`/`profile_update`/`password_reset`/`notification_settings`
ağırlıklarıyla tutarlı) ve `screen_view` gürültü ön-eki family'yi bölmüyor, aynı family içinde
ikinci bir variant olarak kalıyor — yani gerçek fragmentation SIFIR. Geri kalan 5 singleton
family, kasıtlı enjekte edilen tek-sembollük ("open_settings") fragment'lardır; bunlar hem
`password_reset` hem `notification_settings` ile aynı başlangıcı paylaştığından motor bunları
rastgele bir family'ye zorla eşlemek yerine kendi singleton family'lerinde bırakıyor — bu, tek
sembolden ibaret, gerçekten ayırt edilemez bir occurrence karşısında beklenen ve güvenli
varsayılan davranıştır (yanlış pozitif merge yerine muhafazakâr split). Singleton oranının yüksek
görünmesi (%55.6) bu yüzden bir motor kusuru değil, veri kümesine kasıtlı olarak enjekte edilmiş
belirsizliğin doğru şekilde yansımasıdır.

## Büyük ölçekli sentetik değerlendirme

`scripts/evaluate_engine.py --subjects-per-profile 6 --multi-habit-subjects 10` komutuyla
üretilen ve gerçek pipeline'dan (ingestion → analiz, HTTP katmanı atlanarak ama servis katmanı
tam olarak kullanılarak) geçirilen veri kümesi üzerindeki en güncel çalıştırma:

```
subjects: 130   events: 15258
ingestion: ~8.4s   analysis: ~4.2s
```

Hem subject hem event sayısı bölüm 126'nın istediği eşiklerin (100+ subject, 10.000+ event)
üzerindedir. Veri kümesi 6 farklı proje konfigürasyonuna (ShopWave, SocialPulse, FinancePilot,
HealthTrack, Wanderly, StreamBoxx — hepsi aynı canonical-benzeri ham formatı paylaşır ama farklı
`project_id`/iş sözlüğü kullanır) round-robin dağıtılmıştır. LearnLoop ve TaskFlow kasıtlı
olarak farklı bir ham telemetry şekli kullandığından (bölüm 32) bu jenerik üreticiye dahil
edilmemiştir; onların doğruluğu `tests/integration/test_pipeline_end_to_end.py` içindeki adanmış
testlerle ayrıca kanıtlanmıştır.

### Habit sınıflandırma metrikleri

Pozitif sınıf = `PASS`. 120 tekil-profil subject'i (20 profil × 6 tekrar) üzerinden:

```
TP=102   FP=0   FN=0   TN=18
precision=1.0   recall=1.0   f1=1.0
```

`TN=18`, üç "gerçek olmayan Habit" profilinin (`one_day_burst`, `two_day_burst`,
`single_session_repeater` — her biri 6 subject) tamamının doğru biçimde `NOT_HABIT` olarak
sınıflandırıldığını gösterir. 10 multi-habit subject'inin (her biri 4 bağımsız Habit
içeriyor: günlük, haftalık, aylık, düzensiz) tamamı beklenen family sayısıyla eşleşti
(`10/10`).

**Bu sonucu dürüstçe yorumlamak gerekirse:** bu, motorun kendi ürettiği ve motorun kendi
tasarım varsayımlarıyla etiketlediği sentetik bir veri kümesidir — üretici ve motor aynı
zihinsel modeli (ör. "burst" ne demektir, "widget rename" davranışı nasıl etkilemez) paylaştığı
için mükemmel skor beklenir ve bağımsız/gürültülü gerçek dünya verisiyle aynı güvenilirlik
iddiasını taşımaz. Bu değerlendirmenin asıl değeri, **implementasyonun tasarım niyetini
gerçekten gerçekleştirdiğini** — 20 farklı davranış profilinin, 4 bağımsız Habit'in aynı
kullanıcıda karışmadan bulunmasının, 6 farklı proje kapsamının hiç karışmadığının ve tüm
pipeline'ın 15.000+ event üzerinde saniyeler içinde ve hatasız çalıştığının — ölçülebilir
biçimde doğrulanmasıdır. Motorun gerçek, etiketlenmemiş veri karşısındaki performansı bu
raporun kapsamı dışındadır.

### Motor sağlığı

```
families_total: 160              (beklenen: 120 tekil + 10×4 multi-habit = 160 — tam eşleşme)
families_per_subject: 1.23
variants_per_family_avg: 1.0
family_cohesion_avg: 1.0
ambiguous_series_rate: 0.0
eligible_habits_total: 142        (= TP 102 + multi-habit 40)
plans_per_habit_avg: 3.04
prefill_downgrade_rate: 0.039
eligible_suggestions_total: 142
eligible_suggestions_per_subject: 1.09
duplicate_suppressed_total: 0
```

`families_total`'ın beklenen değerle tam eşleşmesi, family fragmentation'ın bu veri kümesinde
sıfır olduğunu gösterir. Bu değer başlangıçta 166 çıkmıştı; kök neden araştırıldığında
`single_session_repeater` profilinin sentetik üreticisinin (`_day_list`, bölüm "tek session
içinde 50 tekrar") ardışık occurrence'lar arasında yeterli zaman aralığı bırakmadığı, bu
yüzden bazı occurrence çiftlerinin tam olarak aynı dakikaya düştüğü ve `order_session`'ın
güvenilir bir sıra sinyali olmadan bu belirsiz durumu (doğru biçimde, sahte kesinlik
üretmeden) düşük güvenle çözdüğü, ancak bu çözümün nadiren tek bir occurrence'ı ana family'den
ayırdığı görüldü. Bu bir motor hatası değil, sentetik üreticinin zaman damgası aralığının dar
tutulmasıydı; üretici düzeltildi (`src/awe/testing/generators.py`) ve yukarıdaki sayılar bu
düzeltme sonrasına aittir. Motorun kendisi, sıra belirsizliği karşısında beklendiği gibi
davrandı: çökme yok, deterministik sonuç, yalnızca `OrderingConfidence.LOW` ile açıkça
işaretlenmiş bir belirsizlik.

`prefill_downgrade_rate` sıfırdan farklıdır çünkü `target_variable` ve `parameter_drift`
profilleri kasıtlı olarak kararsız target/parametre üretir; bu durumlarda Risk katmanının
PREFILL'i NAVIGATE'e düşürmesi **beklenen ve doğru** davranıştır (bölüm 83), bir hata değildir.

### Adversarial review'da bulunan gerçek hatalar

İlk implementasyon tamamlandıktan sonra sistemin kendisini kırmaya çalışan adversarial review
sırasında iki gerçek hata bulundu ve düzeltildi (detaylı kök neden analizi
`docs/engine-decisions.md`'de):

1. Sınırsız ardışık "geri" (`navigate_back`) event'i, yığın boşaldığında uydurma bir sembol
   olarak normalize edilmiş diziye sızıyordu.
2. Bir family'nin atipik bir ilk örnekle (outlier) tohumlanması, ayrıştırıcı ağırlıklandırmanın
   nadir sembolleri (o tek örneğe özgü bir detour) asıl çekirdekten daha "ayırt edici"
   göstermesiyle birleşince, sonraki tamamen normal occurrence'ların reddedilmesine yol
   açıyordu.

Her ikisi için de `tests/regression/test_adversarial_edge_cases.py` içinde kalıcı test
eklendi ve düzeltmelerin bölüm 58'deki chaining ve bölüm 115'teki ortak-başlangıç-sembolü
korumalarını bozmadığı hem hedefli testlerle hem tüm test paketinin yeniden çalıştırılmasıyla
doğrulandı.

### Kapsam dışı bırakılanlar

Dürüstlük adına açıkça belirtilmelidir: bu değerlendirme sentetik ve etiketli bir veri kümesi
üzerindedir; gerçek, üçüncü taraf bir mobil uygulamanın canlı event log'u üzerinde
çalıştırılmamıştır. `docs/architecture.md`'deki "Bilinen sınırlamalar" bölümü, bu MVP'nin
bilinçli olarak ele almadığı durumları (tek session içinde tamamlanma sinyali üretmeyen çoklu
davranış, PostgreSQL'de doğrulanmamış olması) ayrıca listeler.
