import 'dart:math';

final _azar = Random.secure();

/// Identificador único (UUID v4) generado en el dispositivo: así toda operación sin conexión tiene su identificador antes de llegar al servidor (RN11).
String generarUuid() {
  final b = List<int>.generate(16, (_) => _azar.nextInt(256));
  b[6] = (b[6] & 0x0f) | 0x40; // versión 4
  b[8] = (b[8] & 0x3f) | 0x80; // variante RFC 4122
  String h(int desde, int hasta) => b.sublist(desde, hasta).map((x) => x.toRadixString(16).padLeft(2, '0')).join();
  return '${h(0, 4)}-${h(4, 6)}-${h(6, 8)}-${h(8, 10)}-${h(10, 16)}';
}
