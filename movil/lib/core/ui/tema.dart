import 'package:flutter/material.dart';

class Tema {
  static const Color vino = Color(0xFF7A1F3D);
  static const Color tinta = Color(0xFF1D1A22);
  static const Color fondo = Color(0xFFF6F4F0);

  static ThemeData claro() {
    final esquema = ColorScheme.fromSeed(seedColor: vino, brightness: Brightness.light);
    return ThemeData(
      useMaterial3: true,
      colorScheme: esquema,
      scaffoldBackgroundColor: fondo,
      appBarTheme: const AppBarTheme(backgroundColor: tinta, foregroundColor: Colors.white),
      inputDecorationTheme: const InputDecorationTheme(
        border: OutlineInputBorder(borderRadius: BorderRadius.all(Radius.circular(10))),
        filled: true,
        fillColor: Colors.white,
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          backgroundColor: vino,
          minimumSize: const Size.fromHeight(48),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
        ),
      ),
    );
  }
}
