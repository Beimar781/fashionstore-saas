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

/// Servidor falso: confirma la primera operación de cada envío y deja en conflicto las demás; guarda lo que le llega.
class ApiFalsa extends ApiClient {
  ApiFalsa() : super(obtenerToken: () async => null, renovarToken: () async => false);

  final enviadas = <Map<String, dynamic>>[];

  @override
  Future<Map<String, dynamic>> post(String ruta, Map<String, dynamic> cuerpo, {bool autenticado = true}) async {
    final operaciones = (cuerpo['operaciones'] as List).cast<Map<String, dynamic>>();
    enviadas.addAll(operaciones);
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

final _cajero = Sesion({
  'usuario': {'id': 5, 'nombre': 'Ana', 'apellidos': 'P', 'email': 'a@b.com', 'rol': 'Cajero', 'sucursal_id': 1},
  'empresa': {'id': 1, 'codigo': 'EMP-A', 'razon_social': 'Moda'},
  'suscripcion': {
    'estado': 'ACTIVA',
    'plan': {'nombre': 'Básico', 'max_sucursales': 2, 'reportes_ia': false, 'offline': true},
  },
});

Map<String, dynamic> _catalogo() => {
      'generado_en': DateTime.now().toUtc().toIso8601String(),
      'empresa_id': 1,
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
      'plazo_devolucion_dias': 15,
      'ventas_recientes': [],
      'reservas_sucursal': [
        {
          'id': 77, 'codigo': 'RSV-77', 'cliente': 'Ana Pérez', 'estado': 'PREPARADA', 'programada_para': '2026-11-12T11:00:00Z',
          'items': [
            {'id': 501, 'variante_id': 100, 'producto': 'Camisa Oxford', 'talla': 'S', 'color': 'Rojo', 'cantidad': 2, 'estado': 'RESERVADO'}
          ],
        }
      ],
    };

OperacionLocal _compra(String estado) => OperacionLocal(
    id: 'compra-123456', empresaId: 1, sucursalId: 1, usuarioId: 5, tipo: 'COMPRA', payload: const {'items': [{'variante_id': 100, 'cantidad': 1}]}, estado: estado, intentos: 1,
    mensaje: 'Stock insuficiente', referencia: null, comprobante: null, detalle: null, resumen: 'Compra: 1× Camisa Oxford (S, Rojo)', creadoEn: '2026-11-10T10:00:00Z');

void main() {
  sqfliteFfiInit();
  databaseFactory = databaseFactoryFfi;

  Future<(OfflineController, ApiFalsa, StreamController<bool>)> preparar() async {
    await LocalDatabase.instance.reiniciar(ruta: inMemoryDatabasePath);
    final api = ApiFalsa();
    final red = StreamController<bool>();
    final repo = OfflineRepository(api);
    await repo.guardarCatalogo(_catalogo());
    final c = OfflineController(repo, conectividad: red.stream)..usarSesion(_cajero);
    await Future<void>.delayed(const Duration(milliseconds: 250));
    return (c, api, red);
  }

  test('El resumen con «Ver detalle» se anuncia tras reconectar, con conflictos o con varias operaciones juntas, pero no por una sola confirmada', () async {
    final (c, _, red) = await preparar();
    final resumenes = <String>[];
    c.alResumir = resumenes.add;
    Future<void> registrar(int n) async {
      for (var i = 0; i < n; i++) {
        await c.repo.registrar(tipo: 'RESERVA', payload: {'items': []}, sucursalId: 1, resumen: 'R$i', usuarioId: 5, empresaId: 1);
      }
      await c.recargar();
    }

    await registrar(1); // una sola operación y sin reconexión: confirmada, no hay resumen global
    await c.sincronizar();
    expect(resumenes, isEmpty);
    await registrar(2); // dos juntas: la primera se confirma y la segunda queda en conflicto
    await c.sincronizar();
    expect(resumenes, ['Sincronización completa: 1 confirmadas, 1 en conflicto, 0 rechazadas']);
    c.dispose();
    await red.close();
  });

  test('Las pantallas abiertas se refrescan solas: el contador sube al sincronizar y al volver la red', () async {
    final (c, _, red) = await preparar();
    final inicial = c.refresco;
    await c.repo.registrar(tipo: 'RESERVA', payload: {'items': []}, sucursalId: 1, resumen: 'R', usuarioId: 5, empresaId: 1);
    await c.recargar();
    await c.sincronizar();
    expect(c.refresco, greaterThan(inicial));
    final despuesDeSync = c.refresco;
    red.add(false);
    await Future<void>.delayed(const Duration(milliseconds: 50));
    red.add(true);
    await Future<void>.delayed(const Duration(milliseconds: 300));
    expect(c.refresco, greaterThan(despuesDeSync));
    c.dispose();
    await red.close();
  });

  test('Cobrar una reserva sin conexión: la venta lleva el código y no toca el stock local; la reserva sale de la copia', () async {
    final (c, api, red) = await preparar();
    c.simularSinConexion(true);
    final antes = (await c.repo.buscar('CAM-S-ROJ')).single.variante.stockEn(1);
    await c.registrar(
      tipo: 'VENTA_CONTADO',
      payload: {'items': [{'variante_id': 100, 'cantidad': 2, 'precio_unitario': '100.00'}], 'forma_pago': 'EFECTIVO', 'monto_recibido': '200.00', 'reserva_codigo': 'RSV-77'},
      sucursalId: 1,
      resumen: 'Cobro de la reserva RSV-77 Bs 200.00',
      comprometer: false,
    );
    await c.repo.actualizarReservaLocal(77, quitar: true);
    expect((await c.repo.buscar('CAM-S-ROJ')).single.variante.stockEn(1), antes); // su stock ya estaba apartado
    expect(await c.repo.reservasSucursal(), isEmpty);
    expect(c.pendientes.single.payload['reserva_codigo'], 'RSV-77');
    c.simularSinConexion(false);
    await Future<void>.delayed(const Duration(milliseconds: 500));
    expect(api.enviadas.single['payload']['reserva_codigo'], 'RSV-77'); // viaja al servidor con su código
    c.dispose();
    await red.close();
  });

  testWidgets('«Elegir otra talla o sucursal» entrega el nombre de la prenda de la operación', (tester) async {
    final (c, _, red) = (await tester.runAsync(preparar))!; // la base de datos real corre fuera del reloj falso de testWidgets
    await tester.runAsync(c.recargar); // carga los nombres de las prendas del catálogo descargado
    c.operaciones = [_compra(Estado.enConflicto)];
    String? elegida;
    await tester.pumpWidget(MaterialApp(
        home: Scaffold(
            body: ChangeNotifierProvider<OfflineController>.value(
                value: c, child: OperacionesConProblema(tipos: const ['COMPRA'], titulo: 'Compras que no se pudieron realizar', alElegirOtra: (prenda) => elegida = prenda)))));
    await tester.tap(find.text('Elegir otra talla o sucursal'));
    expect(elegida, 'Camisa Oxford'); // el nombre sale de la copia descargada, sin talla ni color
    c.dispose();
    await tester.runAsync(red.close);
  });
}
