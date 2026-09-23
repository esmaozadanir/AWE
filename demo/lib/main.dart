import 'package:flutter/material.dart';

import 'screens/home_screen.dart';

void main() {
  runApp(const AweDemoApp());
}

class AweDemoApp extends StatelessWidget {
  const AweDemoApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'AWE Alışkanlık Motoru Demo',
      theme: ThemeData(
        useMaterial3: true,
        colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFF2D6A4F)),
      ),
      home: const HomeScreen(),
    );
  }
}
