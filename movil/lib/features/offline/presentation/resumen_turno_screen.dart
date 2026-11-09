import 'package:flutter/material.dart';
import 'package:open_filex/open_filex.dart';
import 'package:path_provider/path_provider.dart';
import 'package:provider/provider.dart';

import '../data/resumen_turno.dart';
import 'offline_controller.dart';

/// B2 · «Resumen de mi turno» (Cajero y Encargado): cantidad de ventas, efectivo recibido y cambio, y el desglose por estado de sincronización.
/// Es solo lectura sobre los datos de este dispositivo, así que funciona sin conexión; se puede descargar en PDF.
class ResumenTurnoScreen extends StatelessWidget {
  const ResumenTurnoScreen({super.key});

  Future<void> _pdf(BuildContext context, ResumenTurno r) async {
    final c = context.read<OfflineController>();
    final mensajes = ScaffoldMessenger.of(context);
    final ruta = await r.aPdf(carpeta: (await getTemporaryDirectory()).path, empresa: c.sesion?.empresaNombre ?? 'FashionStore', usuario: c.sesion?.nombreCompleto ?? '');
    final abierto = await OpenFilex.open(ruta);
    if (abierto.type != ResultType.done) mensajes.showSnackBar(const SnackBar(content: Text('No hay una aplicación para abrir PDF en este teléfono.')));
  }

  @override
  Widget build(BuildContext context) {
    final r = ResumenTurno.desde(context.watch<OfflineController>().operaciones);
    final texto = Theme.of(context).textTheme;
    return Scaffold(
      appBar: AppBar(title: const Text('Resumen de mi turno')),
      body: ListView(padding: EdgeInsets.fromLTRB(16, 16, 16, MediaQuery.viewPaddingOf(context).bottom + 16), children: [
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('${r.ventas} venta(s) de contado', style: texto.titleLarge),
              const SizedBox(height: 8),
              Text('Total vendido: Bs ${r.totalVendido.toStringAsFixed(2)}'),
              Text('Efectivo recibido: Bs ${r.efectivoRecibido.toStringAsFixed(2)}'),
              Text('Cambio entregado: Bs ${r.cambio.toStringAsFixed(2)}'),
            ]),
          ),
        ),
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('Por estado de sincronización', style: texto.titleMedium),
              for (final e in ResumenTurno.nombresEstado.entries) Text('${e.value}: ${r.porEstado[e.key] ?? 0}'),
            ]),
          ),
        ),
        FilledButton.icon(onPressed: () => _pdf(context, r), icon: const Icon(Icons.picture_as_pdf_outlined), label: const Text('Descargar PDF')),
      ]),
    );
  }
}
