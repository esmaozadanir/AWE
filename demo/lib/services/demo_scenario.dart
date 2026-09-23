import 'dart:math';

/// Bu dosya, demo/simülasyon amaçlı sahte bir kullanıcı geçmişi üretir ve AWE backend'inin
/// `shopwave` proje konfigürasyonunun (config_examples/shopwave.yaml) beklediği ham event
/// biçimine (eventId/actionKey/target.ref gibi alan adları) uygun JSON event'lere çevirir.
///
/// Dört ayrı davranış deseni üretilir:
/// - "habit": 3 farklı günde, 3 farklı oturumda BİREBİR AYNI akış (motorun
///   min_distinct_sessions=3 / min_distinct_days=2 eşiğini geçip önerilmesi için).
/// - "mixed": 3 farklı günde, 3 farklı oturumda ama HER SEFERİNDE FARKLI bir yoldan (farklı
///   giriş noktası, farklı ara adımlar) yapılan bir akış -- yalnızca 2 adımlık bir alt diziyi
///   (ortak "common subsequence") paylaşıyorlar. Motor bunu da alışkanlık olarak tespit
///   ediyor, ama az adım kısalttığı için öneriye dönüşmüyor -- "karışık ama aynı amaca giden
///   session'lardan alışkanlık bulma" senaryosunun kanıtı.
/// - "occasional": yalnızca 2 oturumda görülen bir akış (eşiği geçemez, "yetersiz kanıt").
/// - "one_off": yalnızca 1 kez görülen bir akış (en zayıf kanıt).
class DemoScenario {
  static const String projectId = 'shopwave';

  final String subjectId;
  final DateTime anchorTime;
  final Random _random;

  DemoScenario({String? subjectId, DateTime? anchorTime})
    : subjectId = subjectId ?? _randomSubjectId(),
      anchorTime = anchorTime ?? DateTime.now().toUtc(),
      _random = Random();

  static String _randomSubjectId() {
    final rand = Random();
    final suffix =
        List.generate(8, (_) => rand.nextInt(16).toRadixString(16)).join();
    return 'flutter_demo_$suffix';
  }

  Map<String, dynamic> _rawEvent({
    required String eventId,
    required String sessionId,
    required DateTime timestamp,
    required String action,
    required String effect,
    required String screen,
    String trigger = 'button',
    String? target,
  }) {
    return {
      'eventId': eventId,
      'projectId': projectId,
      'subjectId': subjectId,
      'sessionId': sessionId,
      'timestamp': timestamp.toUtc().toIso8601String(),
      'actionKey': action,
      'effect': effect,
      'trigger': trigger,
      'source': 'client',
      'screen': screen,
      // Nested object her zaman gönderilir: {"ref": null} == "hedef açıkça yok",
      // ham "target": null ise backend bunu "hedef verisi hiç gönderilmedi" sayıp
      // UNKNOWN_TARGET olarak işaretler (bkz. awe.adapter.observation_builder._resolve_target).
      'target': {'ref': target},
      'status': 'success',
      'durationMs': 400 + _random.nextInt(400),
    };
  }

  Map<String, dynamic> _viewEvent({
    required String eventId,
    required String sessionId,
    required DateTime timestamp,
    required String screen,
  }) {
    return _rawEvent(
      eventId: eventId,
      sessionId: sessionId,
      timestamp: timestamp,
      action: 'view_$screen',
      effect: 'view',
      screen: screen,
      trigger: 'automatic',
    );
  }

  /// Tüm senaryonun event listesini üretir.
  List<Map<String, dynamic>> buildEvents() {
    final events = <Map<String, dynamic>>[];

    // Alışkanlık deseni: home -> kategori -> ürün listesi -> sepet, 3 gün üst üste.
    for (var day = 2; day >= 0; day--) {
      final sessionId = '$subjectId-habit-sess-${2 - day}';
      final base = anchorTime.subtract(Duration(days: day, hours: 1));
      events.addAll([
        _rawEvent(
          eventId: '$subjectId-habit-$day-1',
          sessionId: sessionId,
          timestamp: base,
          action: 'open_category',
          effect: 'route',
          screen: 'home',
        ),
        _viewEvent(
          eventId: '$subjectId-habit-$day-2',
          sessionId: sessionId,
          timestamp: base.add(const Duration(minutes: 1)),
          screen: 'category',
        ),
        _rawEvent(
          eventId: '$subjectId-habit-$day-3',
          sessionId: sessionId,
          timestamp: base.add(const Duration(minutes: 2)),
          action: 'open_product_list',
          effect: 'route',
          screen: 'category',
        ),
        _viewEvent(
          eventId: '$subjectId-habit-$day-4',
          sessionId: sessionId,
          timestamp: base.add(const Duration(minutes: 3)),
          screen: 'product_list',
        ),
        _rawEvent(
          eventId: '$subjectId-habit-$day-5',
          sessionId: sessionId,
          timestamp: base.add(const Duration(minutes: 4)),
          action: 'open_cart',
          effect: 'open',
          screen: 'product_list',
        ),
        _viewEvent(
          eventId: '$subjectId-habit-$day-6',
          sessionId: sessionId,
          timestamp: base.add(const Duration(minutes: 5)),
          screen: 'cart',
        ),
      ]);
    }

    // Karışık ama aynı amaca giden desen: her oturumda FARKLI bir yol izleniyor (farklı
    // giriş noktası, farklı ara adımlar) ama üçü de aynı 2 adımlık alt diziyi ("ürün
    // listesini aç" -> "sepete git") aynı sırayla paylaşıyor. Motor bunu, oturumların TAM
    // eşleşmesine değil ortak alt diziye (common subsequence) bakarak buluyor -- bu yüzden
    // "Önerilmeyenler" sekmesinde "Alışkanlık tespit edildi" olarak görünecek (motor deseni
    // gerçekten buldu) ama çok az adım kısalttığı için öneriye dönüşmüyor.
    {
      final base0 = anchorTime.subtract(const Duration(days: 2, hours: 6));
      final s0 = '$subjectId-mixed-sess-0';
      events.addAll([
        _rawEvent(
          eventId: '$subjectId-mixed-0-1',
          sessionId: s0,
          timestamp: base0,
          action: 'open_category',
          effect: 'route',
          screen: 'home',
        ),
        _viewEvent(
          eventId: '$subjectId-mixed-0-2',
          sessionId: s0,
          timestamp: base0.add(const Duration(minutes: 1)),
          screen: 'category',
        ),
        _rawEvent(
          eventId: '$subjectId-mixed-0-3',
          sessionId: s0,
          timestamp: base0.add(const Duration(minutes: 2)),
          action: 'open_product_list',
          effect: 'route',
          screen: 'category',
        ),
        _rawEvent(
          eventId: '$subjectId-mixed-0-4',
          sessionId: s0,
          timestamp: base0.add(const Duration(minutes: 3)),
          action: 'apply_filter',
          effect: 'filter',
          screen: 'product_list',
        ),
        _rawEvent(
          eventId: '$subjectId-mixed-0-5',
          sessionId: s0,
          timestamp: base0.add(const Duration(minutes: 4)),
          action: 'open_cart',
          effect: 'open',
          screen: 'product_list',
        ),
      ]);

      final base1 = anchorTime.subtract(const Duration(days: 1, hours: 6));
      final s1 = '$subjectId-mixed-sess-1';
      events.addAll([
        _rawEvent(
          eventId: '$subjectId-mixed-1-1',
          sessionId: s1,
          timestamp: base1,
          action: 'open_search',
          effect: 'route',
          screen: 'home',
        ),
        _viewEvent(
          eventId: '$subjectId-mixed-1-2',
          sessionId: s1,
          timestamp: base1.add(const Duration(minutes: 1)),
          screen: 'search_results',
        ),
        _rawEvent(
          eventId: '$subjectId-mixed-1-3',
          sessionId: s1,
          timestamp: base1.add(const Duration(minutes: 2)),
          action: 'tap_suggested_item',
          effect: 'select',
          screen: 'search_results',
        ),
        _rawEvent(
          eventId: '$subjectId-mixed-1-4',
          sessionId: s1,
          timestamp: base1.add(const Duration(minutes: 3)),
          action: 'open_product_list',
          effect: 'route',
          screen: 'category',
        ),
        _rawEvent(
          eventId: '$subjectId-mixed-1-5',
          sessionId: s1,
          timestamp: base1.add(const Duration(minutes: 4)),
          action: 'open_cart',
          effect: 'open',
          screen: 'product_list',
        ),
      ]);

      final base2 = anchorTime.subtract(const Duration(hours: 6));
      final s2 = '$subjectId-mixed-sess-2';
      events.addAll([
        _rawEvent(
          eventId: '$subjectId-mixed-2-1',
          sessionId: s2,
          timestamp: base2,
          action: 'open_category',
          effect: 'route',
          screen: 'home',
        ),
        _rawEvent(
          eventId: '$subjectId-mixed-2-2',
          sessionId: s2,
          timestamp: base2.add(const Duration(minutes: 1)),
          action: 'browse_deals',
          effect: 'select',
          screen: 'category',
        ),
        _rawEvent(
          eventId: '$subjectId-mixed-2-3',
          sessionId: s2,
          timestamp: base2.add(const Duration(minutes: 2)),
          action: 'open_product_list',
          effect: 'route',
          screen: 'category',
        ),
        _rawEvent(
          eventId: '$subjectId-mixed-2-4',
          sessionId: s2,
          timestamp: base2.add(const Duration(minutes: 3)),
          action: 'sort_by_price',
          effect: 'sort',
          screen: 'product_list',
        ),
        _rawEvent(
          eventId: '$subjectId-mixed-2-5',
          sessionId: s2,
          timestamp: base2.add(const Duration(minutes: 4)),
          action: 'open_cart',
          effect: 'open',
          screen: 'product_list',
        ),
        _viewEvent(
          eventId: '$subjectId-mixed-2-6',
          sessionId: s2,
          timestamp: base2.add(const Duration(minutes: 5)),
          screen: 'cart',
        ),
      ]);
    }

    // Ara sıra görülen desen: yalnızca 2 oturum -> eşiği (3) geçemez.
    for (var day = 1; day >= 0; day--) {
      final sessionId = '$subjectId-occasional-sess-${1 - day}';
      final base = anchorTime.subtract(Duration(days: day, hours: 3));
      events.addAll([
        _rawEvent(
          eventId: '$subjectId-occ-$day-1',
          sessionId: sessionId,
          timestamp: base,
          action: 'open_wishlist',
          effect: 'route',
          screen: 'home',
        ),
        _viewEvent(
          eventId: '$subjectId-occ-$day-2',
          sessionId: sessionId,
          timestamp: base.add(const Duration(minutes: 1)),
          screen: 'wishlist',
        ),
        _rawEvent(
          eventId: '$subjectId-occ-$day-3',
          sessionId: sessionId,
          timestamp: base.add(const Duration(minutes: 2)),
          action: 'remove_from_wishlist',
          effect: 'delete',
          screen: 'wishlist',
        ),
      ]);
    }

    // Tek seferlik desen: yalnızca 1 oturum -> en zayıf kanıt.
    {
      const sessionId2 = 'oneoff-sess';
      final sessionId = '$subjectId-$sessionId2';
      final base = anchorTime.subtract(const Duration(hours: 5));
      events.addAll([
        _rawEvent(
          eventId: '$subjectId-oneoff-1',
          sessionId: sessionId,
          timestamp: base,
          action: 'open_support_chat',
          effect: 'route',
          screen: 'home',
        ),
        _viewEvent(
          eventId: '$subjectId-oneoff-2',
          sessionId: sessionId,
          timestamp: base.add(const Duration(minutes: 1)),
          screen: 'support_chat',
        ),
        _rawEvent(
          eventId: '$subjectId-oneoff-3',
          sessionId: sessionId,
          timestamp: base.add(const Duration(minutes: 2)),
          action: 'send_message',
          effect: 'submit',
          screen: 'support_chat',
        ),
      ]);
    }

    return events;
  }
}
