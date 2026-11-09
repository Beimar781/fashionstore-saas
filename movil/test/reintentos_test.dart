import 'package:fashionstore_movil/core/db/local_database.dart';
import 'package:fashionstore_movil/core/network/api_client.dart';
import 'package:fashionstore_movil/features/auth/data/sesion.dart';
import 'package:fashionstore_movil/features/offline/data/offline_repository.dart';
import 'package:fashionstore_movil/features/offline/presentation/offline_controller.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';

class ApiFalsa extends ApiClient {
  ApiFalsa() : super(obtenerToken: () async => null, renovarToken: () async => false);

  bool sinRed = true;
  int envios = 0;

  @override
  Future<Map<String, dynamic>> post(String ruta, Map<String, dynamic> cuerpo, {bool autenticado = true}) async {
    envios++;
    if (sinRed) throw ApiException('Sin conexión con el servidor.', sinConexion: true);
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
  'usuario': {'id': 5, 'nombre': 'Ana', 'apellidos': 'P', 'email': 'a@b.com', 'rol': 'Cliente'},
  'empresa': {'id': 1, 'codigo': 'EMP-A', 'razon_social': 'Moda'},
  'suscripcion': {
    'estado': 'ACTIVA',
    'plan': {'nombre': 'Básico', 'max_sucursales': 2, 'reportes_ia': false, 'offline': true},
  },
});

void main() {
  sqfliteFfiInit();
  databaseFactory = databaseFactoryFfi;

  test('RNF06: tras cada fallo de red la espera para reintentar se duplica y al tener éxito se reinicia', () async {
    await LocalDatabase.instance.reiniciar(ruta: inMemoryDatabasePath);
    final api = ApiFalsa();
    final repo = OfflineRepository(api);
    await repo.registrar(tipo: 'RESERVA', payload: {'items': []}, sucursalId: 1, resumen: 'R', usuarioId: 5, empresaId: 1);
    final c = OfflineController(repo)..usarSesion(_sesion);
    await Future<void>.delayed(const Duration(milliseconds: 300));
    expect(c.esperaRestante, greaterThan(30)); // el primer fallo (al abrir) ya dejó una espera
    final primera = c.esperaRestante;
    await c.sincronizar();
    expect(c.esperaRestante, greaterThan(primera)); // la espera creció
    expect(c.pendientes, hasLength(1)); // nada se perdió
    api.sinRed = false;
    await c.sincronizar();
    expect(c.pendientes, isEmpty);
    expect(c.esperaRestante, 0); // éxito: se reinicia
    c.dispose();
  });

  test('Una operación rechazada por el servidor (4xx de negocio) no vuelve a enviarse', () async {
    await LocalDatabase.instance.reiniciar(ruta: inMemoryDatabasePath);
    final api = _Rechaza();
    final repo = OfflineRepository(api);
    await repo.registrar(tipo: 'RESERVA', payload: {'items': []}, sucursalId: 1, resumen: 'R', usuarioId: 5, empresaId: 1);
    final c = OfflineController(repo)..usarSesion(_sesion);
    await Future<void>.delayed(const Duration(milliseconds: 300));
    final antes = api.envios;
    await c.sincronizar();
    await c.sincronizar();
    expect(api.envios, antes); // RECHAZADA es un estado final: no hay nada pendiente que reenviar
    expect(c.operaciones.single.estado, 'RECHAZADA');
    c.dispose();
  });
}

class _Rechaza extends ApiFalsa {
  @override
  Future<Map<String, dynamic>> post(String ruta, Map<String, dynamic> cuerpo, {bool autenticado = true}) async {
    envios++;
    return {
      'resultados': [
        for (final o in (cuerpo['operaciones'] as List).cast<Map<String, dynamic>>()) {'id': o['id'], 'estado': 'RECHAZADA', 'mensaje': 'No se puede', 'referencia': null, 'comprobante': null, 'detalle': null}
      ]
    };
  }
}
