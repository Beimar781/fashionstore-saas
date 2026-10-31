import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:sqflite/sqflite.dart';

import '../../../core/db/local_database.dart';

/// Una prenda (talla y color) que el cliente eligió para reservar. `max` es lo que había disponible al elegirla.
class PrendaElegida {
  PrendaElegida({required this.varianteId, required this.producto, required this.sku, required this.talla, required this.color, required this.max, this.cantidad = 1});

  factory PrendaElegida.desdeJson(Map<String, dynamic> j) => PrendaElegida(
        varianteId: j['variante_id'] as int,
        producto: j['producto'] as String,
        sku: j['sku'] as String,
        talla: j['talla'] as String,
        color: j['color'] as String,
        max: j['max'] as int,
        cantidad: j['cantidad'] as int,
      );

  final int varianteId;
  final String producto;
  final String sku;
  final String talla;
  final String color;
  final int max;
  int cantidad;

  Map<String, dynamic> aJson() =>
      {'variante_id': varianteId, 'producto': producto, 'sku': sku, 'talla': talla, 'color': color, 'max': max, 'cantidad': cantidad};
}

/// CU-09 · Prendas que el cliente va juntando para reservar («Agregar a mi reserva»). Se guardan en el teléfono, separadas por usuario.
class ReservaBorrador extends ChangeNotifier {
  ReservaBorrador({Future<String?> Function(String clave)? leer, Future<void> Function(String clave, String valor)? guardar})
      : _leer = leer ?? _leerDeSqlite,
        _guardar = guardar ?? _guardarEnSqlite;

  final Future<String?> Function(String clave) _leer;
  final Future<void> Function(String clave, String valor) _guardar;

  List<PrendaElegida> prendas = [];
  int? _usuarioId;

  int get total => prendas.fold(0, (suma, p) => suma + p.cantidad);

  /// Lo llama el proveedor al cambiar la sesión: carga el borrador de ese usuario (o lo vacía al cerrar sesión).
  Future<void> usarUsuario(int? usuarioId) async {
    if (usuarioId == _usuarioId) return;
    _usuarioId = usuarioId;
    prendas = [];
    notifyListeners();
    if (usuarioId == null) return;
    final texto = await _leer(_clave(usuarioId));
    if (texto == null || _usuarioId != usuarioId) return;
    prendas = [for (final j in jsonDecode(texto) as List) PrendaElegida.desdeJson(j as Map<String, dynamic>)];
    notifyListeners();
  }

  void agregar(PrendaElegida nueva) {
    final existente = prendas.where((p) => p.varianteId == nueva.varianteId).firstOrNull;
    if (existente == null) {
      prendas.add(nueva);
    } else {
      existente.cantidad = (existente.cantidad + 1).clamp(1, [10, nueva.max].reduce((a, b) => a < b ? a : b)).toInt();
    }
    _cambio();
  }

  void cambiarCantidad(int varianteId, int cantidad) {
    for (final p in prendas.where((p) => p.varianteId == varianteId)) {
      p.cantidad = cantidad.clamp(1, 10).toInt();
    }
    _cambio();
  }

  void quitar(int varianteId) {
    prendas.removeWhere((p) => p.varianteId == varianteId);
    _cambio();
  }

  void vaciar() {
    prendas = [];
    _cambio();
  }

  /// Cuerpo de `POST /reservas`, igual que en la web.
  Map<String, dynamic> aCuerpo({required int sucursalId, required DateTime cuando, String notas = ''}) => {
        'sucursal_id': sucursalId,
        'programada_para': formatoLocal(cuando),
        'notas': notas.trim(),
        'items': [for (final p in prendas) {'variante_id': p.varianteId, 'cantidad': p.cantidad}],
      };

  /// `YYYY-MM-DDTHH:mm` en hora local: el servidor lo toma como hora de la tienda.
  static String formatoLocal(DateTime d) {
    String dos(int n) => n.toString().padLeft(2, '0');
    return '${d.year}-${dos(d.month)}-${dos(d.day)}T${dos(d.hour)}:${dos(d.minute)}';
  }

  String _clave(int usuarioId) => 'reserva_borrador_$usuarioId';

  void _cambio() {
    notifyListeners();
    final id = _usuarioId;
    if (id != null) _guardar(_clave(id), jsonEncode([for (final p in prendas) p.aJson()]));
  }

  static Future<String?> _leerDeSqlite(String clave) async {
    final f = await (await LocalDatabase.instance.database).query('meta', where: 'clave = ?', whereArgs: [clave]);
    return f.isEmpty ? null : f.first['valor'] as String;
  }

  static Future<void> _guardarEnSqlite(String clave, String valor) async =>
      (await LocalDatabase.instance.database).insert('meta', {'clave': clave, 'valor': valor}, conflictAlgorithm: ConflictAlgorithm.replace);
}
