import 'dart:convert';

import 'package:fashionstore_movil/core/network/api_client.dart';
import 'package:fashionstore_movil/features/auth/data/auth_repository.dart';
import 'package:fashionstore_movil/features/offline/data/offline_repository.dart';
import 'package:fashionstore_movil/features/offline/presentation/offline_controller.dart';
import 'package:fashionstore_movil/primer_parcial/reservas/presentation/reservas_screen.dart';
import 'package:fashionstore_movil/primer_parcial/reservas/data/reserva_borrador.dart';
import 'package:fashionstore_movil/primer_parcial/ventas/presentation/pedidos_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:provider/provider.dart';

final _compras = [
  {'id': 1, 'codigo': 'PED-PAGADO', 'fecha': '2026-11-10T10:00:00Z', 'sucursal': 'Centro', 'estado': 'PAGADO', 'total': '100.00', 'total_unidades': 1, 'comprobante_numero': 'CMP-001-000001'},
  {'id': 2, 'codigo': 'PED-DEBE', 'fecha': '2026-11-09T10:00:00Z', 'sucursal': 'Centro', 'estado': 'PENDIENTE_PAGO', 'total': '200.00', 'total_unidades': 2, 'comprobante_numero': null},
];

final _servidor = MockClient((r) async {
  final ruta = r.url.path;
  final cuerpo = ruta.endsWith('/compras')
      ? {'compras': _compras}
      : ruta.endsWith('/compras/2')
          ? {'id': 2, 'codigo': 'PED-DEBE', 'estado': 'PENDIENTE_PAGO', 'total': '200.00', 'items': [], 'comprobante_numero': null}
          : ruta.endsWith('/reservas')
              ? [
                  {'id': 7, 'codigo': 'RES-VIVA', 'estado': 'PENDIENTE', 'sucursal': 'Centro', 'programada_para': '2026-11-12T10:00:00Z', 'puede_cancelar': true, 'items': []},
                  {'id': 8, 'codigo': 'RES-CANC', 'estado': 'CANCELADA', 'sucursal': 'Centro', 'programada_para': '2026-11-12T10:00:00Z', 'puede_cancelar': false, 'items': []},
                ]
              : <String, dynamic>{};
  return http.Response(jsonEncode(cuerpo), 200, headers: {'content-type': 'application/json; charset=utf-8'});
});

class RepoFalso extends AuthRepository {
  RepoFalso() : _api2 = ApiClient(obtenerToken: () async => null, renovarToken: () async => false, cliente: _servidor);
  final ApiClient _api2;
  @override
  ApiClient get api => _api2;
}

Future<void> _montar(WidgetTester tester, Widget pantalla) async {
  final repo = RepoFalso();
  final offline = OfflineController(OfflineRepository(repo.api));
  tester.view.physicalSize = const Size(360 * 3, 1200 * 3);
  tester.view.devicePixelRatio = 3;
  addTearDown(tester.view.reset);
  await tester.pumpWidget(MultiProvider(
    providers: [
      Provider<AuthRepository>.value(value: repo),
      ChangeNotifierProvider<OfflineController>.value(value: offline),
      ChangeNotifierProvider<ReservaBorrador>(create: (_) => ReservaBorrador(leer: (_) async => null, guardar: (_, __) async {})),
    ],
    child: MaterialApp(home: pantalla),
  ));
  await tester.pump(const Duration(milliseconds: 300));
}

void main() {
  testWidgets('Mis compras: el pedido por pagar va primero y resaltado, y los filtros y el buscador funcionan', (tester) async {
    await _montar(tester, const PedidosScreen());
    final porPagar = tester.getTopLeft(find.text('PED-DEBE · Bs 200.00')).dy;
    final pagada = tester.getTopLeft(find.text('PED-PAGADO · Bs 100.00')).dy;
    expect(porPagar, lessThan(pagada)); // «Por pagar» arriba
    expect(find.text('Por pagar'), findsWidgets);
    await tester.tap(find.text('Pagadas'));
    await tester.pump();
    expect(find.text('PED-DEBE · Bs 200.00'), findsNothing);
    await tester.tap(find.text('Todas'));
    await tester.enterText(find.byType(TextField), 'debe');
    await tester.pump();
    expect(find.text('PED-PAGADO · Bs 100.00'), findsNothing);
    expect(find.text('PED-DEBE · Bs 200.00'), findsOneWidget);
  });

  testWidgets('Mis compras: el diálogo del pedido por pagar ofrece «Pagar con tarjeta» y «Cancelar pedido» (con confirmación)', (tester) async {
    await _montar(tester, const PedidosScreen());
    await tester.tap(find.text('PED-DEBE · Bs 200.00'));
    await tester.pump(const Duration(milliseconds: 500));
    await tester.pump(const Duration(milliseconds: 500));
    expect(find.text('Pagar con tarjeta'), findsOneWidget);
    expect(find.text('Cancelar pedido'), findsOneWidget);
    await tester.tap(find.text('Cancelar pedido'));
    await tester.pump(const Duration(milliseconds: 500));
    expect(find.text('¿Cancelar el pedido?'), findsOneWidget);
  });

  testWidgets('Mis reservas: filtros rápidos y buscador por código', (tester) async {
    await _montar(tester, const ReservasScreen());
    expect(find.textContaining('RES-VIVA'), findsOneWidget);
    expect(find.textContaining('RES-CANC'), findsOneWidget);
    await tester.tap(find.text('Canceladas'));
    await tester.pump();
    expect(find.textContaining('RES-VIVA'), findsNothing);
    expect(find.textContaining('RES-CANC'), findsOneWidget);
    await tester.tap(find.text('Todas'));
    await tester.enterText(find.byType(TextField), 'viva');
    await tester.pump();
    expect(find.textContaining('RES-CANC'), findsNothing);
  });
}
