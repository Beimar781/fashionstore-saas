import 'dart:convert';

import 'package:fashionstore_movil/core/db/local_database.dart';
import 'package:fashionstore_movil/features/auth/data/auth_repository.dart';
import 'package:fashionstore_movil/features/auth/presentation/auth_controller.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';

void main() {
  sqfliteFfiInit();
  databaseFactory = databaseFactoryFfi;

  late AuthController controller;
  late AuthRepository repo;

  setUp(() async {
    await LocalDatabase.instance.reiniciar(ruta: inMemoryDatabasePath);
    final db = await LocalDatabase.instance.database;
    await db.insert('sesion', {
      'id': 1,
      'access_token': 'access-vencido',
      'refresh_token': 'refresh-guardado',
      'contexto_json': jsonEncode({
        'usuario': {
          'id': 9,
          'nombre': 'Ana',
          'apellidos': 'Cliente',
          'email': 'ana@tienda.com',
          'rol': 'Cliente'
        },
        'empresa': {'id': 2, 'codigo': 'EMP-B', 'razon_social': 'Tienda B'},
        'suscripcion': {
          'plan': {'nombre': 'Básico', 'offline': true}
        },
        'panel': 'tienda',
      }),
      'actualizado_en': DateTime.now().toIso8601String(),
    });
  });

  test(
      'al abrir offline mantiene nombre, empresa y plan si falla la renovación',
      () async {
    final cliente = MockClient((r) async {
      if (r.url.path.endsWith('/auth/me')) return http.Response('{}', 401);
      if (r.url.path.endsWith('/auth/refresh')) {
        throw http.ClientException('sin red');
      }
      return http.Response('{}', 200);
    });
    repo = AuthRepository(cliente: cliente);
    controller = AuthController(repo);

    await controller.iniciar();

    expect(controller.sesion?.nombreCompleto, 'Ana Cliente');
    expect(controller.sesion?.empresaCodigo, 'EMP-B');
    expect(controller.sesion?.planNombre, 'Básico');
    expect(controller.sinConexion, isTrue);
  });

  test('si el servidor rechaza el refresh, elimina la sesión local', () async {
    final cliente = MockClient((r) async {
      if (r.url.path.endsWith('/auth/me')) return http.Response('{}', 401);
      if (r.url.path.endsWith('/auth/refresh')) return http.Response('{}', 401);
      return http.Response('{}', 200);
    });
    repo = AuthRepository(cliente: cliente);
    controller = AuthController(repo);

    await controller.iniciar();

    expect(controller.sesion, isNull);
    expect(await repo.sesionLocal(), isNull);
  });
}
