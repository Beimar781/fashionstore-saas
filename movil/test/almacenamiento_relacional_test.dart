import 'dart:io';

import 'package:fashionstore_movil/core/db/local_database.dart';
import 'package:fashionstore_movil/core/network/api_client.dart';
import 'package:fashionstore_movil/features/offline/data/detalle_local.dart';
import 'package:fashionstore_movil/features/offline/data/offline_repository.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:path/path.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';

class ApiFalsa extends ApiClient {
  ApiFalsa() : super(obtenerToken: () async => null, renovarToken: () async => false);

  final enviados = <Map<String, dynamic>>[];
  bool sinRed = false;

  @override
  Future<Map<String, dynamic>> post(String ruta, Map<String, dynamic> cuerpo, {bool autenticado = true}) async {
    if (sinRed) throw ApiException('Sin conexión con el servidor.', sinConexion: true);
    enviados.addAll((cuerpo['operaciones'] as List).cast<Map<String, dynamic>>());
    return {
      'resultados': [
        for (final o in (cuerpo['operaciones'] as List).cast<Map<String, dynamic>>())
          {'id': o['id'], 'estado': 'CONFIRMADA', 'mensaje': 'Operación confirmada.', 'referencia': 'PED-1', 'comprobante': 'CMP-001-000001', 'detalle': null}
      ]
    };
  }

  @override
  Future<List<dynamic>> getLista(String ruta) async => [];
}

void main() {
  sqfliteFfiInit();
  databaseFactory = databaseFactoryFfi;

  Future<OfflineRepository> repoNuevo(ApiFalsa api) async {
    await LocalDatabase.instance.reiniciar(ruta: inMemoryDatabasePath);
    return OfflineRepository(api);
  }

  Future<void> venta(OfflineRepository repo) => repo.registrar(
        tipo: 'VENTA_CONTADO',
        payload: {
          'items': [
            {'variante_id': 100, 'cantidad': 2, 'precio_unitario': '40.00'},
            {'variante_id': 101, 'cantidad': 1, 'precio_unitario': '90.00'}
          ],
          'forma_pago': 'EFECTIVO',
          'monto_recibido': '200.00',
          'cliente_email': null
        },
        sucursalId: 1,
        resumen: 'Venta',
        usuarioId: 5,
        empresaId: 1,
      );

  test('Al registrar una venta y una reserva se guardan sus cabeceras y detalles con claves foráneas', () async {
    final repo = await repoNuevo(ApiFalsa());
    await venta(repo);
    await repo.registrar(
        tipo: 'RESERVA',
        payload: {
          'sucursal_id': 1,
          'programada_para': '2026-11-20T10:00:00',
          'notas': 'x',
          'items': [
            {'variante_id': 100, 'cantidad': 1}
          ]
        },
        sucursalId: 1,
        resumen: 'Reserva',
        usuarioId: 5,
        empresaId: 1);
    final db = await LocalDatabase.instance.database;
    final v = (await db.query('ventas_locales')).single;
    expect((v['forma_pago'], v['total'], v['monto_recibido']), ('EFECTIVO', '170.00', '200.00'));
    expect(await db.query('detalle_venta_local'), hasLength(2));
    expect(await db.query('reservas_locales'), hasLength(1));
    expect(await db.query('detalle_reserva_local'), hasLength(1));
    expect((await db.rawQuery('PRAGMA foreign_keys')).single['foreign_keys'], 1); // integridad referencial activa
    expect(() => db.insert('detalle_venta_local', {'operacion_id': 'no-existe', 'variante_id': 1, 'cantidad': 1}), throwsA(anything)); // sin huérfanos
  });

  test('El cuerpo que viaja al servidor sale del detalle y las ventas ya enviadas conservan su detalle y su resultado', () async {
    final api = ApiFalsa();
    final repo = await repoNuevo(api);
    await venta(repo);
    final db = await LocalDatabase.instance.database;
    await db.update('detalle_venta_local', {'cantidad': 5}, where: 'variante_id = 100'); // el detalle es la fuente de los datos
    await repo.sincronizar(5, 1);
    final enviado = api.enviados.single['payload'] as Map<String, dynamic>;
    expect((enviado['items'] as List).first['cantidad'], 5);
    expect(enviado['forma_pago'], 'EFECTIVO');
    expect(await db.query('detalle_venta_local'), hasLength(2)); // cambiar de estado NO borra el detalle (RN12, §5.4)
    final r = (await db.query('resultados_sincronizacion')).single;
    expect((r['estado'], r['referencia'], r['comprobante']), ('CONFIRMADA', 'PED-1', 'CMP-001-000001'));
  });

  test('Si la sincronización falla por red la operación se conserva y el intento queda en el registro técnico', () async {
    final api = ApiFalsa()..sinRed = true;
    final repo = await repoNuevo(api);
    await venta(repo);
    await repo.sincronizar(5, 1);
    await repo.sincronizar(5, 1);
    final ops = await repo.operaciones(5, 1);
    expect((ops.single.estado, ops.single.intentos), ('REGISTRADA_LOCAL', 2));
    final registro = await repo.registroSincronizacion();
    expect(registro, hasLength(2));
    expect((registro.first['resultado'], registro.first['codigo']), ('SIN_RESPUESTA', 'SIN_RED'));
    final texto = await repo.diagnostico();
    expect(texto, contains('SIN_RED'));
    expect(texto, isNot(contains('@'))); // sin datos personales
  });

  test('Limpiar lo terminado borra también su detalle, pero lo pendiente se queda', () async {
    final repo = await repoNuevo(ApiFalsa());
    await venta(repo);
    await repo.sincronizar(5, 1);
    await venta(repo); // otra venta que sigue pendiente
    await repo.limpiarTerminadas(5, 1);
    final db = await LocalDatabase.instance.database;
    expect(await db.query('ventas_locales'), hasLength(1));
    expect(await db.query('detalle_venta_local'), hasLength(2));
    expect(await db.query('resultados_sincronizacion'), isEmpty);
  });

  test('La cola ya admite CANCELAR_RESERVA (el CHECK anterior la rechazaba)', () async {
    final repo = await repoNuevo(ApiFalsa());
    await repo.registrar(tipo: 'CANCELAR_RESERVA', payload: {'reserva_id': 7, 'motivo': ''}, sucursalId: 1, resumen: 'Cancelar', usuarioId: 5, empresaId: 1);
    expect((await repo.operaciones(5, 1)).single.tipo, 'CANCELAR_RESERVA');
  });

  test('RNF03 y migración: una cola del esquema 4 sobrevive a la actualización y sus ventas pasan a las tablas de detalle', () async {
    final carpeta = await Directory.systemTemp.createTemp('fs_migracion5');
    final ruta = join(carpeta.path, 'v4.db');
    final vieja = await openDatabase(ruta, version: 4, onCreate: (db, _) async {
      await db.execute('''
        CREATE TABLE operaciones_pendientes (
          id TEXT PRIMARY KEY, empresa_id INTEGER NOT NULL, sucursal_id INTEGER, usuario_id INTEGER NOT NULL,
          tipo TEXT NOT NULL CHECK (tipo IN ('VENTA_CONTADO','RESERVA','COMPRA')),
          payload_json TEXT NOT NULL,
          estado TEXT NOT NULL CHECK (estado IN ('REGISTRADA_LOCAL','ENVIADA','CONFIRMADA','RECHAZADA','EN_CONFLICTO')),
          intentos INTEGER NOT NULL DEFAULT 0, mensaje TEXT NOT NULL DEFAULT '', referencia TEXT, comprobante TEXT, detalle_json TEXT,
          resumen TEXT NOT NULL DEFAULT '', creado_en TEXT NOT NULL
        )''');
      await db.execute('CREATE INDEX ix_operaciones_estado ON operaciones_pendientes (empresa_id, usuario_id, estado)');
      await db.insert('operaciones_pendientes', {
        'id': 'v-1',
        'empresa_id': 1,
        'sucursal_id': 1,
        'usuario_id': 5,
        'tipo': 'VENTA_CONTADO',
        'estado': 'REGISTRADA_LOCAL',
        'creado_en': '2026-11-01T10:00:00Z',
        'payload_json': '{"items":[{"variante_id":100,"cantidad":2}],"monto_recibido":"100.00","cliente_email":null}',
      });
      await db.insert('operaciones_pendientes', {
        'id': 'r-1',
        'empresa_id': 1,
        'sucursal_id': 1,
        'usuario_id': 5,
        'tipo': 'RESERVA',
        'estado': 'CONFIRMADA',
        'mensaje': 'Operación confirmada.',
        'referencia': 'RES-9',
        'creado_en': '2026-11-01T11:00:00Z',
        'payload_json': '{"sucursal_id":1,"programada_para":"2026-11-20T10:00:00","notas":"","items":[{"variante_id":101,"cantidad":3}]}',
      });
      await db.insert('operaciones_pendientes', {
        'id': 'c-1',
        'empresa_id': 1,
        'sucursal_id': 1,
        'usuario_id': 5,
        'tipo': 'COMPRA',
        'estado': 'ENVIADA',
        'creado_en': '2026-11-01T12:00:00Z',
        'payload_json': '{"items":[]}',
      });
    });
    await vieja.close();

    await LocalDatabase.instance.reiniciar(ruta: ruta);
    final db = await LocalDatabase.instance.database; // abre la versión 5 y migra
    expect((await db.query('operaciones_pendientes', orderBy: 'id')).map((f) => f['id']), ['c-1', 'r-1', 'v-1']); // ninguna se perdió
    expect((await db.query('detalle_venta_local')).single['cantidad'], 2);
    expect((await db.query('detalle_reserva_local')).single['cantidad'], 3);
    expect((await db.query('resultados_sincronizacion')).single['referencia'], 'RES-9');
    await DetalleLocal.anotarIntento(db, id: 'v-1', tipo: 'VENTA_CONTADO', intento: 1, resultado: 'OK', codigo: '200');
    expect(await db.query('registro_sincronizacion'), hasLength(1));
    await LocalDatabase.instance.reiniciar();
    await carpeta.delete(recursive: true);
  });
}
