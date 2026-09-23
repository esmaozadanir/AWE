class PatternStep {
  final String action;
  final String effect;
  final String? screen;

  const PatternStep({required this.action, required this.effect, this.screen});

  factory PatternStep.fromJson(Map<String, dynamic> json) {
    return PatternStep(
      action: json['action'] as String,
      effect: json['effect'] as String,
      screen: json['screen'] as String?,
    );
  }
}

class VariantPattern {
  final String variantKey;
  final String familyKey;
  final List<PatternStep> pattern;
  final String decision;
  final List<String> reasonCodes;
  final bool recommended;
  final String? suggestionState;
  final int? repeatCount;
  final int? distinctDays;
  final String? mode;
  final String? destinationScreen;
  final String? target;
  final int? savedSteps;

  const VariantPattern({
    required this.variantKey,
    required this.familyKey,
    required this.pattern,
    required this.decision,
    required this.reasonCodes,
    required this.recommended,
    this.suggestionState,
    this.repeatCount,
    this.distinctDays,
    this.mode,
    this.destinationScreen,
    this.target,
    this.savedSteps,
  });

  factory VariantPattern.fromJson(Map<String, dynamic> json) {
    return VariantPattern(
      variantKey: json['variant_key'] as String,
      familyKey: json['family_key'] as String,
      pattern: (json['pattern'] as List<dynamic>)
          .map((e) => PatternStep.fromJson(e as Map<String, dynamic>))
          .toList(),
      decision: json['decision'] as String,
      reasonCodes: (json['reason_codes'] as List<dynamic>).map((e) => e as String).toList(),
      recommended: json['recommended'] as bool,
      suggestionState: json['suggestion_state'] as String?,
      repeatCount: json['repeat_count'] as int?,
      distinctDays: json['distinct_days'] as int?,
      mode: json['mode'] as String?,
      destinationScreen: json['destination_screen'] as String?,
      target: json['target'] as String?,
      savedSteps: json['saved_steps'] as int?,
    );
  }
}

/// Backend'in bilinen ReasonCode değerleri için okunabilir Türkçe açıklama.
/// Motorun ReasonCode enum'unda (awe.domain.enums) tanımlı olmayan bir değer gelirse
/// olduğu gibi (ham kod) gösterilir.
const Map<String, String> reasonCodeExplanations = {
  'insufficient_occurrences': 'Yeterli sayıda tekrar gözlenmedi',
  'insufficient_distinct_sessions': 'Farklı oturumlarda yeterince tekrarlanmadı',
  'insufficient_distinct_days': 'Farklı günlerde yeterince tekrarlanmadı',
  'stale_behavior': 'Bu davranış uzun süredir gözlenmiyor',
  'attempt_only': 'Yalnızca girişim var, tamamlanmış bir akış değil',
  'ambiguous_anchor': 'Akışın hangi adımda "çıpalandığı" belirsiz',
  'unknown_target_blocks_anchor': 'Hedef bilgisi eksik olduğu için çıpa çözülemedi',
  'unsupported_compound_target': 'Birden fazla farklı hedefe değinen bir akış, desteklenmiyor',
  'unrepresented_intermediate_action': 'Ara adımlardan biri kısayolda temsil edilemiyor',
  'destination_unresolved': 'Gidilecek ekran belirlenemedi',
  'execute_blocked_effect': 'Bu etki türü için otomatik işlem güvenlik nedeniyle engellendi',
  'unknown_effect': 'Adımın etkisi tanımlanamadı',
  'critical_quality_flag': 'Veri kalitesi bu öneri için yetersiz',
  'unknown_anchor_status': 'Çıpa durumu belirlenemedi',
  'mixed_observed_outcomes': 'Geçmiş denemelerde karışık sonuçlar (başarısız/iptal) var',
  'resolver_unsupported': 'Bu akış türü için hedef çözümü desteklenmiyor',
  'benefit_too_low': 'Kısayol kullanıcıya yeterince adım kazandırmıyor',
  'duplicate_plan': 'Aynı öneri zaten başka bir varyantla üretiliyor',
  'dominated_plan': 'Daha güçlü bir öneri bu adayın önüne geçti',
  'no_plan_candidate': 'Bu varyant için henüz bir kısayol planı üretilmedi',
};

String explainReasonCode(String code) => reasonCodeExplanations[code] ?? code;
