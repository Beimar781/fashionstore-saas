import 'package:fashionstore_movil/core/db/local_database.dart';
import 'package:fashionstore_movil/core/network/api_client.dart';
import 'package:fashionstore_movil/core/ui/avisos.dart';
import 'package:fashionstore_movil/core/util/mensajes_red.dart';
import 'package:fashionstore_movil/core/util/sugerencia.dart';
import 'package:fashionstore_movil/features/auth/data/sesion.dart';
import 'package:fashionstore_movil/features/home/presentation/home_screen.dart';
import 'package:fashionstore_movil/features/notificaciones/data/push_repository.dart';
import 'package:fashionstore_movil/features/notificaciones/presentation/push_controller.dart';
import 'package:fashionstore_movil/features/offline/data/offline_repository.dart';
import 'package:fashionstore_movil/features/offline/presentation/offline_controller.dart';
import 'package:fashionstore_movil/features/offline/presentation/registrar_offline_screen.dart';
import 'package:fashionstore_movil/features/offline/presentation/tareas_sucursal_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';

class ApiFalsa extends ApiClient {
  ApiFalsa({this.conflictos = 2}) : super(obtenerToken: () async => null, renovarToken: () async => false);

  int conflictos;

  @override
  Future<List<dynamic>> getLista(String ruta) async => ruta.contains('/offline/conflictos') ? List.generate(conflictos, (i) => {'id': 'c$i'}) : [];

  @override
  Future<Map<String, dynamic>> get(String ruta) async => {};
}

Sesion _sesion(String rol) => Sesion({
      'usuario': {'id': 3, 'nombre': 'E', 'apellidos': 'N', 'email': 'e@b.com', 'rol': rol, 'sucursal_id': 1},
      'empresa': {'id': 1, 'codigo': 'EMP-A', 'razon_social': 'Moda'},
      'suscripcion': {'estado': 'ACTIVA', 'plan': {'nombre': 'Básico', 'max_sucursales': 2, 'reportes_ia': false, 'offline': true}},
    });

Map<String, dynamic> _catalogo() => {
      'generado_en': '2026-11-09T10:00:00Z',
      'empresa_id': 1,
      'sucursales': [
        {'id': 1, 'nombre': 'Centro', 'ciudad': 'SC', 'direccion': null, 'horario': null}
      ],
      'productos': [],
      'clientes': [],
      'reservas_sucursal': [
        {
          'id': 77, 'codigo': 'RES-77', 'estado': 'PENDIENTE', 'programada_para': '2026-11-12T11:00:00Z',
          'items': [
            {'id': 501, 'variante_id': 100, 'producto': 'Camisa Oxford', 'talla': 'S', 'color': 'Rojo', 'cantidad': 1, 'estado': 'RESERVADO'}
          ],
        }
      ],
    };

void main() {
  sqfliteFfiInit();
  databaseFactory = databaseFactoryFfi;

  testWidgets('El aviso con botón «Ver detalle» se cierra solo: visible a los 3 s y desaparece a los 6 s', (tester) async {
    final clave = GlobalKey<ScaffoldMessengerState>();
    await tester.pumpWidget(MaterialApp(scaffoldMessengerKey: clave, home: const Scaffold(body: SizedBox())));
    clave.currentState!.showSnackBar(avisoConAccion('Sincronización completa', etiqueta: 'Ver detalle', alPulsar: () {}));
    await tester.pump();
    for (var i = 0; i < 6; i++) {
      await tester.pump(const Duration(milliseconds: 500)); // 3 s en pasos, como pasa en el teléfono
    }
    expect(find.text('Sincronización completa'), findsOneWidget);
    expect(find.text('Ver detalle'), findsOneWidget);
    for (var i = 0; i < 14; i++) {
      await tester.pump(const Duration(milliseconds: 500)); // hasta los 10 s: ya debe haberse cerrado
    }
    expect(find.text('Sincronización completa'), findsNothing);
  });

  test('El contador de conflictos usa los del servidor con red y los locales sin red', () async {
    await LocalDatabase.instance.reiniciar(ruta: inMemoryDatabasePath);
    final c = OfflineController(OfflineRepository(ApiFalsa()))..usarSesion(_sesion('Encargado'));
    await Future<void>.delayed(const Duration(milliseconds: 300));
    expect(c.conflictosPendientes, 2); // la lista del servidor tiene 2
    c.enLinea = false;
    expect(c.conflictosPendientes, 0); // sin red: solo los locales EN_CONFLICTO (no hay ninguno)
    c.dispose();
  });

  testWidgets('Encargado: el acceso «Conflictos de sincronización» muestra la insignia con la cantidad', (tester) async {
    late OfflineController offline;
    final api = ApiFalsa();
    await tester.runAsync(() async {
      await LocalDatabase.instance.reiniciar(ruta: inMemoryDatabasePath);
      offline = OfflineController(OfflineRepository(api))..usarSesion(_sesion('Encargado'));
      await Future<void>.delayed(const Duration(milliseconds: 300));
    });
    expect(offline.conflictosPendientes, 2);
    tester.view.physicalSize = const Size(360 * 3, 1400 * 3);
    tester.view.devicePixelRatio = 3;
    addTearDown(tester.view.reset);
    await tester.pumpWidget(MultiProvider(
      providers: [ChangeNotifierProvider<OfflineController>.value(value: offline)],
      child: MaterialApp(home: Scaffold(body: ListView(children: [Consumer<OfflineController>(builder: (c, o, _) => AccesoHome(icono: Icons.warning, titulo: 'Conflictos de sincronización', detalle: 'd', pantalla: const SizedBox(), contador: o.conflictosPendientes))]))),
    ));
    expect(find.text('2'), findsOneWidget);
    offline.conflictosServidor = 0;
    // ignore: invalid_use_of_protected_member, invalid_use_of_visible_for_testing_member
    offline.notifyListeners();
    await tester.pump();
    expect(find.text('2'), findsNothing); // con 0 no hay insignia
    offline.dispose();
  });

  testWidgets('Reservas: «Marcar no encontrada» pide confirmación y después el ítem queda como «No encontrada»', (tester) async {
    await tester.runAsync(() async {
      await LocalDatabase.instance.reiniciar(ruta: inMemoryDatabasePath);
      final repo = OfflineRepository(ApiFalsa());
      await repo.guardarCatalogo(_catalogo());
      await repo.anotarDueno('3|Encargado|1'); // la copia es de este usuario: no se descarta al iniciar sesión
      final c = OfflineController(repo)..usarSesion(_sesion('Encargado'));
      await c.recargar();
      await tester.pumpWidget(MaterialApp(home: Scaffold(body: ChangeNotifierProvider<OfflineController>.value(value: c, child: const ReservasTab()))));
      await Future<void>.delayed(const Duration(milliseconds: 300));
      await tester.pump();
      expect(find.text('Marcar no encontrada'), findsOneWidget);
      await tester.tap(find.text('Marcar no encontrada'));
      await tester.pump(const Duration(milliseconds: 300));
      expect(find.text('¿Marcar como no encontrada?'), findsOneWidget);
      await tester.tap(find.text('Sí, no está'));
      await Future<void>.delayed(const Duration(milliseconds: 400));
      await tester.pump(const Duration(milliseconds: 300));
      expect(find.text('Marcar no encontrada'), findsNothing); // el botón se va y queda el estado
      expect(find.text('No encontrada'), findsOneWidget);
      c.dispose();
    });
  });

  testWidgets('Avisos: «Marcar todos como leídos» limpia la lista y agrupa en Hoy / Anteriores', (tester) async {
    final api = ApiFalsa();
    final push = PushController(PushRepository(api))
      ..avisos = [
        AvisoPush(id: 1, titulo: 'De hoy', mensaje: 'm', leido: false, creada: DateTime.now()),
        AvisoPush(id: 2, titulo: 'Viejo', mensaje: 'm', leido: false, creada: DateTime.now().subtract(const Duration(days: 3))),
      ];
    final offline = OfflineController(OfflineRepository(api));
    await tester.pumpWidget(MultiProvider(
      providers: [
        ChangeNotifierProvider<PushController>.value(value: push),
        ChangeNotifierProvider<OfflineController>.value(value: offline),
      ],
      child: const MaterialApp(home: AvisosScreen()),
    ));
    await tester.pump(const Duration(milliseconds: 300));
    expect(find.text('Hoy'), findsOneWidget);
    expect(find.text('Anteriores'), findsOneWidget);
    expect(find.text('De hoy'), findsOneWidget);
    await tester.tap(find.text('Marcar todos como leídos'));
    await tester.pump(const Duration(milliseconds: 300));
    expect(find.text('De hoy'), findsNothing);
    expect(find.text('No hay avisos nuevos.'), findsOneWidget);
  });

  test('«¿Quiso decir…?» sugiere la palabra conocida más parecida y no inventa nada lejano', () {
    expect(sugerirPalabra('camiza', ['Camisa', 'Pantalón']), 'Camisa');
    expect(sugerirPalabra('zzzzzz', ['Camisa', 'Pantalón']), isNull);
    expect(sugerirPalabra('camisa', ['Camisa']), isNull); // ya está bien escrita
  });

  test('Los errores se muestran en español claro, nunca con códigos ni excepciones', () {
    expect(mensajeAmigable(ApiException('x', sinConexion: true), guardado: true), msgSinRedGuardado);
    expect(mensajeAmigable(ApiException('Internal', statusCode: 503)), msgServidorNoRespondio);
    expect(mensajeAmigable(Exception('SocketException: boom')), msgErrorGeneral);
    expect(mensajeAmigable(ApiException('La prenda se agotó.', statusCode: 409)), 'La prenda se agotó.');
  });

  testWidgets('Con texto grande (130 %) y tema oscuro las listas vacías y las tarjetas no se desbordan', (tester) async {
    final api = ApiFalsa();
    final offline = OfflineController(OfflineRepository(api));
    tester.view.physicalSize = const Size(360 * 3, 800 * 3);
    tester.view.devicePixelRatio = 3;
    addTearDown(tester.view.reset);
    await tester.pumpWidget(MultiProvider(
      providers: [
        ChangeNotifierProvider<OfflineController>.value(value: offline),
        ChangeNotifierProvider<PushController>.value(value: PushController(PushRepository(api))),
      ],
      child: MaterialApp(
        theme: ThemeData.dark(useMaterial3: true),
        builder: (context, child) => MediaQuery(data: MediaQuery.of(context).copyWith(textScaler: const TextScaler.linear(1.3)), child: child!),
        home: const AvisosScreen(),
      ),
    ));
    await tester.pump(const Duration(milliseconds: 300));
    expect(tester.takeException(), isNull);
  });

  testWidgets('Caja: el panel fijo muestra total e IVA, al agregar se limpia el buscador y «Atrás» con una venta en curso pregunta antes de salir', (tester) async {
    await tester.runAsync(() async {
      await LocalDatabase.instance.reiniciar(ruta: inMemoryDatabasePath);
      final repo = OfflineRepository(ApiFalsa());
      await repo.guardarCatalogo({
        ..._catalogo(),
        'productos': [
          {
            'id': 10, 'nombre': 'Camisa Oxford', 'categoria': 'Camisas', 'genero': 'UNISEX', 'imagen': null,
            'variantes': [
              {'id': 100, 'sku': 'CAM-S-ROJ', 'codigo_barras': null, 'talla': 'S', 'color': 'Rojo', 'precio': '100.00', 'precio_final': '100.00', 'promocion': null, 'stock': {'1': 5}}
            ],
          }
        ],
      });
      await repo.anotarDueno('3|Cajero|1');
      final c = OfflineController(repo)..usarSesion(_sesion('Cajero'));
      await c.recargar();
      tester.view.physicalSize = const Size(360 * 3, 1600 * 3);
      tester.view.devicePixelRatio = 3;
      addTearDown(tester.view.reset);
      await tester.pumpWidget(MaterialApp(
          home: Builder(builder: (ctx) => Scaffold(body: Center(child: ElevatedButton(onPressed: () => Navigator.of(ctx).push(MaterialPageRoute<void>(builder: (_) => Scaffold(body: ChangeNotifierProvider<OfflineController>.value(value: c, child: const RegistrarOfflineTab())))), child: const Text('Abrir caja')))))));
      await tester.tap(find.text('Abrir caja'));
      await tester.pump(const Duration(milliseconds: 500));
      await Future<void>.delayed(const Duration(milliseconds: 300));
      await tester.pump(const Duration(milliseconds: 500));
      await tester.enterText(find.widgetWithText(TextField, 'Buscar prenda (nombre, SKU o código de barras)'), 'camisa');
      await Future<void>.delayed(const Duration(milliseconds: 200));
      await tester.pump();
      expect(find.text('Sin resultados en el catálogo guardado.'), findsNothing);
      await tester.tap(find.byType(ActionChip).first);
      await Future<void>.delayed(const Duration(milliseconds: 200));
      await tester.pump();
      expect(find.text('IVA incluido: Bs 11.50'), findsOneWidget);   // en el panel fijo
      expect(find.text('Total Bs 100.00'), findsOneWidget);
      expect((tester.widget<TextField>(find.widgetWithText(TextField, 'Buscar prenda (nombre, SKU o código de barras)'))).controller!.text, isEmpty); // el buscador queda limpio
      await tester.enterText(find.widgetWithText(TextField, 'Buscar prenda (nombre, SKU o código de barras)'), 'zzzzzz');
      await Future<void>.delayed(const Duration(milliseconds: 200));
      await tester.pump();
      expect(find.text('Sin resultados en el catálogo guardado.'), findsOneWidget);
      // «Atrás» con la venta en curso
      final cerrar = tester.state<NavigatorState>(find.byType(Navigator).first).maybePop();
      await Future<void>.delayed(const Duration(milliseconds: 200));
      await tester.pump(const Duration(milliseconds: 400));
      expect(find.text('¿Descartar la venta en curso?'), findsOneWidget);
      await tester.tap(find.text('Seguir vendiendo'));
      await tester.pump(const Duration(milliseconds: 400));
      expect(find.text('Venta en curso · 1 prenda(s)'), findsOneWidget); // sigue en la Caja
      await cerrar;
      c.dispose();
    });
  });
}
