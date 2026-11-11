import 'dart:async';

import 'package:fashionstore_movil/core/db/local_database.dart';
import 'package:fashionstore_movil/core/network/api_client.dart';
import 'package:fashionstore_movil/features/auth/data/sesion.dart';
import 'package:fashionstore_movil/features/offline/data/modelos.dart';
import 'package:fashionstore_movil/features/offline/data/offline_repository.dart';
import 'package:fashionstore_movil/features/offline/presentation/offline_controller.dart';
import 'package:fashionstore_movil/features/offline/presentation/registrar_offline_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';

/// Servidor falso: entrega un catálogo, confirma lo que se le envía y puede quedar sin red.
class ApiFalsa extends ApiClient {
  ApiFalsa() : super(obtenerToken: () async => null, renovarToken: () async => false);

  int descargas = 0;
  int envios = 0;
  bool sinRed = false;
  String estadoDeLaSegunda = 'CONFIRMADA';

  @override
  Future<Map<String, dynamic>> get(String ruta) async {
    if (sinRed) throw ApiException('Sin conexión con el servidor.', sinConexion: true);
    descargas++;
    return {
      'generado_en': DateTime.now().toUtc().toIso8601String(),
      'empresa_id': 1,
      'iva_porcentaje': 13,
      'sucursales': [
        {'id': 1, 'nombre': 'Centro', 'ciudad': 'SC', 'direccion': null, 'horario': null}
      ],
      'productos': [
        {
          'id': 10, 'nombre': 'Camisa Oxford', 'categoria': 'Camisas', 'genero': 'UNISEX', 'imagen': null,
          'variantes': [
            {'id': 100, 'sku': 'CAM-S-ROJ', 'codigo_barras': null, 'talla': 'S', 'color': 'Rojo', 'precio': '100.00', 'precio_final': '100.00', 'promocion': null, 'stock': {'1': 5}}
          ],
        }
      ],
      'clientes': [],
    };
  }

  @override
  Future<Map<String, dynamic>> post(String ruta, Map<String, dynamic> cuerpo, {bool autenticado = true}) async {
    envios++;
    if (sinRed) throw ApiException('Sin conexión con el servidor.', sinConexion: true);
    final operaciones = (cuerpo['operaciones'] as List).cast<Map<String, dynamic>>();
    return {
      'resultados': [
        for (final (i, o) in operaciones.indexed)
          {'id': o['id'], 'estado': i == 0 ? 'CONFIRMADA' : estadoDeLaSegunda, 'mensaje': i == 0 ? 'ok' : 'Stock insuficiente', 'referencia': 'R', 'comprobante': null, 'detalle': null}
      ]
    };
  }

  @override
  Future<List<dynamic>> getLista(String ruta) async => [];
}

Sesion _sesion(int id, String rol) => Sesion({
      'usuario': {'id': id, 'nombre': 'U$id', 'apellidos': 'P', 'email': 'u$id@b.com', 'rol': rol, 'sucursal_id': 1},
      'empresa': {'id': 1, 'codigo': 'EMP-A', 'razon_social': 'Moda'},
      'suscripcion': {
        'estado': 'ACTIVA',
        'plan': {'nombre': 'Básico', 'max_sucursales': 2, 'reportes_ia': false, 'offline': true},
      },
    });

Future<void> _esperar(bool Function() listo) async {
  for (var i = 0; i < 80 && !listo(); i++) {
    await Future<void>.delayed(const Duration(milliseconds: 50));
  }
  await Future<void>.delayed(const Duration(milliseconds: 100));
}

void main() {
  sqfliteFfiInit();
  databaseFactory = databaseFactoryFfi;

  test('Cliente → Cajero → Encargado en el mismo teléfono: cada uno descarga su copia y no ve la del anterior', () async {
    await LocalDatabase.instance.reiniciar(ruta: inMemoryDatabasePath);
    final api = ApiFalsa();
    final repo = OfflineRepository(api);
    final c = OfflineController(repo, descargaAutomatica: true)..usarSesion(_sesion(1, 'Cliente'));
    await _esperar(() => api.descargas >= 1);
    expect(await repo.duenoDeLaCopia(), '1|Cliente|1');

    // sin red, el siguiente usuario no puede ver la copia del Cliente (se borra antes de mostrar nada)
    api.sinRed = true;
    c.usarSesion(null);
    await _esperar(() => false);
    expect(c.hayCatalogo, isFalse);
    expect(await repo.hayCatalogo(), isFalse);
    c.usarSesion(_sesion(2, 'Cajero'));
    await _esperar(() => false);
    expect(c.hayCatalogo, isFalse); // sin red y sin copia propia: nada del Cliente
    expect(await repo.duenoDeLaCopia(), isNull);

    api.sinRed = false;
    c.usarSesion(null);
    c.usarSesion(_sesion(2, 'Cajero'));
    await _esperar(() => api.descargas >= 2);
    expect(await repo.duenoDeLaCopia(), '2|Cajero|1');

    // cambio directo de usuario (sin pasar por el cierre de sesión): la copia del Cajero se descarta y se baja la del Encargado
    c.usarSesion(_sesion(3, 'Encargado'));
    await _esperar(() => api.descargas >= 3);
    expect(await repo.duenoDeLaCopia(), '3|Encargado|1');
    c.dispose();
  });

  test('Al cerrar sesión se borra la copia, el carrito y los avisos en caché, pero las operaciones pendientes se conservan con su dueño', () async {
    await LocalDatabase.instance.reiniciar(ruta: inMemoryDatabasePath);
    final api = ApiFalsa()..sinRed = true;
    final repo = OfflineRepository(api);
    api.sinRed = false;
    await repo.guardarCatalogo(await api.get('/offline/catalogo'));
    await repo.anotarDueno('1|Cliente|1');
    await repo.guardarCarritoCliente({'sucursal_id': 1, 'items': []}, 1, 1);
    await repo.ponerMeta('avisos_usuario_1', '[]');
    await repo.guardarTarjetas([{'id': 1}]);
    await repo.registrar(tipo: 'RESERVA', payload: {'items': []}, sucursalId: 1, resumen: 'Mi reserva', usuarioId: 1, empresaId: 1);
    api.sinRed = true;
    final c = OfflineController(repo)..usarSesion(_sesion(1, 'Cliente'));
    await _esperar(() => false);
    c.usarSesion(null);
    await _esperar(() => false);
    expect(await repo.hayCatalogo(), isFalse);
    expect(await repo.carritoClienteLocal(1, 1), isNull);
    expect(await repo.leerMeta('avisos_usuario_1'), isNull);
    expect(await repo.tarjetasLocales(), isEmpty);
    expect(await repo.operaciones(1, 1), hasLength(1)); // la operación sigue siendo de su dueño
    expect(await repo.operaciones(2, 1), isEmpty);      // otro usuario no la ve
    c.dispose();
  });

  test('El aviso de la sincronización cuenta lo de ESA sincronización, dice cuándo hay conflicto y no sale si se cerró la sesión', () async {
    await LocalDatabase.instance.reiniciar(ruta: inMemoryDatabasePath);
    final api = ApiFalsa()..estadoDeLaSegunda = 'EN_CONFLICTO';
    final repo = OfflineRepository(api);
    final avisos = <(String, bool)>[];
    final c = OfflineController(repo)
      ..alResumir = (t, {bool conflicto = false}) { avisos.add((t, conflicto)); }
      ..usarSesion(_sesion(3, 'Encargado'));
    await _esperar(() => false);
    for (final n in ['A', 'B']) {
      await repo.registrar(tipo: 'RESERVA', payload: {'items': []}, sucursalId: 1, resumen: n, usuarioId: 3, empresaId: 1);
    }
    await c.recargar();
    await c.sincronizar();
    expect(avisos.single.$1, 'Sincronización completa: 1 confirmadas, 1 en conflicto (revíselas), 0 rechazadas');
    expect(avisos.single.$2, isTrue); // «Ver detalle» abre Conflictos (es Encargado)

    // otra sincronización: solo cuenta lo nuevo, no el conflicto anterior
    avisos.clear();
    api.estadoDeLaSegunda = 'CONFIRMADA';
    for (final n in ['C', 'D']) {
      await repo.registrar(tipo: 'RESERVA', payload: {'items': []}, sucursalId: 1, resumen: n, usuarioId: 3, empresaId: 1);
    }
    await c.recargar();
    await c.sincronizar();
    expect(avisos.single.$1, 'Sincronización completa: 2 confirmadas, 0 en conflicto, 0 rechazadas');

    // si se cierra la sesión mientras se envía, nadie recibe el aviso
    avisos.clear();
    for (final n in ['E', 'F']) {
      await repo.registrar(tipo: 'RESERVA', payload: {'items': []}, sucursalId: 1, resumen: n, usuarioId: 3, empresaId: 1);
    }
    await c.recargar();
    final f = c.sincronizar();
    c.usarSesion(null);
    await f;
    expect(avisos, isEmpty);
    c.dispose();
  });

  test('Al volver la red se reintenta solo lo pendiente, una vez, y reenviar no duplica (RN12)', () async {
    await LocalDatabase.instance.reiniciar(ruta: inMemoryDatabasePath);
    final api = ApiFalsa()..sinRed = true;
    final repo = OfflineRepository(api);
    final red = StreamController<bool>();
    await repo.registrar(tipo: 'RESERVA', payload: {'items': []}, sucursalId: 1, resumen: 'R', usuarioId: 1, empresaId: 1);
    final c = OfflineController(repo, conectividad: red.stream)..usarSesion(_sesion(1, 'Cliente'));
    await _esperar(() => false);
    expect(c.pendientes, hasLength(1));
    api.sinRed = false;
    red.add(true);
    await _esperar(() => c.pendientes.isEmpty);
    expect(c.pendientes, isEmpty);
    final enviosAntes = api.envios;
    red.add(true);
    await _esperar(() => false);
    expect(api.envios, enviosAntes); // ya confirmada: no se vuelve a mandar
    expect(c.operaciones.where((o) => o.estado == Estado.confirmada), hasLength(1));
    c.dispose();
    await red.close();
  });

  testWidgets('Caja: la línea «IVA incluido» aparece al armar la venta (100.00 → Bs 11.50)', (tester) async {
    await tester.runAsync(() async {
      await LocalDatabase.instance.reiniciar(ruta: inMemoryDatabasePath);
      final api = ApiFalsa();
      final repo = OfflineRepository(api);
      await repo.guardarCatalogo(await api.get('/offline/catalogo'));
      await repo.anotarDueno('2|Cajero|1');
      final c = OfflineController(repo)..usarSesion(_sesion(2, 'Cajero'));
      await c.recargar();
      await tester.pumpWidget(MaterialApp(
          home: Scaffold(body: ChangeNotifierProvider<OfflineController>.value(value: c, child: const RegistrarOfflineTab()))));
      await Future<void>.delayed(const Duration(milliseconds: 300));
      await tester.pump();
      await tester.enterText(find.byType(TextField).last, 'camisa');
      await Future<void>.delayed(const Duration(milliseconds: 200));
      await tester.pump();
      await tester.tap(find.byType(ActionChip).first);
      await Future<void>.delayed(const Duration(milliseconds: 200));
      await tester.pump();
      expect(find.text('IVA incluido: Bs 11.50'), findsOneWidget);
      expect(find.text('Registrar venta en el dispositivo'), findsOneWidget); // botón fijo abajo
      c.dispose();
    });
  });
}
