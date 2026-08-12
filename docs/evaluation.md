# Test ve Değerlendirme Raporu

Bu doküman iki şeyi bir arada raporlar: test paketinin kapsamı ve `scripts/evaluate_engine.py`
ile alınan büyük ölçekli sentetik değerlendirme sonucu. İkisi de motorun kendi tasarım
kurallarına uyduğunu gösterir; gerçek üretim precision/recall veya kullanıcı kabul oranı
kanıtı **değildir**.

## 1. Test paketi

135 test, `pytest tests/ -q` ile tamamı yeşil:

| Kategori | Dosyalar | Odak |
|---|---|---|
| `tests/unit/` (90 test) | `test_event_classification`, `test_series_extraction`, `test_episode_candidates`, `test_family_matching`, `test_target_resolver`, `test_habit_assessment`, `test_planner`, `test_risk`, `test_benefit`, `test_selector` | Her katmanın kendi kararı — bölüm 6.2-6.15'in worked example'ları ve MVP kuralları birebir doğrulanır |
| `tests/scenarios/` (20 test) | `test_clean_action_flow`, `test_data_quality`, `test_domain_universality`, `test_habit_profiles` (17 profil), `test_end_to_end_selection` | Adapter'dan Selector'a gerçek servis katmanından (mock'suz) uçtan uca akış; bölüm 7'nin K1→K2→K3 worked example'ı `test_end_to_end_selection.py`'de birebir doğrulanır |
| `tests/property/` (3 test, hypothesis) | `test_family_invariants` | Exact-match gruplamasının girdi sırasından bağımsızlığı ve exact eşitlik garantisi |
| `tests/regression/` (5 test) | `test_adversarial_edge_cases` | Aynı timestamp'te çoklu ACTION, çakışan event gövdesi (conflict quarantine), yüksek tekrarlı retry'ların çökmemesi |
| `tests/integration/` (5 test) | `test_api_http` | Gerçek FastAPI + gerçek `config_examples/shopwave.yaml` üzerinden ingest → analyze → suggestions → dismiss |

Doğrulama komutları: `ruff format . && ruff check .` (temiz), `mypy src` (68 dosya, hatasız),
`pytest tests/ -q` (135/135).

## 2. Büyük ölçekli sentetik değerlendirme

```text
python scripts/evaluate_engine.py --subjects-per-profile 6 --multi-habit-subjects 10
```

`--subjects-per-profile 3 --multi-habit-subjects 3` ile alınan bir örnek çalıştırma
(17 profil × 3 + 3 multi-habit = 54 subject, 6447 event):

```text
Habit Classification (positive class = HABIT_DETECTED)
TP=45 FP=0 FN=0 TN=6
precision=1.0  recall=1.0  f1=1.0

Per-profile: 17/17 profil, tamamı 3/3 doğru
Multi-habit: 3/3 subject beklenen habit sayısını üretti
Failure buckets: none
```

Bu, sentetik üreticinin kendi ground-truth beklentisiyle motorun kendi mental modelini
karşılaştırır — motorun kendi tasarım kurallarına uyduğunu gösterir, bağımsız/gerçek dünya
doğrulaması değildir.

### Bilinçli bir gözlem: `shortcut_intents_evaluated_total: 0`

Aynı çalıştırmada `engine_health.shortcut_intents_evaluated_total` **0**'dır — Habit tespit
edilen 63 target variant'ın hiçbiri bir `READY` Shortcut Intent üretmedi. Kök neden bir motor
hatası değil, `awe.testing.generators`'ın akışlarıdır: `_STANDARD_FLOW`/`_LONG_FLOW`, anchor'dan
ÖNCE bir `select`/`input` adımı içerir (ör. `open_dashboard → open_detail → select_option →
confirm_action`). Bölüm 6.12'nin "Anchor'dan önceki ara effect'ler yalnız route/open olabilir"
kuralı bu yüzden her occurrence'ı `UNSUPPORTED` (`UNREPRESENTED_INTERMEDIATE_ACTION`) yapar —
bu, motorun "sahte kısayol üretmeme" garantisinin doğru çalıştığının bir kanıtıdır, ama bu
sentetik akışlar Habit-tespiti senaryolarını (motorun eski tasarımdan devralınan asıl amacı)
test etmek için tasarlanmıştı, shortcut-intent üretimini değil. Shortcut Intent/Risk/Benefit/
Selector'ın gerçek `READY` yolu ayrı, adanmış testlerle doğrulanır: `tests/unit/test_planner.py`,
`test_risk.py`, `test_benefit.py`, `test_selector.py`, ve tam pipeline üzerinden
`tests/scenarios/test_end_to_end_selection.py`. Sentetik üreticinin akışlarını da shortcut-
uygun hale getirmek (ör. anchor'dan önce yalnız route/open adımları bırakmak) bu değerlendirme
scriptinin kapsamını Habit-doğruluğunun ötesine genişletir; şimdilik bilinçli olarak
yapılmamıştır.
