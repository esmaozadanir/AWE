import 'dart:convert';

import 'package:http/http.dart' as http;

import '../models/pattern_result.dart';

class AweApiException implements Exception {
  final String message;
  AweApiException(this.message);

  @override
  String toString() => message;
}

/// AWE motor backend'ine (bkz. AWE/src/awe/api) HTTP istemcisi.
/// Yalnızca demo için gereken üç çağrıyı sarar: event batch gönderimi, analiz tetikleme
/// ve pattern (alışkanlık dizisi + karar) listesini okuma.
class AweApiClient {
  final String baseUrl;

  AweApiClient({required this.baseUrl});

  Uri _uri(String path) => Uri.parse('$baseUrl$path');

  Future<void> checkHealth() async {
    final response = await http.get(_uri('/health')).timeout(const Duration(seconds: 5));
    if (response.statusCode != 200) {
      throw AweApiException('Backend /health beklenmeyen yanıt verdi: ${response.statusCode}');
    }
  }

  Future<void> pushEventsBatch(String projectId, List<Map<String, dynamic>> events) async {
    final response = await http
        .post(
          _uri('/projects/$projectId/events/batch'),
          headers: {'Content-Type': 'application/json'},
          body: jsonEncode(events),
        )
        .timeout(const Duration(seconds: 15));
    if (response.statusCode != 200) {
      throw AweApiException('Event gönderimi başarısız (${response.statusCode}): ${response.body}');
    }
  }

  Future<void> analyzeSubject(String projectId, String subjectId) async {
    final response = await http
        .post(_uri('/projects/$projectId/subjects/$subjectId/analyze'))
        .timeout(const Duration(seconds: 15));
    if (response.statusCode != 200) {
      throw AweApiException('Analiz çağrısı başarısız (${response.statusCode}): ${response.body}');
    }
  }

  Future<List<VariantPattern>> getPatterns(String projectId, String subjectId) async {
    final response = await http
        .get(_uri('/projects/$projectId/subjects/$subjectId/patterns'))
        .timeout(const Duration(seconds: 15));
    if (response.statusCode != 200) {
      throw AweApiException('Pattern listesi alınamadı (${response.statusCode}): ${response.body}');
    }
    final decoded = jsonDecode(utf8.decode(response.bodyBytes)) as List<dynamic>;
    return decoded.map((e) => VariantPattern.fromJson(e as Map<String, dynamic>)).toList();
  }
}
