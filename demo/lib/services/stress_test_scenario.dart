import 'dart:convert';

import 'package:flutter/services.dart' show rootBundle;

/// `AWE/scripts/engine_stress_test.py`nin ürettiği hazır event log'unu (learnloop projesi,
/// tek bir kullanıcının ~10 haftalık geçmişi) uygulama içine gömülü asset olarak yükler.
/// Bu betiğin amacı motoru "uydurmadan", canlı log'lara benzeyen geniş bir davranış
/// çeşitliliğiyle (paralel bağımsız alışkanlıklar, yapısal olarak asla alışkanlık
/// sayılamayacak değişken hedefli davranışlar, çakışan timestamp'ler, eksik target alanı,
/// double-tap tekrarları, uzun çok-amaçlı session) stres testine tabi tutmaktır.
class StressTestScenario {
  static const String projectId = 'learnloop';
  static const String subjectId = 'learner_512';
  static const String _assetPath = 'assets/engine_stress_test_events.json';

  Future<List<Map<String, dynamic>>> loadEvents() async {
    final raw = await rootBundle.loadString(_assetPath);
    final decoded = jsonDecode(raw) as List<dynamic>;
    return decoded.cast<Map<String, dynamic>>();
  }
}
