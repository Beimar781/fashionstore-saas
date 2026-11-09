import 'dart:io';

import 'package:fashionstore_movil/core/db/local_database.dart';
import 'package:fashionstore_movil/core/network/api_client.dart';
import 'package:fashionstore_movil/features/auth/data/sesion.dart';
import 'package:fashionstore_movil/features/offline/data/offline_repository.dart';
import 'package:fashionstore_movil/features/offline/presentation/offline_controller.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:path/path.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';

class ApiFalsa extends ApiClient {
  ApiFalsa() : super(obtenerToken: () async => null, renovarToken: () async => false);

  final enviados = <Map<String, dynamic>>[];

  @override
  Future<Map<String, dynamic>> post(String ruta, Map<String, dynamic> cuerpo, {bool autenticado = true}) async {
    if (ApiClient.simularSinConexion) throw ApiException('Sin conexión con el servidor.', sinConexion: true);
    enviados.addAll((cuerpo['operaciones'] as List).cast<Map<String, dynamic>>());
    return {
      'resultados': [
        for (final o in (cuerpo['operaciones'] as List).cast<Map<String, dynamic>>()) {'id': o['id'], 'estado': 'CONFIRMADA', 'mensaje': 'ok', 'referencia': 'R', 'comprobante': null, 'detalle': null}
      ]
    };
  }

  @override
  Future<List<dynamic>> getLista(String ruta) async => [];
}

final _sesion = Sesion({
  'usuario': {'id': 5, 'nombre': 'Luis', 'apellidos': 'P', 'email': 'e@b.com', 'rol': 'Encargado', 'sucursal_id': 1},
  'empresa': {'id': 1, 'codigo': 'EMP-A', 'razon_social': 'Moda'},
  'suscripcion': {
    'estado': 'ACTIVA',
    'plan': {'nombre': 'Básico', 'max_sucursales': 2, 'reportes_ia': false, 'offline': true},
  },
});

Map<String, dynamic> _catalogo() => {
      'generado_en': '2026-11-09T10:00:00Z',
      'empresa_id': 1,
      'sucursales': [
        {'id': 1, 'nombre': 'Centro', 'ciudad': 'SC', 'direccion': null, 'horario': null}
      ],
      'productos': [
        {
          'id': 10, 'nombre': 'Camisa Oxford', 'categoria': 'Camisas', 'genero': 'UNISEX', 'imagen': null,
          'variantes': [
            {'id': 100, 'sku': 'CAM-S-ROJ', 'codigo_barras': null, 'talla': 'S', 'color': 'Rojo', 'precio': '100.00', 'precio_final': '100.00', 'promocion': null, 'stock': {'1': 5}}
          ],
        }
      ],
      'clientes': [],
      'plazo_devolucion_dias': 15,
      'ventas_recientes': [
        {
          'comprobante': 'CMP-001-000007', 'pagado_en': '2026-11-08T10:00:00Z', 'total': '200.00', 'vence_el': '2026-11-23T10:00:00Z',
          'items': [
            {'pedido_item_id': 31, 'producto': 'Camisa Oxford', 'talla': 'S', 'color': 'Rojo', 'vendida': 2, 'devolvible': 2, 'precio_final': '100.00'}
          ],
        }
      ],
      'reservas_sucursal': [
        {
          'id': 77, 'codigo': 'RES-77', 'estado': 'PENDIENTE', 'programada_para': '2026-11-12T11:00:00Z',
          'items': [
            {'id': 501, 'variante_id': 100, 'producto': 'Camisa Oxford', 'talla': 'S', 'color': 'Rojo', 'cantidad': 1, 'estado': 'RESERVADO'}
          ],
        }
      ],
    };

void main() {
  sqfliteFfiInit();
  databaseFactory = databaseFactoryFfi;

  late OfflineRepository repo;

  setUp(() async {
    await LocalDatabase.instance.reiniciar(ruta: inMemoryDatabasePath);
    repo = OfflineRepository(ApiFalsa());
    await repo.guardarCatalogo(_catalogo());
  });

  test('B3 y B4: la descarga guarda las ventas recientes con su plazo y las reservas de la sucursal', () async {
    expect(await repo.plazoDevolucionDias(), 15);
    expect((await repo.ventasRecientes()).single['comprobante'], 'CMP-001-000007');
    expect((await repo.reservasSucursal()).single['codigo'], 'RES-77');
  });

  test('B3: lo devuelto sin conexión descuenta lo que todavía se puede devolver', () async {
    await repo.descontarDevolvible('CMP-001-000007', {31: 2});
    expect(((await repo.ventasRecientes()).single['items'] as List).single['devolvible'], 0);
  });

  test('B4: la copia local de la reserva refleja lo preparado, la prenda no encontrada y lo atendido', () async {
    await repo.actualizarReservaLocal(77, estado: 'PREPARADA');
    expect((await repo.reservasSucursal()).single['estado'], 'PREPARADA');
    await repo.actualizarReservaLocal(77, itemNoEncontrado: 501);
    expect(((await repo.reservasSucursal()).single['items'] as List).single['estado'], 'NO_ENCONTRADO');
    await repo.actualizarReservaLocal(77, quitar: true);
    expect(await repo.reservasSucursal(), isEmpty);
  });

  test('B5 y B6: el stock local se mueve de forma provisional con lo recibido o ajustado, sin bajar de cero', () async {
    await repo.moverStockLocal(100, 1, 4);
    expect((await repo.buscar('CAM-S-ROJ')).single.variante.stock[1], 9);
    await repo.moverStockLocal(100, 1, -20);
    expect((await repo.buscar('CAM-S-ROJ')).single.variante.stock[1], 0);
  });

  test('Las tareas de la sucursal se guardan en la cola y se envían con su tipo y sus datos', () async {
    final api = ApiFalsa();
    final r = OfflineRepository(api);
    final c = OfflineController(r)..usarSesion(_sesion);
    await Future<void>.delayed(const Duration(milliseconds: 200));
    c.simularSinConexion(true);
    await c.registrarTarea(tipo: 'AJUSTE_INVENTARIO', payload: {'variante_id': 100, 'diferencia': -2, 'motivo': 'MERMA', 'nota': ''}, resumen: 'Ajuste');
    await c.registrarTarea(tipo: 'RECEPCION', payload: {'variante_id': 100, 'cantidad': 5, 'referencia': 'Envío 9'}, resumen: 'Recepción');
    await c.registrarTarea(tipo: 'PREPARAR_RESERVA', payload: {'reserva_id': 77}, resumen: 'Preparar');
    expect(c.pendientes.map((o) => o.tipo).toSet(), {'AJUSTE_INVENTARIO', 'RECEPCION', 'PREPARAR_RESERVA'});
    c.simularSinConexion(false);
    await Future<void>.delayed(const Duration(milliseconds: 500));
    expect(api.enviados.map((o) => o['tipo']).toSet(), {'AJUSTE_INVENTARIO', 'RECEPCION', 'PREPARAR_RESERVA'});
    expect(c.pendientes, isEmpty);
    c.dispose();
    ApiClient.simularSinConexion = false;
  });

  test('Migración v5 → v6: la cola admite los tipos nuevos y no se pierde ninguna operación ni su detalle', () async {
    final carpeta = await Directory.systemTemp.createTemp('fs_migracion6');
    final ruta = join(carpeta.path, 'v5.db');
    await LocalDatabase.instance.reiniciar(ruta: ruta);
    var db = await LocalDatabase.instance.database; // crea la versión actual
    await db.close();
    // se imita una base de la versión 5: la cola con su CHECK anterior y datos en las tablas hijas
    final vieja = await openDatabase(ruta);
    await vieja.execute('PRAGMA foreign_keys = OFF');
    await vieja.execute('DROP TABLE detalle_venta_local');
    await vieja.execute('DROP TABLE ventas_locales');
    await vieja.execute('DROP TABLE operaciones_pendientes');
    await vieja.execute('''
      CREATE TABLE operaciones_pendientes (
        id TEXT PRIMARY KEY, empresa_id INTEGER NOT NULL, sucursal_id INTEGER, usuario_id INTEGER NOT NULL,
        tipo TEXT NOT NULL CHECK (tipo IN ('VENTA_CONTADO','RESERVA','COMPRA','CANCELAR_RESERVA')),
        payload_json TEXT NOT NULL,
        estado TEXT NOT NULL CHECK (estado IN ('REGISTRADA_LOCAL','ENVIADA','CONFIRMADA','RECHAZADA','EN_CONFLICTO')),
        intentos INTEGER NOT NULL DEFAULT 0, mensaje TEXT NOT NULL DEFAULT '', referencia TEXT, comprobante TEXT, detalle_json TEXT,
        resumen TEXT NOT NULL DEFAULT '', creado_en TEXT NOT NULL
      )''');
    await vieja.execute('''CREATE TABLE ventas_locales (operacion_id TEXT PRIMARY KEY REFERENCES operaciones_pendientes(id) ON DELETE CASCADE, empresa_id INTEGER NOT NULL, sucursal_id INTEGER, usuario_id INTEGER NOT NULL, cliente_email TEXT, forma_pago TEXT NOT NULL DEFAULT 'EFECTIVO', monto_recibido TEXT NOT NULL, total TEXT NOT NULL, registrada_en TEXT NOT NULL)''');
    await vieja.execute('''CREATE TABLE detalle_venta_local (id INTEGER PRIMARY KEY AUTOINCREMENT, operacion_id TEXT NOT NULL REFERENCES ventas_locales(operacion_id) ON DELETE CASCADE, variante_id INTEGER NOT NULL, cantidad INTEGER NOT NULL, precio_unitario TEXT)''');
    await vieja.insert('operaciones_pendientes', {'id': 'v-1', 'empresa_id': 1, 'sucursal_id': 1, 'usuario_id': 5, 'tipo': 'VENTA_CONTADO', 'payload_json': '{}', 'estado': 'REGISTRADA_LOCAL', 'creado_en': '2026-11-01T10:00:00Z'});
    await vieja.insert('ventas_locales', {'operacion_id': 'v-1', 'empresa_id': 1, 'sucursal_id': 1, 'usuario_id': 5, 'monto_recibido': '100', 'total': '80', 'registrada_en': '2026-11-01T10:00:00Z'});
    await vieja.insert('detalle_venta_local', {'operacion_id': 'v-1', 'variante_id': 100, 'cantidad': 2, 'precio_unitario': '40.00'});
    await vieja.setVersion(5);
    await vieja.close();

    await LocalDatabase.instance.reiniciar(ruta: ruta);
    db = await LocalDatabase.instance.database; // abre la versión 6 y migra
    expect((await db.query('operaciones_pendientes')).single['id'], 'v-1');
    expect((await db.query('detalle_venta_local')).single['cantidad'], 2); // el detalle sobrevivió a rehacer la cola
    await db.insert('operaciones_pendientes', {'id': 'a-1', 'empresa_id': 1, 'sucursal_id': 1, 'usuario_id': 5, 'tipo': 'AJUSTE_INVENTARIO', 'payload_json': '{}', 'estado': 'REGISTRADA_LOCAL', 'creado_en': '2026-11-02T10:00:00Z'});
    expect(await db.query('operaciones_pendientes'), hasLength(2));
    await LocalDatabase.instance.reiniciar();
    await carpeta.delete(recursive: true);
  });
}
