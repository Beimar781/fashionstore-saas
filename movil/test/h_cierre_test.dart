import 'package:fashionstore_movil/core/db/local_database.dart';
import 'package:fashionstore_movil/core/network/api_client.dart';
import 'package:fashionstore_movil/features/offline/data/estado_legible.dart';
import 'package:fashionstore_movil/features/offline/data/modelos.dart';
import 'package:fashionstore_movil/features/offline/data/offline_repository.dart';
import 'package:fashionstore_movil/features/offline/presentation/offline_controller.dart';
import 'package:fashionstore_movil/features/offline/presentation/tareas_sucursal_screen.dart' show textoSinFilas;
import 'package:fashionstore_movil/primer_parcial/reservas/data/datos_entrega.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';

OperacionLocal _op(String tipo, String estado, String resumen) => OperacionLocal(
    id: 'op-1', empresaId: 1, sucursalId: 1, usuarioId: 5, tipo: tipo, payload: const {}, estado: estado, intentos: 0, mensaje: '', referencia: null,
    comprobante: null, detalle: null, resumen: resumen, creadoEn: '2026-11-11T10:00:00Z');

void main() {
  sqfliteFfiInit();
  databaseFactory = databaseFactoryFfi;

  test('Copia de tarjetas: guardar y apagar la red sin reabrir la entrega las ofrece; eliminar una, ya no', () async {
    await LocalDatabase.instance.reiniciar(ruta: inMemoryDatabasePath);
    final repo = OfflineRepository(ApiClient(obtenerToken: () async => null, renovarToken: () async => false));
    await repo.guardarTarjetas([
      {'id': 7, 'marca': 'Visa', 'ultimos4': '4242', 'exp_mes': 12, 'exp_anio': 2099},
      {'id': 8, 'marca': 'Mastercard', 'ultimos4': '4444', 'exp_mes': 11, 'exp_anio': 2099},
    ]);
    expect((await repo.tarjetasLocales()).map((t) => t['id']), [7, 8]);
    await repo.quitarTarjetaLocal(7);
    expect((await repo.tarjetasLocales()).map((t) => t['id']), [8]);
  });

  test('Estado legible de la compra pendiente', () {
    expect(estadoLegible(_op('COMPRA', Estado.registradaLocal, 'Compra: 1× Camisa · se cobrará a Visa terminada en 4242')), 'Pendiente de enviar · se cobrará a la Visa 4242 al reconectar');
    expect(estadoLegible(_op('COMPRA', Estado.registradaLocal, 'Compra: 1× Camisa')), 'Pendiente de enviar · quedará por pagar al reconectar');
    expect(estadoLegible(_op('COMPRA', Estado.enviada, '')), 'Enviando al servidor…');
    expect(estadoLegible(_op('RESERVA', Estado.registradaLocal, '')), 'Pendiente de enviar · se enviará al reconectar');
  });

  test('«No hay copia» no es lo mismo que «no hay ventas en el plazo»', () async {
    await LocalDatabase.instance.reiniciar(ruta: inMemoryDatabasePath);
    final repo = OfflineRepository(ApiClient(obtenerToken: () async => null, renovarToken: () async => false));
    final c = OfflineController(repo);
    expect(textoSinFilas(c, 'ventas', false), startsWith('Todavía no se descargó el catálogo con las ventas'));
    c.hayCatalogo = true;
    c.catalogoGeneradoEn = '2026-11-11T10:00:00Z';
    expect(textoSinFilas(c, 'ventas', false), startsWith('No hay ventas de esta sucursal dentro del plazo hasta la última descarga'));
    expect(textoSinFilas(c, 'ventas', true), 'No hay ventas descargadas con ese texto.');
    c.dispose();
  });

  test('NIT/CI: el mensaje explica la regla y es el mismo en la entrega y en el registro sin conexión', () {
    expect(const DatosEntrega().validar(), msgNit);
    expect(msgNit, 'Ingrese su NIT o CI (al menos 3 caracteres; consumidor final: su CI).');
    expect(const DatosEntrega(nitCi: '123').validar(), isNull);
  });
}
