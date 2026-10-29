import 'package:fashionstore_movil/core/db/local_database.dart';
import 'package:fashionstore_movil/core/network/api_client.dart';
import 'package:fashionstore_movil/features/auth/data/sesion.dart';
import 'package:fashionstore_movil/features/notificaciones/data/push_repository.dart';
import 'package:fashionstore_movil/features/notificaciones/presentation/push_controller.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';

/// API simulada: anota lo que se le envía y devuelve los avisos que la prueba le indique.
class ApiFalsa extends ApiClient {
  ApiFalsa() : super(obtenerToken: () async => null, renovarToken: () async => false);

  final List<(String, Map<String, dynamic>)> llamadas = [];
  List<dynamic> avisos = [];
  bool cae = false;

  @override
  Future<Map<String, dynamic>> post(String ruta, Map<String, dynamic> cuerpo, {bool autenticado = true}) async {
    if (cae) throw ApiException('Sin conexión con el servidor.', sinConexion: true);
    llamadas.add((ruta, cuerpo));
    return {};
  }

  @override
  Future<List<dynamic>> getLista(String ruta) async {
    if (cae) throw ApiException('Sin conexión con el servidor.', sinConexion: true);
    return avisos;
  }
}

Map<String, dynamic> _aviso(int id) => {'id': id, 'titulo': 'Devolución registrada', 'mensaje': 'Registramos la devolución NDV-001-000001.', 'leida': false};

Sesion _sesion({int usuario = 5, bool restringido = false}) => Sesion({
      'usuario': {'id': usuario, 'nombre': 'Ana', 'apellidos': 'Cliente', 'email': 'ana@tienda.com', 'rol': 'Cliente'},
      'empresa': {'id': 1, 'codigo': 'EMP-A', 'razon_social': 'Empresa A'},
      'restringido': restringido,
    });

void main() {
  sqfliteFfiInit();
  databaseFactory = databaseFactoryFfi;

  late ApiFalsa api;
  late PushRepository repo;

  setUp(() async {
    await LocalDatabase.instance.reiniciar(ruta: inMemoryDatabasePath);
    api = ApiFalsa();
    repo = PushRepository(api);
  });

  test('el dispositivo se registra con un identificador local que no cambia', () async {
    await repo.registrarDispositivo();
    await repo.registrarDispositivo();
    expect(api.llamadas.map((l) => l.$1), ['/notificaciones/dispositivos', '/notificaciones/dispositivos']);
    final token = api.llamadas.first.$2['token'] as String;
    expect(api.llamadas.first.$2['canal'], 'MOVIL');
    expect(token, startsWith('simulado-'));
    expect(api.llamadas.last.$2['token'], token);
  });

  test('al cerrar sesión se da de baja el mismo dispositivo', () async {
    await repo.registrarDispositivo();
    await repo.quitarDispositivo();
    expect(api.llamadas.last.$1, '/notificaciones/dispositivos/baja');
    expect(api.llamadas.last.$2['token'], api.llamadas.first.$2['token']);
  });

  test('los avisos pendientes se leen y se marcan como leídos', () async {
    api.avisos = [_aviso(1), _aviso(2)];
    final pendientes = await repo.pendientes();
    expect(pendientes.map((a) => a.id), [1, 2]);
    await repo.marcarLeido(1);
    expect(api.llamadas.last.$1, '/notificaciones/1/leer');
  });

  test('al iniciar sesión registra el dispositivo y muestra los avisos; sin conexión no falla', () async {
    api.avisos = [_aviso(7)];
    final c = PushController(repo);
    c.usarSesion(_sesion());
    await Future<void>.delayed(const Duration(milliseconds: 100));
    expect(api.llamadas.map((l) => l.$1), contains('/notificaciones/dispositivos'));
    expect(c.avisos.map((a) => a.id), [7]);
    await c.leer(c.avisos.first);
    expect(c.avisos, isEmpty);

    api.cae = true;
    c.usarSesion(_sesion(usuario: 6));
    await Future<void>.delayed(const Duration(milliseconds: 100));
    expect(c.avisos, isEmpty); // sin conexión la app sigue y no lanza errores
    c.usarSesion(null);
    c.dispose();
  });

  test('con la suscripción vencida no se registra el dispositivo', () async {
    final c = PushController(repo);
    c.usarSesion(_sesion(restringido: true));
    await Future<void>.delayed(const Duration(milliseconds: 100));
    expect(api.llamadas, isEmpty);
    c.dispose();
  });
}
