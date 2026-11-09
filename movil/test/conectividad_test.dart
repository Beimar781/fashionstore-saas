import 'dart:async';

import 'package:fashionstore_movil/core/db/local_database.dart';
import 'package:fashionstore_movil/core/network/api_client.dart';
import 'package:fashionstore_movil/features/auth/data/sesion.dart';
import 'package:fashionstore_movil/features/offline/data/offline_repository.dart';
import 'package:fashionstore_movil/features/offline/presentation/offline_controller.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';

/// Servidor falso: cuenta cuántas veces se sincronizó y confirma toda operación.
class ApiFalsa extends ApiClient {
  ApiFalsa()
      : super(obtenerToken: () async => null, renovarToken: () async => false);

  int sincronizaciones = 0;

  @override
  Future<Map<String, dynamic>> post(String ruta, Map<String, dynamic> cuerpo,
      {bool autenticado = true}) async {
    sincronizaciones++;
    return {
      'resultados': [
        for (final o
            in (cuerpo['operaciones'] as List).cast<Map<String, dynamic>>())
          {
            'id': o['id'],
            'estado': 'CONFIRMADA',
            'mensaje': 'Confirmada.',
            'referencia': 'RES-1',
            'comprobante': null,
            'detalle': null
          }
      ]
    };
  }

  @override
  Future<List<dynamic>> getLista(String ruta) async => [];
}

final _sesion = Sesion({
  'usuario': {
    'id': 5,
    'nombre': 'Ana',
    'apellidos': 'Pérez',
    'email': 'a@b.com',
    'rol': 'Cliente'
  },
  'empresa': {'id': 1, 'codigo': 'EMP-A', 'razon_social': 'Moda'},
  'suscripcion': {
    'estado': 'ACTIVA',
    'plan': {
      'nombre': 'Básico',
      'max_sucursales': 2,
      'reportes_ia': false,
      'offline': true
    },
  },
});

void main() {
  sqfliteFfiInit();
  databaseFactory = databaseFactoryFfi;

  test(
      'Al volver la red se sincroniza en el acto lo pendiente, sin esperar el reintento',
      () async {
    await LocalDatabase.instance.reiniciar(ruta: inMemoryDatabasePath);
    final api = ApiFalsa();
    final repo = OfflineRepository(api);
    final red = StreamController<bool>();
    final c = OfflineController(repo, conectividad: red.stream);
    c.usarSesion(_sesion);
    await Future<void>.delayed(const Duration(
        milliseconds:
            200)); // arranque: recarga y primera sincronización (nada pendiente)

    red.add(false);
    await Future<void>.delayed(Duration.zero);
    expect(c.enLinea, isFalse); // al perder la red se avisa enseguida

    await repo.registrar(
        tipo: 'RESERVA',
        payload: {'items': []},
        sucursalId: 1,
        resumen: 'Reserva',
        usuarioId: 5,
        empresaId: 1);
    await c.recargar();
    expect(c.pendientes, hasLength(1));
    final antes = api.sincronizaciones;

    red.add(true);
    await Future<void>.delayed(const Duration(milliseconds: 300));
    expect(api.sincronizaciones, antes + 1); // se envió apenas volvió la red
    expect(c.enLinea, isTrue);
    expect(c.pendientes, isEmpty);

    c.dispose();
    await red.close();
  });

  test('Si vuelve la red y no hay nada pendiente no se llama al servidor',
      () async {
    await LocalDatabase.instance.reiniciar(ruta: inMemoryDatabasePath);
    final api = ApiFalsa();
    final red = StreamController<bool>();
    final c =
        OfflineController(OfflineRepository(api), conectividad: red.stream)
          ..usarSesion(_sesion);
    await Future<void>.delayed(const Duration(milliseconds: 200));
    final antes = api.sincronizaciones;
    red.add(true);
    await Future<void>.delayed(const Duration(milliseconds: 200));
    expect(api.sincronizaciones, antes);
    c.dispose();
    await red.close();
  });
}
