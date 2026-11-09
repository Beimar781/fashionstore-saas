import 'dart:convert';

import 'package:fashionstore_movil/core/network/api_client.dart';
import 'package:fashionstore_movil/features/auth/data/auth_repository.dart';
import 'package:fashionstore_movil/features/auth/data/sesion.dart';
import 'package:fashionstore_movil/features/auth/presentation/auth_controller.dart';
import 'package:fashionstore_movil/features/home/presentation/home_screen.dart';
import 'package:fashionstore_movil/features/notificaciones/data/push_repository.dart';
import 'package:fashionstore_movil/features/notificaciones/presentation/push_controller.dart';
import 'package:fashionstore_movil/features/offline/data/offline_repository.dart';
import 'package:fashionstore_movil/features/offline/presentation/offline_controller.dart';
import 'package:fashionstore_movil/primer_parcial/reservas/data/reserva_borrador.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:provider/provider.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';

Sesion _sesion({bool ia = false, bool restringido = false}) => Sesion({
      'usuario': {
        'id': 1,
        'nombre': 'Ana',
        'apellidos': 'Pérez',
        'email': 'a@b.com',
        'rol': 'Cliente'
      },
      'empresa': {'id': 1, 'codigo': 'EMP-B', 'razon_social': 'Estilo Andino'},
      'suscripcion': {
        'estado': 'ACTIVA',
        'fecha_vencimiento': '2027-01-01',
        'plan': {
          'nombre': ia ? 'Profesional' : 'Básico',
          'max_sucursales': 2,
          'reportes_ia': ia,
          'offline': false
        },
      },
      'restringido': restringido,
      'panel': 'catalogo',
    });

/// Servidor falso: el carrito tiene 3 prendas y todo lo demás responde vacío.
final _servidor = MockClient((r) async {
  final cuerpo = r.url.path.endsWith('/carrito')
      ? {
          'items': [
            {'cantidad': 2},
            {'cantidad': 1}
          ]
        }
      : r.url.path.endsWith('/compras')
          ? {'compras': []}
          : r.url.path.contains('/catalogo/buscar')
              ? {'total': 0, 'items': []}
              : r.url.path.contains('/sucursales')
                  ? []
                  : <String, dynamic>{};
  return http.Response(jsonEncode(cuerpo), 200,
      headers: {'content-type': 'application/json; charset=utf-8'});
});

/// Repositorio sin SQLite: la API usa el servidor falso y sin token.
class RepoFalso extends AuthRepository {
  RepoFalso()
      : _api2 = ApiClient(
            obtenerToken: () async => null,
            renovarToken: () async => false,
            cliente: _servidor);

  final ApiClient _api2;

  @override
  ApiClient get api => _api2;
}

Future<PushController> _montar(WidgetTester tester, Sesion sesion,
    {List<AvisoPush> avisos = const []}) async {
  final repo = RepoFalso();
  final auth = AuthController(repo)
    ..sesion = sesion
    ..iniciando = false;
  final offline = OfflineController(OfflineRepository(repo.api))
    ..usarSesion(sesion);
  final push = PushController(PushRepository(repo.api))..avisos = [...avisos];
  tester.view.physicalSize = const Size(360 * 3, 800 * 3);
  tester.view.devicePixelRatio = 3;
  addTearDown(tester.view.reset);
  await tester.pumpWidget(MultiProvider(
    providers: [
      Provider<AuthRepository>.value(value: repo),
      ChangeNotifierProvider<AuthController>.value(value: auth),
      ChangeNotifierProvider<OfflineController>.value(value: offline),
      ChangeNotifierProvider<PushController>.value(value: push),
      ChangeNotifierProvider<ReservaBorrador>(
          create: (_) => ReservaBorrador(
              leer: (_) async => null, guardar: (_, __) async {})),
    ],
    child: const MaterialApp(home: HomeScreen()),
  ));
  await tester.pump(const Duration(milliseconds: 300));
  return push;
}

Future<void> _cerrar(WidgetTester tester) async {
  await tester.pumpWidget(const SizedBox());
  await tester.pump(const Duration(seconds: 1));
}

void main() {
  setUpAll(() {
    sqfliteFfiInit();
    databaseFactory =
        databaseFactoryFfi; // las pantallas guardan lo visto en SQLite; aquí solo importa que no falle
  });

  testWidgets('El Cliente ve la barra inferior con sus 5 pestañas',
      (tester) async {
    await _montar(tester, _sesion());
    expect(find.byType(NavigationBar), findsOneWidget);
    for (final etiqueta in [
      'Inicio',
      'Promociones',
      'Reservas',
      'Compras',
      'Perfil'
    ]) {
      expect(
          find.descendant(
              of: find.byType(NavigationBar), matching: find.text(etiqueta)),
          findsOneWidget,
          reason: etiqueta);
    }
    await _cerrar(tester);
  });

  testWidgets('Las pestañas conservan su estado al cambiar (IndexedStack)',
      (tester) async {
    await _montar(tester, _sesion());
    final pila = tester.widget<IndexedStack>(find.byType(IndexedStack));
    expect(pila.children, hasLength(5));
    await tester.tap(find.text('Perfil'));
    await tester.pump(const Duration(milliseconds: 300));
    expect(tester.widget<IndexedStack>(find.byType(IndexedStack)).index, 4);
    expect(find.text('Ana Pérez'), findsWidgets);
    await _cerrar(tester);
  });

  testWidgets(
      'Con la suscripción restringida solo se ve el Perfil, sin barra ni campana',
      (tester) async {
    await _montar(tester, _sesion(restringido: true));
    expect(find.byType(NavigationBar), findsNothing);
    expect(find.byTooltip('Avisos'), findsNothing);
    expect(find.byTooltip('Carrito'), findsNothing);
    expect(tester.widget<IndexedStack>(find.byType(IndexedStack)).index, 4);
    await _cerrar(tester);
  });

  testWidgets('La campana y el carrito muestran su número y lo ocultan en cero',
      (tester) async {
    await _montar(tester, _sesion(), avisos: [
      AvisoPush(id: 1, titulo: 'A', mensaje: 'm', leido: false),
      AvisoPush(id: 2, titulo: 'B', mensaje: 'm', leido: false),
    ]);
    final campana = find.byTooltip('Avisos');
    final carrito = find.byTooltip('Carrito');
    expect(
        find.descendant(of: campana, matching: find.text('2')), findsOneWidget);
    expect(
        find.descendant(of: carrito, matching: find.text('3')), findsOneWidget);
    await _cerrar(tester);

    await _montar(tester, _sesion());
    expect(
        tester
            .widget<Badge>(find.descendant(
                of: find.byTooltip('Avisos'), matching: find.byType(Badge)))
            .isLabelVisible,
        isFalse);
    await _cerrar(tester);
  });

  testWidgets('El asistente flotante solo aparece con el plan que incluye IA',
      (tester) async {
    await _montar(tester, _sesion(ia: true));
    expect(find.byTooltip('Asistente de compras'), findsOneWidget);
    await _cerrar(tester);

    await _montar(tester, _sesion());
    expect(find.byTooltip('Asistente de compras'), findsNothing);
    await _cerrar(tester);
  });
}
