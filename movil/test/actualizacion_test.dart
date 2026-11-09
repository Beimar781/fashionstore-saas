import 'package:fashionstore_movil/core/db/local_database.dart';
import 'package:fashionstore_movil/core/network/api_client.dart';
import 'package:fashionstore_movil/features/auth/data/sesion.dart';
import 'package:fashionstore_movil/features/offline/data/offline_repository.dart';
import 'package:fashionstore_movil/features/offline/presentation/offline_controller.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';

/// Servidor falso: cuenta cuántas veces se descargó el catálogo.
class ApiFalsa extends ApiClient {
  ApiFalsa() : super(obtenerToken: () async => null, renovarToken: () async => false);

  int descargas = 0;

  @override
  Future<Map<String, dynamic>> get(String ruta) async {
    descargas++;
    return _catalogo(DateTime.now().toUtc().toIso8601String());
  }

  @override
  Future<Map<String, dynamic>> post(String ruta, Map<String, dynamic> cuerpo, {bool autenticado = true}) async => {'resultados': []};

  @override
  Future<List<dynamic>> getLista(String ruta) async => [];
}

Map<String, dynamic> _catalogo(String generadoEn) => {'generado_en': generadoEn, 'empresa_id': 1, 'sucursales': [], 'productos': [], 'clientes': []};

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

  Future<OfflineController> preparar(ApiFalsa api, DateTime generado) async {
    await LocalDatabase.instance.reiniciar(ruta: inMemoryDatabasePath);
    final repo = OfflineRepository(api);
    await repo.guardarCatalogo({
      'generado_en': generado.toUtc().toIso8601String(),
      'empresa_id': 1,
      'sucursales': [],
      'productos': [
        {'id': 1, 'nombre': 'Camisa', 'categoria': 'Camisas', 'genero': 'UNISEX', 'imagen': null, 'variantes': []}
      ],
      'clientes': [],
    });
    final c = OfflineController(repo)..usarSesion(_sesion);
    await Future<void>.delayed(const Duration(milliseconds: 300));
    await c.recargar();
    return c;
  }

  test('Un catálogo de más de 6 horas se actualiza solo con conexión', () async {
    final api = ApiFalsa();
    final c = await preparar(api, DateTime.now().subtract(const Duration(hours: 7)));
    expect(c.catalogoVencido, isTrue);
    final antes = api.descargas;
    await c.actualizarSiVencido();
    expect(api.descargas, antes + 1);
    expect(c.catalogoVencido, isFalse);
    c.dispose();
  });

  test('Un catálogo reciente no se vuelve a descargar', () async {
    final api = ApiFalsa();
    final c = await preparar(api, DateTime.now().subtract(const Duration(hours: 1)));
    final antes = api.descargas;
    await c.actualizarSiVencido();
    expect(api.descargas, antes);
    c.dispose();
  });

  test('Sin conexión no intenta actualizar aunque esté vencido', () async {
    final api = ApiFalsa();
    final c = await preparar(api, DateTime.now().subtract(const Duration(hours: 9)));
    c.enLinea = false;
    final antes = api.descargas;
    await c.actualizarSiVencido();
    expect(api.descargas, antes);
    c.dispose();
  });
}
