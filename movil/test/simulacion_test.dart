import 'package:fashionstore_movil/core/db/local_database.dart';
import 'package:fashionstore_movil/core/network/api_client.dart';
import 'package:fashionstore_movil/features/auth/data/sesion.dart';
import 'package:fashionstore_movil/features/offline/data/offline_repository.dart';
import 'package:fashionstore_movil/features/offline/presentation/offline_controller.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';

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

  tearDown(() => ApiClient.simularSinConexion = false);

  test('Simular sin conexión: toda llamada falla como sin red aunque el servidor responda', () async {
    var llamadas = 0;
    final api = ApiClient(
      obtenerToken: () async => null,
      renovarToken: () async => false,
      cliente: MockClient((_) async {
        llamadas++;
        return http.Response('{}', 200);
      }),
    );
    expect(await api.get('/algo'), isEmpty);
    ApiClient.simularSinConexion = true;
    await expectLater(api.get('/algo'), throwsA(isA<ApiException>().having((e) => e.sinConexion, 'sinConexion', isTrue)));
    expect(llamadas, 1); // la segunda ni siquiera salió del teléfono
  });

  test('El interruptor del controlador pone «sin conexión» y, al apagarlo, sincroniza lo pendiente', () async {
    await LocalDatabase.instance.reiniciar(ruta: inMemoryDatabasePath);
    var envios = 0;
    final api = _Api(() => envios++);
    final repo = OfflineRepository(api);
    final c = OfflineController(repo)..usarSesion(_sesion);
    await Future<void>.delayed(const Duration(milliseconds: 200));
    c.simularSinConexion(true);
    expect((c.simulado, c.enLinea), (true, false));
    await repo.registrar(tipo: 'RESERVA', payload: {'items': []}, sucursalId: 1, resumen: 'R', usuarioId: 5, empresaId: 1);
    await c.recargar();
    await c.sincronizar();
    expect(c.pendientes, hasLength(1)); // con la simulación activa nada sale
    final antes = envios;
    c.simularSinConexion(false);
    await Future<void>.delayed(const Duration(milliseconds: 400));
    expect(c.enLinea, isTrue);
    expect(envios, greaterThan(antes)); // al apagarla se sincroniza
    expect(c.pendientes, isEmpty);
    c.dispose();
  });
}

class _Api extends ApiClient {
  _Api(this.alEnviar) : super(obtenerToken: () async => null, renovarToken: () async => false);

  final void Function() alEnviar;

  @override
  Future<Map<String, dynamic>> post(String ruta, Map<String, dynamic> cuerpo, {bool autenticado = true}) async {
    if (ApiClient.simularSinConexion) throw ApiException('Sin conexión con el servidor.', sinConexion: true);
    alEnviar();
    return {
      'resultados': [
        for (final o in (cuerpo['operaciones'] as List).cast<Map<String, dynamic>>()) {'id': o['id'], 'estado': 'CONFIRMADA', 'mensaje': 'ok', 'referencia': 'R', 'comprobante': null, 'detalle': null}
      ]
    };
  }

  @override
  Future<List<dynamic>> getLista(String ruta) async => [];
}
