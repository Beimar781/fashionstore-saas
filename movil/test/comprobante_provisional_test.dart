import 'dart:io';

import 'package:fashionstore_movil/features/offline/data/comprobante_provisional.dart';
import 'package:fashionstore_movil/features/offline/data/modelos.dart';
import 'package:flutter_test/flutter_test.dart';

OperacionLocal _venta() => OperacionLocal(
      id: 'a1b2c3d4-0000-4000-8000-000000000001', empresaId: 1, sucursalId: 7, usuarioId: 5, tipo: 'VENTA_CONTADO',
      payload: {
        'items': [
          {'variante_id': 100, 'cantidad': 2, 'precio_unitario': '40.00'},
          {'variante_id': 101, 'cantidad': 1, 'precio_unitario': '90.00'},
        ],
        'monto_recibido': '200.00',
      },
      estado: Estado.registradaLocal, intentos: 0, mensaje: '', referencia: null, comprobante: null, detalle: null, resumen: '', creadoEn: '2026-11-01T10:00:00Z',
    );

void main() {
  test('B1: la numeración local es LOC-<sucursal>-<código corto del UUID>', () {
    expect(ComprobanteProvisional.numero(7, 'a1b2c3d4-0000-4000-8000-000000000001'), 'LOC-007-A1B2C3');
    expect(ComprobanteProvisional.numero(null, 'ffeedd11-0000-4000-8000-000000000002'), 'LOC-000-FFEEDD');
  });

  test('B1: el comprobante provisional se genera en el dispositivo como un PDF válido', () async {
    final carpeta = await Directory.systemTemp.createTemp('provisional');
    final ruta = await ComprobanteProvisional.aPdf(_venta(), carpeta: carpeta.path, empresa: 'Moda Urbana', nombreDe: (id) => 'Prenda $id');
    expect(ruta.endsWith('LOC-007-A1B2C3.pdf'), isTrue);
    final bytes = await File(ruta).readAsBytes();
    expect(String.fromCharCodes(bytes.take(5)), '%PDF-');
    expect(bytes.length, greaterThan(900));
    await carpeta.delete(recursive: true);
  });
}
