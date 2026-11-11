import 'dart:async';

import 'package:fashionstore_movil/core/db/local_database.dart';
import 'package:fashionstore_movil/core/network/api_client.dart';
import 'package:fashionstore_movil/features/auth/data/sesion.dart';
import 'package:fashionstore_movil/features/offline/data/modelos.dart';
import 'package:fashionstore_movil/features/offline/data/offline_repository.dart';
import 'package:fashionstore_movil/features/offline/presentation/offline_controller.dart';
import 'package:fashionstore_movil/features/offline/presentation/operaciones_con_problema.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';

/// Servidor falso: confirma la primera operación de cada envío y deja en conflicto las demás.
class ApiFalsa extends ApiClient {
  ApiFalsa() : super(obtenerToken: () async => null, renovarToken: () async => false);

  @override
  Future<Map<String, dynamic>> post(String ruta, Map<String, dynamic> cuerpo, {bool autenticado = true}) async {
    final operaciones = (cuerpo['operaciones'] as List).cast<Map<String, dynamic>>();
    return {
      'resultados': [
        for (final (i, o) in operaciones.indexed)
          {'id': o['id'], 'estado': i == 0 ? 'CONFIRMADA' : 'EN_CONFLICTO', 'mensaje': i == 0 ? 'ok' : 'Stock insuficiente', 'referencia': 'R', 'comprobante': null, 'detalle': null}
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

OperacionLocal _operacion(String tipo, String estado, String mensaje) => OperacionLocal(
    id: 'op-$tipo-$estado', empresaId: 1, sucursalId: 1, usuarioId: 5, tipo: tipo, payload: const {}, estado: estado, intentos: 1, mensaje: mensaje,
    referencia: null, comprobante: null, detalle: null, resumen: 'Operación de prueba', creadoEn: '2026-11-10T10:00:00Z');

void main() {
  sqfliteFfiInit();
  databaseFactory = databaseFactoryFfi;

  test('Al perder y recuperar la red se avisa en cualquier pantalla y, tras sincronizar, sale el resumen', () async {
    await LocalDatabase.instance.reiniciar(ruta: inMemoryDatabasePath);
    final red = StreamController<bool>();
    final repo = OfflineRepository(ApiFalsa());
    final avisos = <String>[];
    final c = OfflineController(repo, conectividad: red.stream)
      ..alAvisar = avisos.add
      ..usarSesion(_sesion);
    await Future<void>.delayed(const Duration(milliseconds: 200));

    red.add(true); // el primer valor que entrega el teléfono (ya había red) no es una reconexión
    await Future<void>.delayed(const Duration(milliseconds: 50));
    expect(avisos, isEmpty);

    red.add(false);
    await Future<void>.delayed(const Duration(milliseconds: 50));
    expect(avisos, [msgSinRed]);

    for (final n in [1, 2]) {
      await repo.registrar(tipo: 'RESERVA', payload: {'items': []}, sucursalId: 1, resumen: 'R$n', usuarioId: 5, empresaId: 1);
    }
    await c.recargar();
    red.add(true);
    await Future<void>.delayed(const Duration(milliseconds: 500));
    expect(avisos[1], 'Conexión restablecida. Sincronizando 2 operaciones…');
    expect(avisos.last, 'Sincronización completa: 1 confirmadas, 1 en conflicto, 0 rechazadas');
    c.dispose();
    await red.close();
  });

  test('Con la app en segundo plano el aviso sale además como notificación del sistema', () async {
    await LocalDatabase.instance.reiniciar(ruta: inMemoryDatabasePath);
    final red = StreamController<bool>();
    final notificaciones = <String>[];
    final c = OfflineController(OfflineRepository(ApiFalsa()), conectividad: red.stream)
      ..alNotificar = notificaciones.add
      ..usarSesion(_sesion);
    await Future<void>.delayed(const Duration(milliseconds: 200));
    red.add(false);
    await Future<void>.delayed(const Duration(milliseconds: 50));
    expect(notificaciones, isEmpty); // en primer plano basta el aviso dentro de la app
    c.didChangeAppLifecycleState(AppLifecycleState.paused);
    red.add(true);
    await Future<void>.delayed(const Duration(milliseconds: 50));
    expect(notificaciones, ['Conexión restablecida.']);
    c.dispose();
    await red.close();
  });

  test('Con la app en segundo plano, al volver la red sale la notificación local «Volvió la conexión: se enviaron N operaciones»', () async {
    await LocalDatabase.instance.reiniciar(ruta: inMemoryDatabasePath);
    final red = StreamController<bool>();
    final repo = OfflineRepository(ApiFalsa());
    final notificaciones = <String>[];
    final c = OfflineController(repo, conectividad: red.stream)
      ..alNotificar = notificaciones.add
      ..usarSesion(_sesion);
    await Future<void>.delayed(const Duration(milliseconds: 200));
    red.add(false);
    await Future<void>.delayed(const Duration(milliseconds: 50));
    for (final n in [1, 2]) {
      await repo.registrar(tipo: 'RESERVA', payload: {'items': []}, sucursalId: 1, resumen: 'R$n', usuarioId: 5, empresaId: 1);
    }
    await c.recargar();
    c.didChangeAppLifecycleState(AppLifecycleState.paused);
    notificaciones.clear();
    red.add(true);
    await Future<void>.delayed(const Duration(milliseconds: 500));
    expect(notificaciones, contains('Volvió la conexión: se enviaron 2 operaciones.'));
    expect(textoVolvioLaConexion(1), 'Volvió la conexión: se enviaron 1 operación.');
    c.dispose();
    await red.close();
  });

  test('Los textos de los avisos', () {
    expect(textoReconexion(0), 'Conexión restablecida.');
    expect(textoResumen(ResumenSync(confirmadas: 2, enConflicto: 1, rechazadas: 3)), 'Sincronización completa: 2 confirmadas, 1 en conflicto, 3 rechazadas');
    expect(motivoParaCliente(_operacion('COMPRA', Estado.enConflicto, 'Stock insuficiente')), msgAgotada);
    expect(devolucionDeEfectivo(_operacion('VENTA_CONTADO', Estado.rechazada, 'Se devolvieron Bs 100 en efectivo al cliente (nota ND-1).')), 'Efectivo devuelto al cliente.');
  });

  testWidgets('El cliente ve su compra en conflicto con el motivo y el botón para elegir otra talla o sucursal', (tester) async {
    final c = OfflineController(OfflineRepository(ApiFalsa()));
    c.operaciones = [_operacion('COMPRA', Estado.enConflicto, 'Stock insuficiente'), _operacion('RESERVA', Estado.enConflicto, 'x'), _operacion('COMPRA', Estado.confirmada, 'ok')];
    var elegir = 0;
    await tester.pumpWidget(MaterialApp(
        home: Scaffold(
            body: ChangeNotifierProvider<OfflineController>.value(
                value: c, child: OperacionesConProblema(tipos: const ['COMPRA'], titulo: 'Compras que no se pudieron realizar', alElegirOtra: (_) => elegir++)))));
    expect(find.text('Compras que no se pudieron realizar'), findsOneWidget);
    expect(find.text(msgAgotada), findsOneWidget); // solo la compra en conflicto: ni la reserva ni la confirmada
    await tester.tap(find.text('Elegir otra talla o sucursal'));
    expect(elegir, 1);
  });

  testWidgets('El cajero ve «Ventas con problema» con el estado de la devolución del efectivo; sin problemas no se muestra nada', (tester) async {
    final c = OfflineController(OfflineRepository(ApiFalsa()));
    Widget app() => MaterialApp(
        home: Scaffold(body: ChangeNotifierProvider<OfflineController>.value(value: c, child: OperacionesConProblema(key: ValueKey(c.operaciones.length), tipos: const ['VENTA_CONTADO'], titulo: 'Ventas con problema'))));
    await tester.pumpWidget(app());
    expect(find.text('Ventas con problema'), findsNothing);
    c.operaciones = [_operacion('VENTA_CONTADO', Estado.enConflicto, 'Stock insuficiente')];
    await tester.pumpWidget(app());
    expect(find.text('Ventas con problema'), findsOneWidget);
    expect(find.textContaining('Pendiente: el Encargado'), findsOneWidget);
  });
}
