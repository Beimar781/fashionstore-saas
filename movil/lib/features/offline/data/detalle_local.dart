import 'dart:convert';

import 'package:sqflite/sqflite.dart';

/// §6.3 · Almacenamiento local relacional de las operaciones: ventas y reservas con sus detalles, resultado de cada sincronización y registro técnico.
/// Todo cuelga de `operaciones_pendientes` (la bandeja de salida: UUID, tipo y estado) con claves foráneas, así que nada queda huérfano ni duplicado.
/// La fuente de los datos es el detalle: el cuerpo que viaja al servidor se arma al enviar con `payloadDesdeDetalle`.
class DetalleLocal {
  static Future<void> crearTablas(DatabaseExecutor db) async {
    await db.execute('''
      CREATE TABLE IF NOT EXISTS ventas_locales (
        operacion_id TEXT PRIMARY KEY REFERENCES operaciones_pendientes(id) ON DELETE CASCADE,
        empresa_id INTEGER NOT NULL,
        sucursal_id INTEGER,
        usuario_id INTEGER NOT NULL,
        cliente_email TEXT,
        forma_pago TEXT NOT NULL DEFAULT 'EFECTIVO',
        monto_recibido TEXT NOT NULL,
        total TEXT NOT NULL,
        registrada_en TEXT NOT NULL
      )''');
    await db.execute('''
      CREATE TABLE IF NOT EXISTS detalle_venta_local (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        operacion_id TEXT NOT NULL REFERENCES ventas_locales(operacion_id) ON DELETE CASCADE,
        variante_id INTEGER NOT NULL,
        cantidad INTEGER NOT NULL,
        precio_unitario TEXT
      )''');
    await db.execute('''
      CREATE TABLE IF NOT EXISTS reservas_locales (
        operacion_id TEXT PRIMARY KEY REFERENCES operaciones_pendientes(id) ON DELETE CASCADE,
        empresa_id INTEGER NOT NULL,
        sucursal_id INTEGER,
        usuario_id INTEGER NOT NULL,
        programada_para TEXT,
        notas TEXT NOT NULL DEFAULT '',
        registrada_en TEXT NOT NULL
      )''');
    await db.execute('''
      CREATE TABLE IF NOT EXISTS detalle_reserva_local (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        operacion_id TEXT NOT NULL REFERENCES reservas_locales(operacion_id) ON DELETE CASCADE,
        variante_id INTEGER NOT NULL,
        cantidad INTEGER NOT NULL
      )''');
    await db.execute('''
      CREATE TABLE IF NOT EXISTS resultados_sincronizacion (
        operacion_id TEXT PRIMARY KEY REFERENCES operaciones_pendientes(id) ON DELETE CASCADE,
        estado TEXT NOT NULL,
        mensaje TEXT NOT NULL DEFAULT '',
        referencia TEXT,
        comprobante TEXT,
        actualizado_en TEXT NOT NULL
      )''');
    // RNF10: registro técnico de cada intento (sin datos personales). No depende de la operación: sobrevive a su limpieza.
    await db.execute('''
      CREATE TABLE IF NOT EXISTS registro_sincronizacion (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        operacion_id TEXT NOT NULL,
        tipo TEXT NOT NULL,
        intento INTEGER NOT NULL,
        fecha TEXT NOT NULL,
        resultado TEXT NOT NULL,
        codigo TEXT NOT NULL,
        motivo TEXT NOT NULL DEFAULT ''
      )''');
    await db.execute('CREATE INDEX IF NOT EXISTS ix_ventas_locales_fecha ON ventas_locales (registrada_en)');
    await db.execute('CREATE INDEX IF NOT EXISTS ix_resultados_estado ON resultados_sincronizacion (estado, actualizado_en)');
    await db.execute('CREATE INDEX IF NOT EXISTS ix_registro_sync_fecha ON registro_sincronizacion (fecha)');
  }

  /// Guarda la venta o la reserva con sus líneas a partir del cuerpo con que se registró. Se puede repetir sin duplicar.
  static Future<void> guardar(DatabaseExecutor db, {required String id, required String tipo, required int empresaId, required int? sucursalId, required int usuarioId, required Map<String, dynamic> payload, required String creadoEn}) async {
    final items = ((payload['items'] as List?) ?? const []).cast<Map<String, dynamic>>();
    if (tipo == 'VENTA_CONTADO') {
      await db.delete('ventas_locales', where: 'operacion_id = ?', whereArgs: [id]); // las líneas se van en cascada
      final total = items.fold<double>(0, (s, i) => s + (double.tryParse('${i['precio_unitario']}') ?? 0) * (i['cantidad'] as int));
      await db.insert('ventas_locales', {
        'operacion_id': id, 'empresa_id': empresaId, 'sucursal_id': sucursalId, 'usuario_id': usuarioId, 'cliente_email': payload['cliente_email'],
        'forma_pago': payload['forma_pago'] ?? 'EFECTIVO', 'monto_recibido': '${payload['monto_recibido'] ?? '0'}', 'total': total.toStringAsFixed(2), 'registrada_en': creadoEn,
      });
      for (final i in items) {
        await db.insert('detalle_venta_local', {'operacion_id': id, 'variante_id': i['variante_id'], 'cantidad': i['cantidad'], 'precio_unitario': i['precio_unitario']?.toString()});
      }
    } else if (tipo == 'RESERVA') {
      await db.delete('reservas_locales', where: 'operacion_id = ?', whereArgs: [id]);
      await db.insert('reservas_locales', {
        'operacion_id': id, 'empresa_id': empresaId, 'sucursal_id': payload['sucursal_id'] ?? sucursalId, 'usuario_id': usuarioId,
        'programada_para': payload['programada_para']?.toString(), 'notas': '${payload['notas'] ?? ''}', 'registrada_en': creadoEn,
      });
      for (final i in items) {
        await db.insert('detalle_reserva_local', {'operacion_id': id, 'variante_id': i['variante_id'], 'cantidad': i['cantidad']});
      }
    }
  }

  /// El cuerpo que viaja al servidor, armado desde el detalle. Si la operación no tiene detalle (otro tipo), se usa el cuerpo guardado.
  static Future<Map<String, dynamic>> payloadDesdeDetalle(DatabaseExecutor db, String id, String tipo, Map<String, dynamic> respaldo) async {
    if (tipo == 'VENTA_CONTADO') {
      final v = await db.query('ventas_locales', where: 'operacion_id = ?', whereArgs: [id]);
      if (v.isEmpty) return respaldo;
      final lineas = await db.query('detalle_venta_local', where: 'operacion_id = ?', whereArgs: [id], orderBy: 'id');
      return {
        ...respaldo,
        'items': [for (final l in lineas) {'variante_id': l['variante_id'], 'cantidad': l['cantidad'], if (l['precio_unitario'] != null) 'precio_unitario': l['precio_unitario']}],
        'forma_pago': v.first['forma_pago'], 'monto_recibido': v.first['monto_recibido'], 'cliente_email': v.first['cliente_email'],
      };
    }
    if (tipo == 'RESERVA') {
      final r = await db.query('reservas_locales', where: 'operacion_id = ?', whereArgs: [id]);
      if (r.isEmpty) return respaldo;
      final lineas = await db.query('detalle_reserva_local', where: 'operacion_id = ?', whereArgs: [id], orderBy: 'id');
      return {
        ...respaldo,
        'sucursal_id': r.first['sucursal_id'], 'programada_para': r.first['programada_para'], 'notas': r.first['notas'],
        'items': [for (final l in lineas) {'variante_id': l['variante_id'], 'cantidad': l['cantidad']}],
      };
    }
    return respaldo;
  }

  /// Deja el último resultado de la sincronización de la operación (uno por operación).
  static Future<void> guardarResultado(DatabaseExecutor db, {required String id, required String estado, required String mensaje, String? referencia, String? comprobante}) async {
    await db.insert('resultados_sincronizacion', {
      'operacion_id': id, 'estado': estado, 'mensaje': mensaje, 'referencia': referencia, 'comprobante': comprobante, 'actualizado_en': DateTime.now().toIso8601String(),
    }, conflictAlgorithm: ConflictAlgorithm.replace);
  }

  /// RNF10: una fila por intento, con el código y el motivo técnico (sin correos, NIT ni datos de tarjeta).
  static Future<void> anotarIntento(DatabaseExecutor db, {required String id, required String tipo, required int intento, required String resultado, required String codigo, String motivo = ''}) async {
    await db.insert('registro_sincronizacion', {'operacion_id': id, 'tipo': tipo, 'intento': intento, 'fecha': DateTime.now().toIso8601String(), 'resultado': resultado, 'codigo': codigo, 'motivo': motivo});
  }

  /// Texto para pegar en un correo o chat de soporte: el registro técnico reciente, sin datos personales.
  static Future<String> diagnostico(DatabaseExecutor db, {int limite = 100}) async {
    final filas = await db.query('registro_sincronizacion', orderBy: 'id DESC', limit: limite);
    final lineas = [
      'Diagnóstico de sincronización de FashionStore',
      for (final f in filas) '${f['fecha']} · ${f['tipo']} ${f['operacion_id']} · intento ${f['intento']} · ${f['resultado']} (${f['codigo']})${(f['motivo'] as String).isEmpty ? '' : ' · ${f['motivo']}'}',
    ];
    return lineas.join('\n');
  }

  /// Migración: convierte lo que ya había en la cola (esquema anterior) en filas de las tablas nuevas, sin perder ninguna operación pendiente.
  static Future<void> poblarDesdeOperaciones(DatabaseExecutor db) async {
    final filas = await db.query('operaciones_pendientes');
    for (final f in filas) {
      final tipo = f['tipo'] as String;
      if (tipo != 'VENTA_CONTADO' && tipo != 'RESERVA') continue;
      await guardar(
        db, id: f['id'] as String, tipo: tipo, empresaId: f['empresa_id'] as int, sucursalId: f['sucursal_id'] as int?, usuarioId: f['usuario_id'] as int,
        payload: jsonDecode(f['payload_json'] as String) as Map<String, dynamic>, creadoEn: f['creado_en'] as String,
      );
      if (f['estado'] != 'REGISTRADA_LOCAL' && f['estado'] != 'ENVIADA') {
        await guardarResultado(db, id: f['id'] as String, estado: f['estado'] as String, mensaje: f['mensaje'] as String, referencia: f['referencia'] as String?, comprobante: f['comprobante'] as String?);
      }
    }
  }
}
