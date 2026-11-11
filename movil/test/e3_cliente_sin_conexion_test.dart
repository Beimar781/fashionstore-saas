import 'dart:convert';
import 'dart:io';

import 'package:fashionstore_movil/core/db/local_database.dart';
import 'package:fashionstore_movil/core/network/api_client.dart';
import 'package:fashionstore_movil/core/network/lecturas_locales.dart';
import 'package:fashionstore_movil/features/auth/data/auth_repository.dart';
import 'package:fashionstore_movil/features/auth/data/sesion.dart';
import 'package:fashionstore_movil/features/offline/data/carrito_sin_conexion.dart';
import 'package:fashionstore_movil/features/offline/data/offline_repository.dart';
import 'package:fashionstore_movil/features/offline/presentation/estado_conexion_chip.dart';
import 'package:fashionstore_movil/features/offline/presentation/offline_controller.dart';
import 'package:fashionstore_movil/primer_parcial/catalogo/data/catalogo_repository.dart';
import 'package:fashionstore_movil/primer_parcial/catalogo/presentation/catalogo_screen.dart';
import 'package:fashionstore_movil/primer_parcial/reservas/data/reserva_borrador.dart';
import 'package:fashionstore_movil/primer_parcial/reservas/data/reservas_repository.dart';
import 'package:fashionstore_movil/primer_parcial/reservas/presentation/carrito_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:provider/provider.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';

final _sesion = Sesion({
  'usuario': {'id': 5, 'nombre': 'Luis', 'apellidos': 'P', 'email': 'e@b.com', 'rol': 'Cliente'},
  'empresa': {'id': 1, 'codigo': 'EMP-A', 'razon_social': 'Moda'},
  'suscripcion': {'estado': 'ACTIVA', 'plan': {'nombre': 'Básico', 'max_sucursales': 2, 'reportes_ia': false, 'offline': true}},
});

Map<String, dynamic> _catalogo() => {
      'generado_en': DateTime.now().toUtc().toIso8601String(),
      'empresa_id': 1,
      'sucursales': [{'id': 1, 'nombre': 'Centro', 'ciudad': 'SC', 'direccion': null, 'horario': null}],
      'productos': [
        {
          'id': 10, 'nombre': 'Camisa Oxford', 'categoria': 'Camisas', 'genero': 'UNISEX', 'imagen': '1/productos/10/a.png',
          'variantes': [
            {'id': 100, 'sku': 'CAM-S-ROJ', 'codigo_barras': null, 'talla': 'S', 'color': 'Rojo', 'precio': '100.00', 'precio_final': '100.00', 'promocion': null, 'stock': {'1': 5}},
            {'id': 101, 'sku': 'CAM-M-AZU', 'codigo_barras': null, 'talla': 'M', 'color': 'Azul', 'precio': '100.00', 'precio_final': '100.00', 'promocion': null, 'stock': {'1': 0}},
          ],
        }
      ],
      'clientes': [],
    };

/// Servidor falso: responde lo que se le pida o, si `caido`, no contesta.
class ServidorFalso extends http.BaseClient {
  bool caido = false;
  final peticiones = <String>[];

  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) async {
    if (caido) throw const SocketException('sin red');
    peticiones.add('${request.method} ${request.url.path}');
    final cuerpo = jsonEncode(request.url.path.endsWith('/carrito') ? {'items': [], 'total': '0.00'} : {'hay': 'datos'});
    return http.StreamedResponse(Stream.value(utf8.encode(cuerpo)), 200, headers: {'content-type': 'application/json'});
  }
}

void main() {
  sqfliteFfiInit();
  databaseFactory = databaseFactoryFfi;

  setUp(() async {
    await LocalDatabase.instance.reiniciar(ruta: inMemoryDatabasePath);
    ApiClient.simularSinConexion = false;
    ApiClient.lecturaLocalDesde = null;
    ApiClient.alDetectarServidor = null;
  });

  group('Lecturas guardadas (E3)', () {
    ApiClient cliente(ServidorFalso servidor, {String cuenta = '1:5'}) =>
        ApiClient(obtenerToken: () async => 'tok', renovarToken: () async => false, cliente: servidor, lecturas: LecturasSqlite(), cuenta: () async => cuenta);

    test('con red guarda la lectura y, con el servidor caído o «Simular sin conexión», entrega la copia con su fecha', () async {
      final servidor = ServidorFalso();
      final api = cliente(servidor);
      expect(await api.get('/catalogo/productos/10/opciones'), {'hay': 'datos'});
      await Future<void>.delayed(const Duration(milliseconds: 50));
      servidor.caido = true;
      expect(await api.get('/catalogo/productos/10/opciones'), {'hay': 'datos'});
      expect(ApiClient.lecturaLocalDesde, isNotNull);
      ApiClient.simularSinConexion = true;
      servidor.caido = false;
      expect(await api.get('/catalogo/productos/10/opciones'), {'hay': 'datos'});
      expect(servidor.peticiones.length, 1); // la segunda y la tercera no llegaron al servidor
    });

    test('sin copia falla con sinConexion; la copia es de cada cuenta; no se guardan la sesión ni la IA ni las escrituras', () async {
      final servidor = ServidorFalso();
      await cliente(servidor).get('/reservas');
      await cliente(servidor).get('/auth/me');
      await cliente(servidor).get('/asistente/outfit');
      await cliente(servidor).post('/reservas', {});
      await Future<void>.delayed(const Duration(milliseconds: 50));
      servidor.caido = true;
      await expectLater(cliente(servidor, cuenta: '1:6').get('/reservas'), throwsA(isA<ApiException>().having((e) => e.sinConexion, 'sinConexion', true)));
      await expectLater(cliente(servidor).get('/auth/me'), throwsA(isA<ApiException>()));
      await expectLater(cliente(servidor).get('/asistente/outfit'), throwsA(isA<ApiException>()));
      await expectLater(cliente(servidor).post('/reservas', {}), throwsA(isA<ApiException>()));
      expect(await cliente(servidor).get('/reservas'), {'hay': 'datos'}); // la de su cuenta sí
    });

    test('avisa si el servidor respondió o no: es la única fuente del indicador de conexión', () async {
      final servidor = ServidorFalso();
      final avisos = <bool>[];
      ApiClient.alDetectarServidor = avisos.add;
      final api = cliente(servidor);
      await api.get('/reservas');
      servidor.caido = true;
      await api.get('/reservas'); // sale de la copia, pero el servidor no contestó
      expect(avisos, [true, false]);
    });
  });

  group('Indicador de conexión (E3)', () {
    testWidgets('pasa a «Sin conexión» cuando el servidor no responde y vuelve a «En línea» con la primera respuesta', (tester) async {
      await tester.runAsync(() async {
        final c = OfflineController(OfflineRepository(ApiClient(obtenerToken: () async => null, renovarToken: () async => false)))..usarSesion(_sesion);
        await Future<void>.delayed(const Duration(milliseconds: 100));
        await tester.pumpWidget(MaterialApp(home: Scaffold(appBar: AppBar(actions: [ChangeNotifierProvider<OfflineController>.value(value: c, child: const EstadoConexionChip())]))));
        expect(find.text('En línea'), findsOneWidget);
        ApiClient.alDetectarServidor!(false);
        await tester.pump();
        expect(c.enLinea, isFalse);
        expect(find.text('Sin conexión'), findsOneWidget);
        ApiClient.alDetectarServidor!(true);
        await tester.pump();
        expect(c.enLinea, isTrue);
        await Future<void>.delayed(const Duration(milliseconds: 150)); // deja terminar lo que el controlador tenga en curso
        c.dispose();
      });
    });
  });

  group('Carrito del Cliente sin conexión (E3)', () {
    late OfflineRepository repo;
    late CarritoSinConexion sin;
    final servidor = {
      'sucursal_id': 1, 'sucursal': 'Centro', 'total_unidades': 3, 'subtotal': '300.00', 'descuento': '0.00', 'iva_incluido': '0.00', 'total': '300.00', 'puede_pagar': true, 'avisos': [],
      'items': [
        {'id': 11, 'variante_id': 100, 'producto': 'Camisa Oxford', 'talla': 'S', 'color': 'Rojo', 'precio': '100.00', 'precio_final': '100.00', 'cantidad': 2, 'disponible': 5, 'estado': 'OK'},
        {'id': 12, 'variante_id': 101, 'producto': 'Camisa Oxford', 'talla': 'M', 'color': 'Azul', 'precio': '100.00', 'precio_final': '100.00', 'cantidad': 1, 'disponible': 5, 'estado': 'OK'},
      ],
    };

    setUp(() async {
      repo = OfflineRepository(ApiClient(obtenerToken: () async => null, renovarToken: () async => false));
      await repo.guardarCatalogo(_catalogo());
      sin = CarritoSinConexion(repo, empresaId: 1, usuarioId: 5);
    });

    test('cambiar cantidad, quitar y agregar sin red se ven en la vista con el total recalculado', () async {
      await sin.cambiarCantidad(Map<String, dynamic>.from((servidor['items'] as List)[0] as Map), 3);
      await sin.quitar(Map<String, dynamic>.from((servidor['items'] as List)[1] as Map));
      final prenda = (await repo.buscar('CAM-S-ROJ')).single;
      await sin.agregar(prenda, 1);
      final vista = (await sin.vista(servidor))!;
      final items = (vista['items'] as List).cast<Map<String, dynamic>>();
      expect(items.map((i) => [i['id'], i['cantidad']]), [[11, 3], [-100, 1]]); // la prenda agregada aquí lleva id negativo
      expect(vista['total'], '400.00');
      expect(await sin.hayCambios(), isTrue);
    });

    test('no deja pasar de lo disponible en la copia descargada ni de 10 unidades', () async {
      final prenda = (await repo.buscar('CAM-M-AZU')).single; // sin stock
      await expectLater(sin.agregar(prenda, 1), throwsA(isA<ApiException>()));
      await expectLater(sin.cambiarCantidad({'id': 11, 'disponible': 5, 'cantidad': 2}, 6), throwsA(isA<ApiException>()));
      await expectLater(sin.cambiarCantidad({'id': 11, 'disponible': 50, 'cantidad': 2}, 11), throwsA(isA<ApiException>()));
    });

    test('sin cambios la vista es el carrito del servidor tal cual y, sin servidor ni cambios, no hay carrito', () async {
      expect(await sin.vista(servidor), servidor);
      expect(await sin.vista(null), isNull);
    });

    test('al volver la red repite los cambios en orden, fusiona lo agregado una sola vez y deja todo limpio', () async {
      final api = _ReservasFalso();
      await sin.cambiarCantidad(Map<String, dynamic>.from((servidor['items'] as List)[0] as Map), 3);
      await sin.quitar(Map<String, dynamic>.from((servidor['items'] as List)[1] as Map));
      await sin.agregar((await repo.buscar('CAM-S-ROJ')).single, 1);
      expect(await sin.reenviar(api), 0);
      expect(api.llamadas, ['cantidad 11=3', 'quitar 12', 'fusionar 1 [100x1]']);
      expect(await sin.hayCambios(), isFalse);
    });

    test('si la red se cae a mitad del reenvío, lo que falta espera y no se pierde', () async {
      final api = _ReservasFalso()..caerEn = 'quitar';
      await sin.cambiarCantidad(Map<String, dynamic>.from((servidor['items'] as List)[0] as Map), 3);
      await sin.quitar(Map<String, dynamic>.from((servidor['items'] as List)[1] as Map));
      await expectLater(sin.reenviar(api), throwsA(isA<ApiException>()));
      expect((await sin.ediciones()).map((e) => e['tipo']), ['quitar']);
    });

    test('una compra hecha sin conexión limpia lo agregado y los cambios pendientes', () async {
      await sin.cambiarCantidad(Map<String, dynamic>.from((servidor['items'] as List)[0] as Map), 3);
      await sin.agregar((await repo.buscar('CAM-S-ROJ')).single, 1);
      await sin.alComprar();
      expect(await sin.hayCambios(), isFalse);
    });
  });

  testWidgets('Ficha de prenda sin conexión: arma las variantes con el catálogo descargado, muestra «datos al» y deja agregar al carrito del teléfono', (tester) async {
    await tester.runAsync(() async {
      final repoLocal = OfflineRepository(ApiClient(obtenerToken: () async => null, renovarToken: () async => false));
      await repoLocal.guardarCatalogo(_catalogo());
      final c = OfflineController(repoLocal)..usarSesion(_sesion);
      await Future<void>.delayed(const Duration(milliseconds: 100));
      await c.recargar();
      c.simularSinConexion(true);
      final auth = AuthRepository(cliente: MockClient((_) async => throw const SocketException('sin red')));
      final catalogo = _CatalogoSinRed();
      tester.view.physicalSize = const Size(800, 1800);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.reset);
      await tester.pumpWidget(MultiProvider(
        providers: [
          ChangeNotifierProvider<OfflineController>.value(value: c),
          Provider<AuthRepository>.value(value: auth),
          ChangeNotifierProvider<ReservaBorrador>(create: (_) => ReservaBorrador()),
        ],
        child: MaterialApp(home: Builder(builder: (ctx) => Scaffold(body: TextButton(onPressed: () => mostrarDetallePrenda(ctx, catalogo, {'id': 10, 'nombre': 'Camisa Oxford', 'imagen': null}, const []), child: const Text('abrir'))))),
      ));
      await tester.tap(find.text('abrir'));
      for (var i = 0; i < 20; i++) {
        await tester.pump(const Duration(milliseconds: 50));
        await Future<void>.delayed(const Duration(milliseconds: 20));
      }
      expect(find.byType(CircularProgressIndicator), findsNothing); // nunca queda girando
      expect(find.text('S · Rojo'), findsOneWidget);
      expect(find.text('5 disponible(s)'), findsOneWidget);
      expect(find.text('Agotada'), findsOneWidget);
      expect(find.textContaining('Sin conexión · datos al'), findsOneWidget);
      await tester.tap(find.text('S · Rojo'));
      await tester.pump();
      await tester.tap(find.text('Agregar'));
      for (var i = 0; i < 10; i++) {
        await tester.pump(const Duration(milliseconds: 50));
        await Future<void>.delayed(const Duration(milliseconds: 20));
      }
      expect(find.textContaining('agregada a su carrito guardado en este teléfono'), findsOneWidget);
      expect(await CarritoSinConexion(repoLocal, empresaId: 1, usuarioId: 5).hayCambios(), isTrue);
      await Future<void>.delayed(const Duration(milliseconds: 150));
      c.dispose();
    });
  });

  testWidgets('Mi carrito sin conexión: sin carrito guardado lo explica y con prendas agregadas aquí las muestra con «Guardar compra para sincronizar»', (tester) async {
    await tester.runAsync(() async {
      final repoLocal = OfflineRepository(ApiClient(obtenerToken: () async => null, renovarToken: () async => false));
      await repoLocal.guardarCatalogo(_catalogo());
      final c = OfflineController(repoLocal)..usarSesion(_sesion);
      await Future<void>.delayed(const Duration(milliseconds: 100));
      await c.recargar();
      c.simularSinConexion(true);
      tester.view.physicalSize = const Size(800, 1800);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.reset);
      Future<void> abrir() async {
        await tester.pumpWidget(MultiProvider(
          providers: [ChangeNotifierProvider<OfflineController>.value(value: c), Provider<AuthRepository>.value(value: AuthRepository(cliente: MockClient((_) async => throw const SocketException('sin red'))))],
          child: MaterialApp(key: UniqueKey(), home: const CarritoScreen()),
        ));
        for (var i = 0; i < 15; i++) {
          await tester.pump(const Duration(milliseconds: 50));
          await Future<void>.delayed(const Duration(milliseconds: 20));
        }
      }

      await abrir();
      expect(find.textContaining('su carrito no está guardado en este teléfono'), findsOneWidget);
      expect(find.byType(CircularProgressIndicator), findsNothing);

      await CarritoSinConexion(repoLocal, empresaId: 1, usuarioId: 5).agregar((await repoLocal.buscar('CAM-S-ROJ')).single, 1);
      await abrir();
      expect(find.text('Camisa Oxford'), findsOneWidget);
      expect(find.text('Guardar compra para sincronizar'), findsOneWidget);
      expect(find.textContaining('los cambios de su carrito se guardan en este teléfono'), findsOneWidget);
      await Future<void>.delayed(const Duration(milliseconds: 150));
      c.dispose();
    });
  });
}

class _CatalogoSinRed extends CatalogoRepository {
  _CatalogoSinRed() : super(ApiClient(obtenerToken: () async => null, renovarToken: () async => false));

  @override
  Future<Map<String, dynamic>> opciones(int productoId, int? sucursalId) async => throw ApiException('Sin conexión con el servidor.', sinConexion: true);

  @override
  Future<Map<String, dynamic>> detalle(int productoId, {int? sucursalId}) async => throw ApiException('Sin conexión con el servidor.', sinConexion: true);
}

class _ReservasFalso extends ReservasRepository {
  _ReservasFalso() : super(ApiClient(obtenerToken: () async => null, renovarToken: () async => false));

  final llamadas = <String>[];
  String? caerEn;

  void _red(String que) {
    if (caerEn == que) throw ApiException('Sin conexión con el servidor.', sinConexion: true);
  }

  @override
  Future<Map<String, dynamic>> cambiarCantidad(int itemId, int cantidad) async {
    llamadas.add('cantidad $itemId=$cantidad');
    _red('cantidad');
    return {};
  }

  @override
  Future<Map<String, dynamic>> quitar(int itemId) async {
    llamadas.add('quitar $itemId');
    _red('quitar');
    return {};
  }

  @override
  Future<Map<String, dynamic>> vaciarCarrito() async {
    llamadas.add('vaciar');
    return {};
  }

  @override
  Future<Map<String, dynamic>> fusionarCarrito(String fusionId, int sucursalId, List<Map<String, dynamic>> items) async {
    llamadas.add('fusionar $sucursalId [${items.map((i) => '${i['variante_id']}x${i['cantidad']}').join(',')}]');
    return {'rechazadas': []};
  }
}
