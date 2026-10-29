import 'package:fashionstore_movil/core/db/local_database.dart';
import 'package:fashionstore_movil/core/network/api_client.dart';
import 'package:fashionstore_movil/core/util/uuid.dart';
import 'package:fashionstore_movil/features/auth/data/sesion.dart';
import 'package:fashionstore_movil/features/offline/data/modelos.dart';
import 'package:fashionstore_movil/features/offline/data/offline_repository.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';

/// API simulada en memoria: guarda lo que se le envía y responde lo que la prueba le indique.
class ApiFalsa extends ApiClient {
  ApiFalsa() : super(obtenerToken: () async => null, renovarToken: () async => false);

  Map<String, dynamic> Function(Map<String, dynamic> cuerpo)? alSincronizar;
  List<dynamic> operacionesDelServidor = [];
  ApiException? fallo;
  final List<Map<String, dynamic>> enviados = [];

  @override
  Future<Map<String, dynamic>> post(String ruta, Map<String, dynamic> cuerpo, {bool autenticado = true}) async {
    if (fallo != null) throw fallo!;
    enviados.add(cuerpo);
    return alSincronizar!(cuerpo);
  }

  @override
  Future<List<dynamic>> getLista(String ruta) async {
    if (fallo != null) throw fallo!;
    return operacionesDelServidor;
  }
}

Map<String, dynamic> _catalogo() => {
      'generado_en': '2026-10-29T10:00:00+00:00',
      'empresa_id': 1,
      'sucursales': [
        {'id': 1, 'nombre': 'Centro', 'ciudad': 'Santa Cruz', 'direccion': 'Av. 1', 'horario': '9:00-20:00'},
      ],
      'productos': [
        {
          'id': 10, 'nombre': 'Camisa Oxford', 'categoria': 'Camisas', 'genero': 'UNISEX', 'imagen': null,
          'variantes': [
            {'id': 100, 'sku': 'CAM-S-ROJ', 'codigo_barras': '7770001', 'talla': 'S', 'color': 'Rojo', 'precio': '100.00', 'precio_final': '80.00', 'promocion': 'Liquidación', 'stock': {'1': 5}},
            {'id': 101, 'sku': 'CAM-M-AZU', 'codigo_barras': null, 'talla': 'M', 'color': 'Azul', 'precio': '100.00', 'precio_final': '100.00', 'promocion': null, 'stock': {'1': 2}},
          ],
        },
      ],
      'clientes': [
        {'id': 7, 'nombre': 'Ana Cliente', 'email': 'ana@tienda.com'},
      ],
    };

Map<String, dynamic> _resultado(String id, String estado, {String? referencia, String? comprobante, Map<String, dynamic>? detalle, String mensaje = ''}) =>
    {'id': id, 'estado': estado, 'mensaje': mensaje, 'referencia': referencia, 'comprobante': comprobante, 'detalle': detalle, 'ya_procesada': false};

void main() {
  sqfliteFfiInit();
  databaseFactory = databaseFactoryFfi;

  late ApiFalsa api;
  late OfflineRepository repo;

  setUp(() async {
    await LocalDatabase.instance.reiniciar(ruta: inMemoryDatabasePath);
    api = ApiFalsa();
    repo = OfflineRepository(api);
  });

  Future<OperacionLocal> venta({int cantidad = 1}) => repo.registrar(
        tipo: 'VENTA_CONTADO',
        payload: {'items': [{'variante_id': 100, 'cantidad': cantidad}], 'monto_recibido': '80.00'},
        sucursalId: 1,
        resumen: 'Venta de contado',
        usuarioId: 5,
        empresaId: 1,
      );

  test('CU-37: el catálogo descargado se guarda y se busca sin conexión, con la fecha de la descarga (RN16)', () async {
    expect(await repo.hayCatalogo(), isFalse);
    await repo.guardarCatalogo(_catalogo());
    expect(await repo.hayCatalogo(), isTrue);
    expect(await repo.catalogoGeneradoEn(), '2026-10-29T10:00:00+00:00');
    expect((await repo.buscar('camisa')).length, 2);
    final porCodigo = await repo.buscar('7770001');
    expect(porCodigo.single.variante.sku, 'CAM-S-ROJ');
    expect(porCodigo.single.variante.precioFinal, '80.00');
    expect(porCodigo.single.variante.stockEn(1), 5);
    expect((await repo.buscar('pantalón')), isEmpty);
    expect((await repo.sucursales()).single.nombre, 'Centro');
    expect((await repo.clientes()).single.email, 'ana@tienda.com');
  });

  test('Una nueva descarga reemplaza el catálogo anterior', () async {
    await repo.guardarCatalogo(_catalogo());
    final nuevo = _catalogo()..['productos'] = [];
    await repo.guardarCatalogo(nuevo);
    expect(await repo.hayCatalogo(), isFalse);
  });

  test('RN11: toda operación recibe un UUID del dispositivo y queda REGISTRADA_LOCAL con empresa, sucursal y usuario', () async {
    final a = await venta();
    final b = await venta();
    expect(RegExp(r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$').hasMatch(a.id), isTrue);
    expect(a.id, isNot(b.id));
    final guardadas = await repo.operaciones(5, 1);
    expect(guardadas.length, 2);
    expect((guardadas.first.estado, guardadas.first.empresaId, guardadas.first.sucursalId, guardadas.first.usuarioId), (Estado.registradaLocal, 1, 1, 5));
    expect(await repo.operaciones(6, 1), isEmpty); // cada usuario ve las suyas
    expect(await repo.operaciones(5, 2), isEmpty); // y cada empresa las suyas
  });

  test('RNF03: las operaciones sobreviven al cierre de la app', () async {
    final ruta = '${Uri.directory(databaseFactoryFfi.hashCode.toString()).path}persistencia_test.db';
    await LocalDatabase.instance.reiniciar(ruta: ruta);
    await databaseFactory.deleteDatabase(ruta);
    final op = await venta();
    await LocalDatabase.instance.reiniciar(ruta: ruta); // se cierra y se vuelve a abrir
    final tras = await OfflineRepository(api).operaciones(5, 1);
    expect(tras.map((o) => o.id), [op.id]);
    await LocalDatabase.instance.reiniciar(ruta: inMemoryDatabasePath);
    await databaseFactory.deleteDatabase(ruta);
  });

  test('CU-38: al sincronizar la operación pasa a CONFIRMADA y guarda su referencia y comprobante', () async {
    final op = await venta();
    api.alSincronizar = (c) => {
          'resultados': [_resultado(op.id, 'CONFIRMADA', referencia: 'PED-ABC', comprobante: 'CMP-001-000001', mensaje: 'Operación confirmada.')],
          'sincronizado_en': '2026-10-29T11:00:00Z',
        };
    final r = await repo.sincronizar(5, 1);
    expect((r.enviadas, r.confirmadas, r.sinConexion), (1, 1, false));
    final o = (await repo.operaciones(5, 1)).single;
    expect((o.estado, o.referencia, o.comprobante, o.intentos), (Estado.confirmada, 'PED-ABC', 'CMP-001-000001', 1));
    expect(api.enviados.single['operaciones'].single['id'], op.id); // viajó con su UUID
    expect(await repo.ultimaSincronizacion(), isNotNull);
  });

  test('RN12 y RNF06: sin conexión la operación NO se pierde, vuelve a REGISTRADA_LOCAL y se reintenta con el mismo UUID', () async {
    final op = await venta();
    api.fallo = ApiException('Sin conexión con el servidor.', sinConexion: true);
    final r = await repo.sincronizar(5, 1);
    expect(r.sinConexion, isTrue);
    expect(r.error, contains('siguen guardadas'));
    var o = (await repo.operaciones(5, 1)).single;
    expect((o.estado, o.intentos, o.id), (Estado.registradaLocal, 1, op.id));
    // vuelve la conexión: se reenvía la misma operación (el servidor no la duplica, RNF05)
    api.fallo = null;
    api.alSincronizar = (c) => {
          'resultados': [_resultado(op.id, 'CONFIRMADA', referencia: 'PED-1')],
          'sincronizado_en': '2026-10-29T11:00:00Z',
        };
    await repo.sincronizar(5, 1);
    o = (await repo.operaciones(5, 1)).single;
    expect((o.estado, o.intentos), (Estado.confirmada, 2));
    expect(api.enviados.single['operaciones'].single['id'], op.id);
  });

  test('Un error pasajero del servidor deja la operación para reintentar; un rechazo queda registrado', () async {
    final a = await venta();
    final b = await venta();
    api.alSincronizar = (c) => {
          'resultados': [_resultado(a.id, 'ERROR', mensaje: 'reintente'), _resultado(b.id, 'RECHAZADA', mensaje: 'El monto recibido es menor al total de la venta.')],
          'sincronizado_en': '2026-10-29T11:00:00Z',
        };
    final r = await repo.sincronizar(5, 1);
    expect((r.reintentar, r.rechazadas), (1, 1));
    final ops = {for (final o in await repo.operaciones(5, 1)) o.id: o};
    expect(ops[a.id]!.estado, Estado.registradaLocal);
    expect((ops[b.id]!.estado, ops[b.id]!.mensaje), (Estado.rechazada, 'El monto recibido es menor al total de la venta.'));
  });

  test('RN14 y CU-39: un conflicto guarda el detalle y cambia de estado cuando el Encargado lo resuelve', () async {
    final op = await venta(cantidad: 9);
    final faltantes = {
      'faltantes': [
        {'variante_id': 100, 'producto': 'Camisa Oxford', 'talla': 'S', 'color': 'Rojo', 'solicitadas': 9, 'disponibles': 5},
      ],
    };
    api.alSincronizar = (c) => {'resultados': [_resultado(op.id, 'EN_CONFLICTO', detalle: faltantes)], 'sincronizado_en': '2026-10-29T11:00:00Z'};
    final r = await repo.sincronizar(5, 1);
    expect(r.enConflicto, 1);
    var o = (await repo.operaciones(5, 1)).single;
    expect(o.estado, Estado.enConflicto);
    expect(o.faltantes.single['disponibles'], 5);
    // el Encargado la resuelve en el servidor; al consultar, el dispositivo se entera
    api.operacionesDelServidor = [
      {'id': op.id, 'estado': 'CONFIRMADA', 'mensaje': 'Operación confirmada. Resuelta por reintento.', 'referencia': 'PED-9', 'comprobante': 'CMP-001-000002', 'detalle': null},
    ];
    await repo.refrescarEstados(5, 1);
    o = (await repo.operaciones(5, 1)).single;
    expect((o.estado, o.referencia), (Estado.confirmada, 'PED-9'));
    expect(o.detalle, isNull);
  });

  Future<OperacionLocal> compra() => repo.registrar(
        tipo: 'COMPRA',
        payload: {'sucursal_id': 1, 'items': [{'variante_id': 100, 'cantidad': 1}]},
        sucursalId: 1,
        resumen: 'Compra: 1× Camisa Oxford',
        usuarioId: 5,
        empresaId: 1,
      );

  test('Fase K: la compra del cliente sin conexión queda REGISTRADA_LOCAL sin datos de tarjeta y, si ya no alcanza, se le avisa que no se cobró nada', () async {
    final op = await compra();
    expect(op.estado, Estado.registradaLocal);
    expect(op.payload.keys, unorderedEquals(['sucursal_id', 'items'])); // nada de tarjeta: el pago se hace en línea
    api.alSincronizar = (c) => {'resultados': [_resultado(op.id, 'EN_CONFLICTO', detalle: {'faltantes': []})], 'sincronizado_en': '2026-10-29T11:00:00Z'};
    final r = await repo.sincronizar(5, 1);
    expect(r.enConflicto, 1);
    expect(r.avisos, ['Su compra no se pudo realizar porque la prenda se agotó. No se le cobró nada.']);
  });

  test('Fase K: con stock, la compra queda confirmada y se avisa al cliente que ya puede pagarla con tarjeta', () async {
    final op = await compra();
    api.alSincronizar = (c) => {'resultados': [_resultado(op.id, 'CONFIRMADA', referencia: 'PED-77', mensaje: 'Operación confirmada.')], 'sincronizado_en': '2026-10-29T11:00:00Z'};
    final r = await repo.sincronizar(5, 1);
    expect(r.avisos, ['Su compra PED-77 está lista: págela con tarjeta en «Mis compras».']);
    final v = await venta();
    api.alSincronizar = (c) => {'resultados': [_resultado(v.id, 'EN_CONFLICTO', detalle: {'faltantes': []})], 'sincronizado_en': '2026-10-29T11:00:00Z'};
    expect((await repo.sincronizar(5, 1)).avisos, isEmpty); // la venta de caja la resuelve el personal, no es un aviso del cliente
  });

  test('RN12: solo se quitan del dispositivo las operaciones que el servidor ya confirmó o rechazó', () async {
    final pendiente = await venta();
    final confirmada = await venta();
    final rechazada = await venta();
    final conflicto = await venta();
    api.alSincronizar = (c) => {
          'resultados': [
            _resultado(confirmada.id, 'CONFIRMADA', referencia: 'P1'),
            _resultado(rechazada.id, 'RECHAZADA'),
            _resultado(conflicto.id, 'EN_CONFLICTO'),
            _resultado(pendiente.id, 'ERROR'),
          ],
          'sincronizado_en': '2026-10-29T11:00:00Z',
        };
    await repo.sincronizar(5, 1);
    expect(await repo.limpiarTerminadas(5, 1), 2);
    final quedan = (await repo.operaciones(5, 1)).map((o) => o.estado).toSet();
    expect(quedan, {Estado.registradaLocal, Estado.enConflicto});
  });

  test('Lo registrado sin conexión descuenta del stock local para no ofrecerlo dos veces', () async {
    await repo.guardarCatalogo(_catalogo());
    await repo.comprometerStock([{'variante_id': 100, 'cantidad': 3}], 1);
    expect((await repo.buscar('CAM-S-ROJ')).single.variante.stockEn(1), 2);
    await repo.comprometerStock([{'variante_id': 100, 'cantidad': 9}], 1);
    expect((await repo.buscar('CAM-S-ROJ')).single.variante.stockEn(1), 0); // nunca queda negativo
  });

  test('El UUID v4 generado es único y tiene el formato estándar', () {
    final ids = {for (var i = 0; i < 500; i++) generarUuid()};
    expect(ids.length, 500);
    expect(ids.every((u) => u.length == 36 && u[14] == '4'), isTrue);
  });

  test('La sesión sabe a qué empresa y sucursal pertenece y qué incluye su plan', () {
    final s = Sesion({
      'usuario': {'id': 7, 'nombre': 'Ana', 'apellidos': 'Suárez', 'email': 'c@t.com', 'rol': 'Cajero', 'sucursal_id': 3, 'sucursal_nombre': 'Centro'},
      'empresa': {'id': 2, 'codigo': 'EMP-A', 'razon_social': 'Moda', 'estado': 'ACTIVA'},
      'suscripcion': {'estado': 'ACTIVA', 'fecha_inicio': '2026-10-25', 'fecha_vencimiento': '2027-10-25', 'plan': {'nombre': 'Básico', 'max_sucursales': 2, 'offline': true, 'reportes_ia': false}},
      'panel': 'punto_venta',
      'restringido': false,
    });
    expect((s.empresaId, s.sucursalId, s.offlineHabilitado, s.iaHabilitada), (2, 3, true, false));
  });
}
