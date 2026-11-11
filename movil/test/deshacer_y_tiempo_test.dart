import 'package:fashionstore_movil/core/db/local_database.dart';
import 'package:fashionstore_movil/core/network/api_client.dart';
import 'package:fashionstore_movil/features/auth/data/sesion.dart';
import 'package:fashionstore_movil/features/offline/data/linea_de_tiempo.dart';
import 'package:fashionstore_movil/features/offline/data/modelos.dart';
import 'package:fashionstore_movil/features/offline/data/offline_repository.dart';
import 'package:fashionstore_movil/features/offline/presentation/offline_controller.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';

class ApiFalsa extends ApiClient {
  ApiFalsa() : super(obtenerToken: () async => null, renovarToken: () async => false);

  @override
  Future<Map<String, dynamic>> post(String ruta, Map<String, dynamic> cuerpo, {bool autenticado = true}) async =>
      throw ApiException('Sin conexión con el servidor.', sinConexion: true);

  @override
  Future<List<dynamic>> getLista(String ruta) async => [];
}

final _sesion = Sesion({
  'usuario': {'id': 5, 'nombre': 'Luis', 'apellidos': 'P', 'email': 'e@b.com', 'rol': 'Encargado', 'sucursal_id': 1},
  'empresa': {'id': 1, 'codigo': 'EMP-A', 'razon_social': 'Moda'},
  'suscripcion': {'estado': 'ACTIVA', 'plan': {'nombre': 'Básico', 'max_sucursales': 2, 'reportes_ia': false, 'offline': true}},
});

Map<String, dynamic> _catalogo() => {
      'generado_en': '2026-11-09T10:00:00Z',
      'empresa_id': 1,
      'sucursales': [{'id': 1, 'nombre': 'Centro', 'ciudad': 'SC', 'direccion': null, 'horario': null}],
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
      'ventas_recientes': [
        {
          'comprobante': 'CMP-001-000007', 'pagado_en': '2026-11-08T10:00:00Z', 'total': '200.00', 'vence_el': '2026-11-23T10:00:00Z',
          'items': [{'pedido_item_id': 31, 'producto': 'Camisa Oxford', 'talla': 'S', 'color': 'Rojo', 'vendida': 2, 'devolvible': 2, 'precio_final': '100.00'}],
        }
      ],
      'reservas_sucursal': [],
    };

OperacionLocal _op({String estado = Estado.registradaLocal, String tipo = 'VENTA_CONTADO', Map<String, dynamic>? payload}) => OperacionLocal(
      id: 'op-1', empresaId: 1, sucursalId: 1, usuarioId: 5, tipo: tipo, payload: payload ?? {}, estado: estado, intentos: 0, mensaje: '', referencia: null,
      comprobante: null, detalle: null, resumen: 'Venta de prueba', creadoEn: '2026-11-10T10:00:00Z');

Map<String, Object?> _intento(int n, String resultado, {String codigo = '200', String motivo = ''}) =>
    {'operacion_id': 'op-1', 'tipo': 'VENTA_CONTADO', 'intento': n, 'fecha': '2026-11-10T10:0$n:00Z', 'resultado': resultado, 'codigo': codigo, 'motivo': motivo};

void main() {
  sqfliteFfiInit();
  databaseFactory = databaseFactoryFfi;

  group('Línea de tiempo (D5)', () {
    test('una operación pendiente solo está registrada en el dispositivo', () {
      final pasos = lineaDeTiempo(_op(), [], dispositivo: 'este teléfono Android');
      expect(pasos.map((p) => p.texto), ['Registrada en este teléfono Android', 'Pendiente: se enviará sola al volver la conexión']);
    });

    test('cuenta cada envío con su resultado y termina en confirmada', () {
      final pasos = lineaDeTiempo(_op(estado: Estado.confirmada), [_intento(2, 'CONFIRMADA'), _intento(1, 'SIN_RESPUESTA', codigo: 'SIN_RED')], dispositivo: 'x');
      expect(pasos.map((p) => p.texto), ['Registrada en x', 'Envío 1: el servidor no respondió (SIN_RED); se reintentará', 'Envío 2: confirmada por el servidor']);
      expect(pasos.last.tipo, 'ok');
    });

    test('un conflicto resuelto por el Encargado termina en resuelta', () {
      final conflicto = _intento(1, 'EN_CONFLICTO', motivo: 'No hay existencias suficientes');
      expect(lineaDeTiempo(_op(estado: Estado.confirmada), [conflicto]).last.texto, 'Resuelta por el Encargado: reintentada y confirmada');
      expect(lineaDeTiempo(_op(estado: Estado.rechazada), [conflicto]).last.texto, 'Resuelta por el Encargado: descartada');
      expect(lineaDeTiempo(_op(estado: Estado.enConflicto), [conflicto]).last.tipo, 'warn');
    });
  });

  group('Deshacer (D5)', () {
    late OfflineRepository repo;
    setUp(() async {
      await LocalDatabase.instance.reiniciar(ruta: inMemoryDatabasePath);
      repo = OfflineRepository(ApiFalsa());
      await repo.guardarCatalogo(_catalogo());
    });

    Future<int> stock() async => (await repo.buscar('CAM-S-ROJ')).single.variante.stock[1]!;

    test('una venta sin enviar sale de la cola y su stock vuelve', () async {
      final venta = await repo.registrar(tipo: 'VENTA_CONTADO', payload: {'items': [{'variante_id': 100, 'cantidad': 2}]}, sucursalId: 1, resumen: 'Venta', usuarioId: 5, empresaId: 1);
      await repo.comprometerStock([{'variante_id': 100, 'cantidad': 2}], 1);
      expect(await stock(), 3);
      expect(await repo.deshacerOperacion(venta), isTrue);
      expect(await stock(), 5);
      expect(await repo.operaciones(5, 1), isEmpty);
    });

    test('recepción, ajuste y devolución se revierten con su efecto contrario', () async {
      final recepcion = await repo.registrar(tipo: 'RECEPCION', payload: {'variante_id': 100, 'cantidad': 4, 'referencia': 'X'}, sucursalId: 1, resumen: 'R', usuarioId: 5, empresaId: 1);
      await repo.moverStockLocal(100, 1, 4);
      await repo.deshacerOperacion(recepcion);
      expect(await stock(), 5);
      final ajuste = await repo.registrar(tipo: 'AJUSTE_INVENTARIO', payload: {'variante_id': 100, 'diferencia': -2, 'motivo': 'MERMA', 'nota': ''}, sucursalId: 1, resumen: 'A', usuarioId: 5, empresaId: 1);
      await repo.moverStockLocal(100, 1, -2);
      await repo.deshacerOperacion(ajuste);
      expect(await stock(), 5);
      final devolucion = await repo.registrar(
          tipo: 'DEVOLUCION', payload: {'comprobante': 'CMP-001-000007', 'items': [{'pedido_item_id': 31, 'cantidad': 2}]}, sucursalId: 1, resumen: 'D', usuarioId: 5, empresaId: 1);
      await repo.descontarDevolvible('CMP-001-000007', {31: 2});
      await repo.deshacerOperacion(devolucion);
      expect(((await repo.ventasRecientes()).single['items'] as List).single['devolvible'], 2);
    });

    test('lo ya enviado, la atención de reservas y el cobro de una reserva no se deshacen', () async {
      expect(repo.puedeDeshacer(_op(estado: Estado.enviada)), isFalse);
      expect(repo.puedeDeshacer(_op(estado: Estado.confirmada)), isFalse);
      expect(repo.puedeDeshacer(_op(tipo: 'ATENDER_RESERVA')), isFalse);
      expect(repo.puedeDeshacer(_op(tipo: 'PREPARAR_RESERVA')), isFalse);
      expect(repo.puedeDeshacer(_op(payload: {'reserva_codigo': 'RSV-1'})), isFalse);
      expect(repo.puedeDeshacer(_op()), isTrue);
    });

    test('el controlador avisa y refresca al deshacer', () async {
      final c = OfflineController(repo)..usarSesion(_sesion);
      await Future<void>.delayed(const Duration(milliseconds: 200));
      c.simularSinConexion(true);
      final avisos = <String>[];
      c.alAvisar = avisos.add;
      await c.registrar(tipo: 'VENTA_CONTADO', payload: {'items': [{'variante_id': 100, 'cantidad': 1}]}, sucursalId: 1, resumen: 'Venta');
      expect(await stock(), 4);
      while (c.sincronizando) {
        await Future<void>.delayed(const Duration(milliseconds: 20));
      }
      expect(await c.deshacer(c.pendientes.single), isTrue);
      expect(await stock(), 5);
      expect(c.operaciones, isEmpty);
      expect(avisos.last, contains('el inventario local volvió a como estaba'));
      c.dispose();
      ApiClient.simularSinConexion = false;
    });
  });
}
