import 'dart:io';

import 'package:fashionstore_movil/features/offline/data/modelos.dart';
import 'package:fashionstore_movil/features/offline/data/resumen_turno.dart';
import 'package:flutter_test/flutter_test.dart';

OperacionLocal _venta(String id, String estado, String recibido, List<(int, int, String)> lineas) => OperacionLocal(
      id: id, empresaId: 1, sucursalId: 1, usuarioId: 5, tipo: 'VENTA_CONTADO',
      payload: {
        'items': [for (final l in lineas) {'variante_id': l.$1, 'cantidad': l.$2, 'precio_unitario': l.$3}],
        'monto_recibido': recibido,
      },
      estado: estado, intentos: 0, mensaje: '', referencia: null, comprobante: null, detalle: null, resumen: '', creadoEn: '2026-11-01T10:00:00Z',
    );

void main() {
  test('B2: cuenta ventas, efectivo, cambio y el desglose por estado, y deja de lado lo que no es venta', () {
    final r = ResumenTurno.desde([
      _venta('a', Estado.confirmada, '100.00', [(1, 2, '40.00')]), // total 80, cambio 20
      _venta('b', Estado.registradaLocal, '50.00', [(2, 1, '45.00')]), // total 45, cambio 5
      _venta('c', Estado.enConflicto, '200.00', [(3, 1, '190.00')]),
      OperacionLocal(
        id: 'r', empresaId: 1, sucursalId: 1, usuarioId: 5, tipo: 'RESERVA', payload: {}, estado: Estado.confirmada, intentos: 0, mensaje: '', referencia: null, comprobante: null, detalle: null, resumen: '', creadoEn: 'x',
      ),
    ]);
    expect(r.ventas, 3);
    expect(r.efectivoRecibido, 350);
    expect(r.totalVendido, 315);
    expect(r.cambio, 35);
    expect((r.porEstado[Estado.confirmada], r.porEstado[Estado.registradaLocal], r.porEstado[Estado.enConflicto], r.porEstado[Estado.rechazada]), (1, 1, 1, 0));
  });

  test('B2: el resumen se descarga como un PDF válido', () async {
    final carpeta = await Directory.systemTemp.createTemp('turno');
    final ruta = await ResumenTurno.desde([_venta('a', Estado.confirmada, '100.00', [(1, 2, '40.00')])]).aPdf(carpeta: carpeta.path, empresa: 'Moda Urbana', usuario: 'Ana');
    final bytes = await File(ruta).readAsBytes();
    expect(String.fromCharCodes(bytes.take(5)), '%PDF-');
    expect(bytes.length, greaterThan(800));
    await carpeta.delete(recursive: true);
  });
}
