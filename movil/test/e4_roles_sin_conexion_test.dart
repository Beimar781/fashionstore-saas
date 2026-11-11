import 'dart:convert';

import 'package:fashionstore_movil/core/network/api_client.dart';
import 'package:fashionstore_movil/features/auth/data/auth_repository.dart';
import 'package:fashionstore_movil/features/auth/data/sesion.dart';
import 'package:fashionstore_movil/features/auth/presentation/auth_controller.dart';
import 'package:fashionstore_movil/features/home/presentation/home_screen.dart';
import 'package:fashionstore_movil/features/notificaciones/data/push_repository.dart';
import 'package:fashionstore_movil/features/notificaciones/presentation/push_controller.dart';
import 'package:fashionstore_movil/features/offline/data/offline_repository.dart';
import 'package:fashionstore_movil/features/offline/presentation/conflictos_screen.dart';
import 'package:fashionstore_movil/features/offline/presentation/offline_controller.dart';
import 'package:fashionstore_movil/primer_parcial/reservas/data/reserva_borrador.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:provider/provider.dart';
// ignore: depend_on_referenced_packages
import 'package:sqflite_common/utils/utils.dart' as utilidades_sqflite;
import 'package:sqflite_common_ffi/sqflite_ffi.dart';

Sesion _sesion(String rol) => Sesion({
      'usuario': {'id': 1, 'nombre': 'Ana', 'apellidos': 'Pérez', 'email': 'a@b.com', 'rol': rol, 'sucursal_id': 1},
      'empresa': {'id': 1, 'codigo': 'EMP-B', 'razon_social': 'Estilo Andino'},
      'suscripcion': {'estado': 'ACTIVA', 'fecha_vencimiento': '2027-01-01', 'plan': {'nombre': 'Profesional', 'max_sucursales': 10, 'reportes_ia': true, 'offline': true}},
      'restringido': false,
      'panel': 'empresa',
    });

class RepoFalso extends AuthRepository {
  RepoFalso()
      : _api2 = ApiClient(
            obtenerToken: () async => null,
            renovarToken: () async => false,
            cliente: MockClient((r) async => http.Response(jsonEncode(<String, dynamic>{}), 200, headers: {'content-type': 'application/json'})));
  final ApiClient _api2;

  @override
  ApiClient get api => _api2;
}

Future<OfflineController> _montar(WidgetTester tester, Sesion sesion) async {
  final repo = RepoFalso();
  final auth = AuthController(repo)
    ..sesion = sesion
    ..iniciando = false;
  final offline = OfflineController(OfflineRepository(repo.api))..usarSesion(sesion);
  tester.view.physicalSize = const Size(360 * 3, 1400 * 3);
  tester.view.devicePixelRatio = 3;
  addTearDown(tester.view.reset);
  await tester.pumpWidget(MultiProvider(
    providers: [
      Provider<AuthRepository>.value(value: repo),
      ChangeNotifierProvider<AuthController>.value(value: auth),
      ChangeNotifierProvider<OfflineController>.value(value: offline),
      ChangeNotifierProvider<PushController>.value(value: PushController(PushRepository(repo.api))),
      ChangeNotifierProvider<ReservaBorrador>(create: (_) => ReservaBorrador(leer: (_) async => null, guardar: (_, __) async {})),
    ],
    child: const MaterialApp(home: HomeScreen()),
  ));
  await tester.pump(const Duration(milliseconds: 300));
  return offline;
}

Future<void> _cerrar(WidgetTester tester) async {
  await tester.pumpWidget(const SizedBox());
  await tester.pump(const Duration(seconds: 1));
}

class _ApiConCopia extends ApiClient {
  _ApiConCopia() : super(obtenerToken: () async => null, renovarToken: () async => false);

  @override
  Future<List<dynamic>> getLista(String ruta) async {
    ApiClient.lecturaLocalDesde = '2026-11-10T10:00:00Z'; // el servidor no respondió: lo que llega es la última copia guardada
    return [
      {'id': 'op-1', 'tipo': 'COMPRA', 'sucursal': 'Centro', 'usuario': 'Luis', 'creada_en': '2026-11-10T10:00:00Z', 'intentos': 1, 'mensaje': 'No hay stock', 'detalle': {'faltantes': []}}
    ];
  }
}

void main() {
  setUpAll(() {
    sqfliteFfiInit();
    // ignore: deprecated_member_use
    utilidades_sqflite.lockWarningDuration = null;
    databaseFactory = databaseFactoryFfi;
  });

  testWidgets('Cajero y Encargado: una sola «Caja» y una sola «Devoluciones» (con o sin conexión); el Encargado suma Tareas y Conflictos', (tester) async {
    var offline = await _montar(tester, _sesion('Encargado'));
    expect(find.text('Caja'), findsOneWidget);
    expect(find.text('Devoluciones'), findsOneWidget);
    expect(find.text('Tareas de la sucursal'), findsOneWidget);
    expect(find.text('Conflictos de sincronización'), findsOneWidget);
    expect(find.text('Caja sin conexión'), findsNothing);
    await _cerrar(tester);
    offline.dispose();
    offline = await _montar(tester, _sesion('Cajero'));
    expect(find.text('Caja'), findsOneWidget);
    expect(find.text('Tareas de la sucursal'), findsNothing);
    expect(find.text('Conflictos de sincronización'), findsNothing);
    await _cerrar(tester);
    offline.dispose();
  });

  testWidgets('Administrador y Proveedor: con red explican que trabajan en la web; sin conexión dicen «Esta función necesita Internet» y el botón queda apagado', (tester) async {
    final offline = await _montar(tester, _sesion('Proveedor'));
    expect(find.text('Las funciones de su rol se usan desde la web de FashionStore.'), findsOneWidget);
    expect(tester.widget<FilledButton>(find.widgetWithText(FilledButton, 'Actualizar mi plan')).onPressed, isNotNull);
    offline.simularSinConexion(true);
    await tester.pump();
    expect(find.text('Esta función necesita Internet.'), findsOneWidget);
    expect(tester.widget<FilledButton>(find.widgetWithText(FilledButton, 'Actualizar mi plan')).onPressed, isNull);
    expect(find.byType(CircularProgressIndicator), findsNothing);
    ApiClient.simularSinConexion = false;
    await _cerrar(tester);
  });

  testWidgets('Conflictos sin conexión: se ve la última lista guardada con su fecha y Reintentar y Descartar quedan apagados', (tester) async {
    await tester.pumpWidget(MaterialApp(home: ConflictosScreen(api: _ApiConCopia())));
    await tester.pumpAndSettle();
    expect(find.textContaining('Sin conexión · datos al'), findsOneWidget);
    expect(find.textContaining('Qué pasó: No hay stock'), findsOneWidget);
    expect(tester.widget<FilledButton>(find.widgetWithText(FilledButton, 'Reintentar')).onPressed, isNull);
    expect(tester.widget<OutlinedButton>(find.widgetWithText(OutlinedButton, 'Descartar…')).onPressed, isNull);
    ApiClient.lecturaLocalDesde = null;
  });
}
