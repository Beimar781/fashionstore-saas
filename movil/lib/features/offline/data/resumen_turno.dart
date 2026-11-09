import 'dart:io';

import 'package:pdf/pdf.dart';
import 'package:pdf/widgets.dart' as pw;

import 'modelos.dart';

/// B2 · «Resumen de mi turno»: lo vendido sin conexión en este dispositivo, calculado solo con los datos locales (solo lectura).
class ResumenTurno {
  ResumenTurno({required this.ventas, required this.efectivoRecibido, required this.cambio, required this.totalVendido, required this.porEstado});

  /// Resume las ventas de contado de la lista (las de otro tipo se ignoran).
  factory ResumenTurno.desde(Iterable<OperacionLocal> operaciones) {
    var ventas = 0;
    var recibido = 0.0;
    var total = 0.0;
    final porEstado = <String, int>{for (final e in Estado.todos) e: 0};
    for (final o in operaciones.where((o) => o.tipo == 'VENTA_CONTADO')) {
      ventas++;
      porEstado[o.estado] = (porEstado[o.estado] ?? 0) + 1;
      recibido += double.tryParse('${o.payload['monto_recibido']}') ?? 0;
      for (final i in ((o.payload['items'] as List?) ?? const []).cast<Map<String, dynamic>>()) {
        total += (double.tryParse('${i['precio_unitario']}') ?? 0) * (i['cantidad'] as int);
      }
    }
    return ResumenTurno(ventas: ventas, efectivoRecibido: recibido, cambio: recibido - total, totalVendido: total, porEstado: porEstado);
  }

  final int ventas;
  final double efectivoRecibido;
  final double cambio;
  final double totalVendido;
  final Map<String, int> porEstado;

  static const nombresEstado = {
    Estado.registradaLocal: 'Pendientes de enviar',
    Estado.enviada: 'Enviadas',
    Estado.confirmada: 'Confirmadas',
    Estado.rechazada: 'Rechazadas',
    Estado.enConflicto: 'En conflicto',
  };

  /// PDF del resumen para imprimir o compartir. Devuelve la ruta del archivo en la carpeta indicada.
  Future<String> aPdf({required String carpeta, required String empresa, required String usuario}) async {
    final doc = pw.Document();
    doc.addPage(pw.Page(
      pageFormat: PdfPageFormat.a4,
      build: (_) => pw.Column(crossAxisAlignment: pw.CrossAxisAlignment.start, children: [
        pw.Text(empresa, style: pw.TextStyle(fontSize: 20, fontWeight: pw.FontWeight.bold)),
        pw.Text('Resumen de mi turno', style: const pw.TextStyle(fontSize: 14)),
        pw.Text('$usuario · ${DateTime.now().toString().substring(0, 16)}'),
        pw.SizedBox(height: 14),
        pw.Text('Ventas registradas: $ventas'),
        pw.Text('Total vendido: Bs ${totalVendido.toStringAsFixed(2)}'),
        pw.Text('Efectivo recibido: Bs ${efectivoRecibido.toStringAsFixed(2)}'),
        pw.Text('Cambio entregado: Bs ${cambio.toStringAsFixed(2)}'),
        pw.SizedBox(height: 10),
        pw.Text('Por estado de sincronización', style: pw.TextStyle(fontWeight: pw.FontWeight.bold)),
        for (final e in nombresEstado.entries) pw.Text('${e.value}: ${porEstado[e.key] ?? 0}'),
        pw.SizedBox(height: 16),
        pw.Text('Generado por FashionStore. Datos locales de este dispositivo.', style: const pw.TextStyle(fontSize: 9)),
      ]),
    ));
    final archivo = File('$carpeta${Platform.pathSeparator}resumen-turno.pdf');
    await archivo.writeAsBytes(await doc.save());
    return archivo.path;
  }
}
