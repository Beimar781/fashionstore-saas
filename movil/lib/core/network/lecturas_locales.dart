import 'dart:convert';

import 'package:sqflite/sqflite.dart';

import '../db/local_database.dart';

/// Una lectura (GET) guardada con red y la fecha en que se guardó («Datos al…»).
class LecturaGuardada {
  const LecturaGuardada(this.datos, this.fecha);
  final dynamic datos;
  final String fecha;
}

/// Copia de las lecturas hechas con red para responder con ella cuando el servidor no contesta. La clave incluye la cuenta: nadie ve lo de otra.
abstract class LecturasLocales {
  Future<void> guardar(String clave, dynamic datos);
  Future<LecturaGuardada?> leer(String clave);
  Future<void> borrarTodo();
}

class LecturasSqlite implements LecturasLocales {
  static const maximo = 300;

  Future<Database> get _db => LocalDatabase.instance.database;

  @override
  Future<void> guardar(String clave, dynamic datos) async {
    final db = await _db;
    await db.insert('lecturas', {'clave': clave, 'cuerpo': jsonEncode(datos), 'fecha': DateTime.now().toUtc().toIso8601String()}, conflictAlgorithm: ConflictAlgorithm.replace);
    // límite de tamaño: se descartan las más viejas
    await db.execute('DELETE FROM lecturas WHERE clave NOT IN (SELECT clave FROM lecturas ORDER BY fecha DESC LIMIT $maximo)');
  }

  @override
  Future<LecturaGuardada?> leer(String clave) async {
    final filas = await (await _db).query('lecturas', where: 'clave = ?', whereArgs: [clave]);
    if (filas.isEmpty) return null;
    return LecturaGuardada(jsonDecode(filas.first['cuerpo'] as String), filas.first['fecha'] as String);
  }

  @override
  Future<void> borrarTodo() async => (await _db).delete('lecturas');
}
