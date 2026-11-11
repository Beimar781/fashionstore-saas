import 'dart:io';

import 'package:fashionstore_movil/core/db/local_database.dart';
import 'package:fashionstore_movil/core/network/api_client.dart';
import 'package:fashionstore_movil/features/auth/data/auth_repository.dart';
import 'package:fashionstore_movil/features/auth/data/sesion.dart';
import 'package:fashionstore_movil/features/offline/data/offline_repository.dart';
import 'package:fashionstore_movil/features/offline/presentation/conflictos_screen.dart';
import 'package:fashionstore_movil/features/offline/presentation/offline_controller.dart';
import 'package:fashionstore_movil/features/offline/presentation/registro_sync_screen.dart';
import 'package:fashionstore_movil/features/offline/presentation/resumen_turno_screen.dart';
import 'package:fashionstore_movil/features/offline/presentation/tareas_sucursal_screen.dart';
import 'package:fashionstore_movil/primer_parcial/catalogo/presentation/catalogo_screen.dart';
import 'package:fashionstore_movil/primer_parcial/reservas/data/reserva_borrador.dart';
import 'package:fashionstore_movil/primer_parcial/reservas/presentation/carrito_screen.dart';
import 'package:fashionstore_movil/primer_parcial/reservas/presentation/reservas_screen.dart';
import 'package:fashionstore_movil/primer_parcial/reservas/presentation/tarjetas_screen.dart';
import 'package:fashionstore_movil/primer_parcial/ventas/presentation/pedidos_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/testing.dart';
import 'package:provider/provider.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';

Sesion _sesion(String rol) => Sesion({
      'usuario': {'id': 5, 'nombre': 'Luis', 'apellidos': 'P', 'email': 'e@b.com', 'rol': rol, 'sucursal_id': 1},
      'empresa': {'id': 1, 'codigo': 'EMP-A', 'razon_social': 'Moda'},
      'suscripcion': {'estado': 'ACTIVA', 'plan': {'nombre': 'Básico', 'max_sucursales': 2, 'reportes_ia': false, 'offline': true}},
    });

/// Tercera ronda F · Con el servidor caído y SIN datos guardados, ninguna pantalla del móvil queda con el círculo girando ni con un «No hay…» que engañe.
void main() {
  sqfliteFfiInit();
  databaseFactory = databaseFactoryFfi;

  final pantallas = <String, ({String rol, Widget Function() crear})>{
    'Mi carrito': (rol: 'Cliente', crear: () => const CarritoScreen()),
    'Tarjetas guardadas': (rol: 'Cliente', crear: () => const TarjetasScreen()),
    'Mis compras': (rol: 'Cliente', crear: () => const PedidosScreen()),
    'Mis reservas': (rol: 'Cliente', crear: () => const ReservasScreen()),
    'Catálogo': (rol: 'Cliente', crear: () => const CatalogoScreen()),
    'Conflictos': (rol: 'Encargado', crear: () => const ConflictosScreen()),
    'Registro de sincronización': (rol: 'Cajero', crear: () => const RegistroSyncScreen()),
    'Resumen del turno': (rol: 'Cajero', crear: () => const ResumenTurnoScreen()),
    'Devoluciones': (rol: 'Cajero', crear: () => const DevolucionesScreen()),
    'Tareas de la sucursal': (rol: 'Encargado', crear: () => const TareasSucursalScreen()),
  };

  for (final e in pantallas.entries) {
    testWidgets('${e.key}: sin red y sin datos guardados no queda con el círculo girando', (tester) async {
      await tester.runAsync(() async {
        await LocalDatabase.instance.reiniciar(ruta: inMemoryDatabasePath);
        ApiClient.simularSinConexion = false;
        final auth = AuthRepository(cliente: MockClient((_) async => throw const SocketException('sin red')));
        final sesion = _sesion(e.value.rol);
        final c = OfflineController(OfflineRepository(auth.api))..usarSesion(sesion);
        await Future<void>.delayed(const Duration(milliseconds: 100));
        tester.view.physicalSize = const Size(800, 2000);
        tester.view.devicePixelRatio = 1;
        addTearDown(tester.view.reset);
        await tester.pumpWidget(MultiProvider(
          providers: [
            ChangeNotifierProvider<OfflineController>.value(value: c),
            Provider<AuthRepository>.value(value: auth),
            ChangeNotifierProvider<ReservaBorrador>(create: (_) => ReservaBorrador(leer: (_) async => null, guardar: (_, __) async {})),
          ],
          child: MaterialApp(home: e.value.crear()),
        ));
        for (var i = 0; i < 25; i++) {
          await tester.pump(const Duration(milliseconds: 60));
          await Future<void>.delayed(const Duration(milliseconds: 20));
        }
        expect(find.byType(CircularProgressIndicator), findsNothing, reason: '${e.key} quedó girando');
        await Future<void>.delayed(const Duration(milliseconds: 150));
        c.dispose();
      });
    });
  }
}
