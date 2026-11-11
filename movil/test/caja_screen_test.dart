import 'package:fashionstore_movil/core/db/local_database.dart';
import 'package:fashionstore_movil/core/network/api_client.dart';
import 'package:fashionstore_movil/features/auth/data/sesion.dart';
import 'package:fashionstore_movil/features/offline/data/modelos.dart';
import 'package:fashionstore_movil/features/offline/data/offline_repository.dart';
import 'package:fashionstore_movil/features/offline/presentation/caja_screen.dart';
import 'package:fashionstore_movil/features/offline/presentation/offline_controller.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';

/// Servidor falso: entrega un catálogo mínimo y confirma toda operación.
class ApiFalsa extends ApiClient {
  ApiFalsa() : super(obtenerToken: () async => null, renovarToken: () async => false);

  int descargas = 0;

  @override
  Future<Map<String, dynamic>> get(String ruta) async {
    descargas++;
    return {
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
    };
  }

  @override
  Future<Map<String, dynamic>> post(String ruta, Map<String, dynamic> cuerpo, {bool autenticado = true}) async {
    return {
      'resultados': [
        for (final o in (cuerpo['operaciones'] as List).cast<Map<String, dynamic>>()) {'id': o['id'], 'estado': 'CONFIRMADA', 'mensaje': 'ok', 'referencia': 'R', 'comprobante': 'CMP-001-000001', 'detalle': null}
      ]
    };
  }

  @override
  Future<List<dynamic>> getLista(String ruta) async => [];
}

final _sesion = Sesion({
  'usuario': {'id': 5, 'nombre': 'Ana', 'apellidos': 'P', 'email': 'a@b.com', 'rol': 'Cajero', 'sucursal_id': 1},
  'empresa': {'id': 1, 'codigo': 'EMP-A', 'razon_social': 'Moda'},
  'suscripcion': {
    'estado': 'ACTIVA',
    'plan': {'nombre': 'Básico', 'max_sucursales': 2, 'reportes_ia': false, 'offline': true},
  },
});

OperacionLocal _venta(String id, String estado, {String? comprobante}) => OperacionLocal(
    id: id, empresaId: 1, sucursalId: 1, usuarioId: 5, tipo: 'VENTA_CONTADO', payload: const {}, estado: estado, intentos: 0, mensaje: '',
    referencia: null, comprobante: comprobante, detalle: null, resumen: 'Venta de contado $id', creadoEn: '2026-11-10T10:00:00Z');

void main() {
  sqfliteFfiInit();
  databaseFactory = databaseFactoryFfi;

  testWidgets('Caja: sin conexión avisa, cuenta las ventas por sincronizar y lista el estado de cada venta del turno', (tester) async {
    final c = OfflineController(OfflineRepository(ApiFalsa()));
    c.enLinea = false;
    c.operaciones = [_venta('uno111', Estado.registradaLocal), _venta('dos222', Estado.confirmada, comprobante: 'CMP-001-000009'), _venta('tres33', Estado.enConflicto)];
    await tester.pumpWidget(MaterialApp(home: ChangeNotifierProvider<OfflineController>.value(value: c, child: const CajaScreen())));
    expect(find.textContaining('Sin conexión'), findsWidgets);
    expect(find.text('Mi turno (1 por sincronizar)'), findsOneWidget); // solo la registrada local cuenta como por sincronizar
    await tester.tap(find.textContaining('Mi turno'));
    await tester.pumpAndSettle();
    expect(find.text('1 venta(s) por sincronizar'), findsOneWidget);
    expect(find.text('Venta de contado dos222'), findsOneWidget);
    expect(find.textContaining('CMP-001-000009'), findsOneWidget); // la confirmada muestra su comprobante oficial
    expect(find.textContaining('LOC-001-'), findsWidgets);        // las demás, el provisional
    expect(find.text('Confirmada por el servidor'), findsOneWidget);
    expect(find.byTooltip('Resumen de mi turno'), findsOneWidget);
    expect(find.text('Ventas con problema'), findsOneWidget);       // la venta en conflicto aparece aparte con su motivo
  });

  testWidgets('Caja: con todo sincronizado el contador lo dice', (tester) async {
    final c = OfflineController(OfflineRepository(ApiFalsa()));
    c.operaciones = [_venta('dos222', Estado.confirmada, comprobante: 'CMP-001-000009')];
    await tester.pumpWidget(MaterialApp(home: ChangeNotifierProvider<OfflineController>.value(value: c, child: const CajaScreen())));
    expect(find.text('Mi turno'), findsOneWidget);
    expect(find.textContaining('Sin conexión'), findsNothing);
  });

  test('El catálogo se descarga solo cuando falta (si la app lo pide), y una sola vez por minuto', () async {
    await LocalDatabase.instance.reiniciar(ruta: inMemoryDatabasePath);
    final api = ApiFalsa();
    final c = OfflineController(OfflineRepository(api), descargaAutomatica: true)..usarSesion(_sesion);
    for (var i = 0; i < 50 && api.descargas == 0; i++) {
      await Future<void>.delayed(const Duration(milliseconds: 100)); // espera a que termine, aunque la máquina esté ocupada
    }
    await Future<void>.delayed(const Duration(milliseconds: 200));
    expect(api.descargas, 1);
    expect(c.hayCatalogo, isTrue);
    await c.actualizarSiVencido(); // ya hay copia y no venció: no vuelve a descargar
    expect(api.descargas, 1);
    c.dispose();
  });

  test('Sin la descarga automática (valor por defecto en las pruebas) no se pide nada al servidor', () async {
    await LocalDatabase.instance.reiniciar(ruta: inMemoryDatabasePath);
    final api = ApiFalsa();
    final c = OfflineController(OfflineRepository(api))..usarSesion(_sesion);
    await Future<void>.delayed(const Duration(milliseconds: 300));
    expect(api.descargas, 0);
    c.dispose();
  });
}
