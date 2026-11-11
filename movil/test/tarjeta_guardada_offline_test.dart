import 'package:fashionstore_movil/core/db/local_database.dart';
import 'package:fashionstore_movil/core/network/api_client.dart';
import 'package:fashionstore_movil/features/auth/data/sesion.dart';
import 'package:fashionstore_movil/features/offline/data/offline_repository.dart';
import 'package:fashionstore_movil/features/offline/presentation/offline_controller.dart';
import 'package:fashionstore_movil/features/offline/presentation/registrar_offline_screen.dart';
import 'package:fashionstore_movil/primer_parcial/reservas/data/medio_de_pago.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
// ignore: depend_on_referenced_packages
import 'package:sqflite_common/utils/utils.dart' as utilidades_sqflite;
import 'package:sqflite_common_ffi/sqflite_ffi.dart';

final _visa = {'id': 7, 'marca': 'Visa', 'ultimos4': '4242', 'exp_mes': 12, 'exp_anio': DateTime.now().year + 3};
final _vencida = {'id': 8, 'marca': 'Mastercard', 'ultimos4': '4444', 'exp_mes': 1, 'exp_anio': 2020};

/// Servidor falso: catálogo mínimo, tarjetas guardadas y registro de lo que recibe al sincronizar.
class ApiFalsa extends ApiClient {
  ApiFalsa() : super(obtenerToken: () async => null, renovarToken: () async => false);

  final enviadas = <Map<String, dynamic>>[];

  @override
  Future<Map<String, dynamic>> get(String ruta) async => {
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

  @override
  Future<List<dynamic>> getLista(String ruta) async => ruta == '/pagos/tarjetas' ? [_visa, _vencida] : [];

  @override
  Future<Map<String, dynamic>> post(String ruta, Map<String, dynamic> cuerpo, {bool autenticado = true}) async {
    final operaciones = (cuerpo['operaciones'] as List).cast<Map<String, dynamic>>();
    enviadas.addAll(operaciones);
    return {
      'resultados': [
        for (final o in operaciones) {'id': o['id'], 'estado': 'CONFIRMADA', 'mensaje': 'Compra cobrada y confirmada.', 'referencia': 'PED-1', 'comprobante': 'CMP-001-000001', 'detalle': null}
      ]
    };
  }
}

final _cliente = Sesion({
  'usuario': {'id': 5, 'nombre': 'Ana', 'apellidos': 'P', 'email': 'a@b.com', 'rol': 'Cliente'},
  'empresa': {'id': 1, 'codigo': 'EMP-A', 'razon_social': 'Moda'},
  'suscripcion': {
    'estado': 'ACTIVA',
    'plan': {'nombre': 'Básico', 'max_sucursales': 2, 'reportes_ia': false, 'offline': true},
  },
});

/// Las consultas a la base de datos real terminan fuera del reloj falso de testWidgets: cada paso necesita esperar y luego dar un pump.
Future<void> asentar(WidgetTester tester) async {
  for (var i = 0; i < 8; i++) {
    await tester.runAsync(() => Future<void>.delayed(const Duration(milliseconds: 40)));
    await tester.pump();
  }
}

void main() {
  sqfliteFfiInit();
  // ignore: deprecated_member_use
  utilidades_sqflite.lockWarningDuration = null; // sin el aviso de bloqueo de 10 s, que dejaría temporizadores pendientes
  databaseFactory = databaseFactoryFfi;

  test('Una tarjeta vencida no se ofrece sin conexión y su copia solo guarda marca, últimos 4 y vencimiento', () {
    final hoy = DateTime(2026, 11, 10);
    expect(TarjetaGuardada.desdeJson(_vencida).vigente(hoy), isFalse);
    expect(TarjetaGuardada(id: 1, marca: 'Visa', ultimos4: '4242', expMes: 11, expAnio: 2026).vigente(hoy), isTrue);
    expect(TarjetaGuardada.desdeJson(_visa).aJson().keys, unorderedEquals(['id', 'marca', 'ultimos4', 'exp_mes', 'exp_anio'])); // nunca número ni CVC
  });

  test('El cliente baja sus tarjetas guardadas junto con el catálogo y quedan en el dispositivo', () async {
    await LocalDatabase.instance.reiniciar(ruta: inMemoryDatabasePath);
    final repo = OfflineRepository(ApiFalsa());
    final c = OfflineController(repo)..usarSesion(_cliente);
    await Future<void>.delayed(const Duration(milliseconds: 200));
    expect(await repo.tarjetasLocales(), isEmpty);
    await c.descargarCatalogo();
    expect((await repo.tarjetasLocales()).map((t) => t['ultimos4']), ['4242', '4444']);
    c.dispose();
  });

  testWidgets('Comprar sin conexión: «Pagar con Visa…» exige autorizar el cobro y manda solo el id de la tarjeta y el total', (tester) async {
    final api = ApiFalsa();
    late OfflineController c;
    tester.view.physicalSize = const Size(800, 3000); // una pantalla alta: toda la lista queda construida y a la vista
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);
    await tester.runAsync(() async {
      await LocalDatabase.instance.reiniciar(ruta: inMemoryDatabasePath);
      final repo = OfflineRepository(api);
      await repo.guardarCatalogo(await api.get('/offline/catalogo')); // sin el caché de imágenes (no hay plugin de rutas en las pruebas)
      await repo.actualizarTarjetas();
      c = OfflineController(repo)..usarSesion(_cliente);
      c.simularSinConexion(true);
      await Future<void>.delayed(const Duration(milliseconds: 300));
    });
    await tester.pumpWidget(MaterialApp(home: Scaffold(body: ChangeNotifierProvider<OfflineController>.value(value: c, child: const RegistrarOfflineTab()))));
    await asentar(tester);

    Future<void> ver(Finder f) => tester.dragUntilVisible(f, find.byType(ListView).first, const Offset(0, -150)); // la lista construye solo lo que se ve

    await tester.tap(find.byType(DropdownButtonFormField<String>).first);
    await tester.pumpAndSettle();
    await tester.tap(find.text('Comprar (pago con tarjeta al sincronizar)').last);
    await tester.pumpAndSettle();
    final buscador = find.widgetWithText(TextField, 'Buscar prenda (nombre, SKU o código de barras)');
    await ver(buscador);
    await tester.enterText(buscador, 'CAM');
    await asentar(tester);
    await ver(find.textContaining('Camisa Oxford (S, Rojo)').first);
    await tester.tap(find.textContaining('Camisa Oxford (S, Rojo)').first);
    await tester.pump();
    final nit = find.widgetWithText(TextField, 'NIT o CI');
    await ver(nit);
    await tester.enterText(nit, '1234567');

    final visa = find.text('Pagar con Visa terminada en 4242 al volver la conexión');
    await ver(visa);
    expect(visa, findsOneWidget);
    expect(find.textContaining('Mastercard'), findsNothing); // la tarjeta vencida no se ofrece
    expect(find.text(msgTarjetaNueva), findsOneWidget);
    await tester.tap(visa);
    await tester.pump();
    await ver(find.textContaining('Autorizo el cobro de Bs'));
    expect(find.text('Autorizo el cobro de Bs 100.00 a esta tarjeta cuando se confirme mi compra.'), findsOneWidget);
    final registrar = find.text('Registrar compra en el dispositivo');
    await ver(registrar);
    await tester.tap(registrar);
    await asentar(tester);
    expect(find.text(msgAutorizar), findsOneWidget); // sin autorizar no se guarda
    expect(c.pendientes, isEmpty);

    final autorizo = find.textContaining('Autorizo el cobro');
    await ver(autorizo);
    await tester.tap(autorizo);
    await tester.pump();
    await ver(registrar);
    await tester.tap(registrar);
    await asentar(tester);
    final compra = c.operaciones.single;
    expect(compra.tipo, 'COMPRA');
    expect(compra.payload['tarjeta_guardada_id'], 7);
    expect(compra.payload['total_autorizado'], '100.00');
    expect(compra.payload.keys.where((k) => ['numero', 'cvc', 'exp_mes', 'exp_anio', 'tarjeta'].contains(k)), isEmpty);
    expect(compra.resumen, contains('se cobrará a Visa terminada en 4242'));
    c.dispose();
  });
}
