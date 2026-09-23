import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:flutter_application_1/main.dart';

void main() {
  testWidgets('App launches and shows the run-simulation button', (WidgetTester tester) async {
    await tester.pumpWidget(const AweDemoApp());

    expect(find.text('Simülasyonu Çalıştır'), findsOneWidget);
    expect(find.byIcon(Icons.settings_outlined), findsOneWidget);
  });
}
