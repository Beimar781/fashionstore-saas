import 'dart:io';
import '../../../core/util/iva.dart';

import 'package:pdf/pdf.dart';
import 'package:pdf/widgets.dart' as pw;

import 'modelos.dart';

/// B1 · Comprobante provisional de una venta de contado registrada sin conexión. Se arma en el dispositivo, con numeración local
/// `LOC-<sucursal>-<código corto del UUID>`. Es válido una vez sincronizada la venta; al confirmarse, la venta muestra su número oficial `CMP-…`.
class ComprobanteProvisional {
  /// Número local: la sucursal con tres cifras y los primeros 6 caracteres del UUID de la operación (únicos en el dispositivo).
  static String numero(int? sucursalId, String operacionId) =>
      'LOC-${(sucursalId ?? 0).toString().padLeft(3, '0')}-${operacionId.replaceAll('-', '').substring(0, 6).toUpperCase()}';

  /// PDF con el detalle, el total, el efectivo recibido y el cambio. Devuelve la ruta del archivo en la carpeta indicada.
  static Future<String> aPdf(OperacionLocal o, {required String carpeta, required String empresa, required String Function(int varianteId) nombreDe, int ivaPorcentaje = 13}) async {
    final items = ((o.payload['items'] as List?) ?? const []).cast<Map<String, dynamic>>();
    final recibido = double.tryParse('${o.payload['monto_recibido']}') ?? 0;
    var total = 0.0;
    final filas = <List<String>>[];
    for (final i in items) {
      final precio = double.tryParse('${i['precio_unitario']}') ?? 0;
      final cantidad = i['cantidad'] as int;
      total += precio * cantidad;
      filas.add([nombreDe(i['variante_id'] as int), '$cantidad', precio.toStringAsFixed(2), (precio * cantidad).toStringAsFixed(2)]);
    }
    final local = numero(o.sucursalId, o.id);
    final doc = pw.Document();
    doc.addPage(pw.Page(
      pageFormat: PdfPageFormat.a5,
      build: (_) => pw.Column(crossAxisAlignment: pw.CrossAxisAlignment.start, children: [
        pw.Text(empresa, style: pw.TextStyle(fontSize: 16, fontWeight: pw.FontWeight.bold)),
        pw.Text('COMPROBANTE PROVISIONAL $local', style: pw.TextStyle(fontSize: 12, fontWeight: pw.FontWeight.bold)),
        pw.Text('Fecha del dispositivo: ${o.creadoEn.substring(0, 16).replaceFirst('T', ' ')}'),
        pw.SizedBox(height: 10),
        pw.TableHelper.fromTextArray(headers: ['Prenda', 'Cant.', 'Precio', 'Subtotal'], data: filas, cellStyle: const pw.TextStyle(fontSize: 9), headerStyle: pw.TextStyle(fontSize: 9, fontWeight: pw.FontWeight.bold)),
        pw.SizedBox(height: 8),
        pw.Text('Total: Bs ${total.toStringAsFixed(2)}'),
        pw.Text('IVA incluido: Bs ${ivaIncluido(total, ivaPorcentaje)}'),
        pw.Text('Efectivo recibido: Bs ${recibido.toStringAsFixed(2)}'),
        pw.Text('Cambio: Bs ${(recibido - total).toStringAsFixed(2)}'),
        pw.SizedBox(height: 12),
        pw.Text('Válido una vez sincronizada la venta.', style: pw.TextStyle(fontSize: 10, fontStyle: pw.FontStyle.italic)),
      ]),
    ));
    final archivo = File('$carpeta${Platform.pathSeparator}$local.pdf');
    await archivo.writeAsBytes(await doc.save());
    return archivo.path;
  }
}
