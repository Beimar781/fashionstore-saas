import 'dart:io';

import 'package:fashionstore_movil/core/db/local_database.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:path/path.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';

void main() {
  sqfliteFfiInit();
  databaseFactory = databaseFactoryFfi;

  test('Fase K: al pasar de la versión 2 a la 3 se conserva lo pendiente de sincronizar y ya se admite la compra del cliente', () async {
    final carpeta = await Directory.systemTemp.createTemp('fs_migracion');
    final ruta = join(carpeta.path, 'v2.db');
    // una base como la que dejó la versión 2 de la app, con una venta todavía sin enviar
    final vieja = await openDatabase(ruta, version: 2, onCreate: (db, _) async {
      await db.execute('''
        CREATE TABLE operaciones_pendientes (
          id TEXT PRIMARY KEY, empresa_id INTEGER NOT NULL, sucursal_id INTEGER, usuario_id INTEGER NOT NULL,
          tipo TEXT NOT NULL CHECK (tipo IN ('VENTA_CONTADO','RESERVA')),
          payload_json TEXT NOT NULL,
          estado TEXT NOT NULL CHECK (estado IN ('REGISTRADA_LOCAL','ENVIADA','CONFIRMADA','RECHAZADA','EN_CONFLICTO')),
          intentos INTEGER NOT NULL DEFAULT 0, mensaje TEXT NOT NULL DEFAULT '', referencia TEXT, comprobante TEXT, detalle_json TEXT,
          resumen TEXT NOT NULL DEFAULT '', creado_en TEXT NOT NULL
        )''');
      await db.execute('CREATE INDEX ix_operaciones_estado ON operaciones_pendientes (empresa_id, usuario_id, estado)');
      await db.insert('operaciones_pendientes', {
        'id': 'uuid-1', 'empresa_id': 1, 'usuario_id': 5, 'tipo': 'VENTA_CONTADO', 'payload_json': '{}', 'estado': 'REGISTRADA_LOCAL', 'creado_en': '2026-10-29T10:00:00Z',
      });
    });
    await vieja.close();

    await LocalDatabase.instance.reiniciar(ruta: ruta);
    final db = await LocalDatabase.instance.database; // abre la versión 3 y migra
    expect((await db.query('operaciones_pendientes')).single['id'], 'uuid-1');
    await db.insert('operaciones_pendientes', {
      'id': 'uuid-2', 'empresa_id': 1, 'usuario_id': 5, 'tipo': 'COMPRA', 'payload_json': '{}', 'estado': 'REGISTRADA_LOCAL', 'creado_en': '2026-10-29T10:05:00Z',
    });
    expect((await db.query('operaciones_pendientes')).length, 2);
    await LocalDatabase.instance.reiniciar();
    await carpeta.delete(recursive: true);
  });
}
