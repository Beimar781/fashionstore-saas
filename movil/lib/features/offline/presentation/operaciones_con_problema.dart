import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../data/modelos.dart';
import 'offline_controller.dart';

const msgAgotada = 'La prenda se agotó mientras estaba sin conexión. No se le cobró nada.';

/// Motivo que lee el cliente: si el servidor informó una devolución de dinero se muestra tal cual; si no, el aviso de que no se cobró nada.
String motivoParaCliente(OperacionLocal o) {
  if (o.mensaje.toLowerCase().contains('devolv')) return o.mensaje;
  if (o.estado == Estado.enConflicto) return msgAgotada;
  return o.mensaje.isEmpty ? 'No se pudo realizar la operación.' : o.mensaje;
}

/// Estado de la devolución del efectivo de una venta de caja con problema (la registra el Encargado al descartarla, CU-40).
String devolucionDeEfectivo(OperacionLocal o) {
  if (o.estado == Estado.enConflicto) return 'Pendiente: el Encargado debe reintentarla o descartarla.';
  return o.mensaje.toLowerCase().contains('devolv') ? 'Efectivo devuelto al cliente.' : 'Sin devolución registrada.';
}

/// Operaciones sin conexión que terminaron EN_CONFLICTO o RECHAZADA, visibles para quien las sufre en su pantalla normal:
/// el Cliente en «Mis compras» y «Mis reservas» (con el botón para elegir otra talla o sucursal) y el Cajero en su inicio («Ventas con problema»).
class OperacionesConProblema extends StatelessWidget {
  const OperacionesConProblema({super.key, required this.tipos, required this.titulo, this.alElegirOtra});

  final List<String> tipos;
  final String titulo;

  /// Solo para el cliente: abre el catálogo para elegir otra talla o sucursal.
  final VoidCallback? alElegirOtra;

  @override
  Widget build(BuildContext context) {
    final operaciones = context
        .watch<OfflineController>()
        .operaciones
        .where((o) => tipos.contains(o.tipo) && (o.estado == Estado.enConflicto || o.estado == Estado.rechazada))
        .toList();
    if (operaciones.isEmpty) return const SizedBox.shrink();
    return Card(
      color: const Color(0xFFFBEFD9),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(titulo, style: const TextStyle(fontWeight: FontWeight.w700)),
          for (final o in operaciones) ...[
            const Divider(),
            Text('${o.resumen} · ${o.estado == Estado.enConflicto ? 'En conflicto' : 'Rechazada'}', style: const TextStyle(fontWeight: FontWeight.w600)),
            Text(alElegirOtra != null ? motivoParaCliente(o) : o.mensaje),
            if (alElegirOtra == null) Text('Devolución del efectivo: ${devolucionDeEfectivo(o)}'),
            for (final f in o.faltantes) Text('• ${f['producto']} (${f['talla']}, ${f['color']}): pidió ${f['solicitadas']}, hay ${f['disponibles']}'),
            if (alElegirOtra != null) Align(alignment: Alignment.centerRight, child: TextButton(onPressed: alElegirOtra, child: const Text('Elegir otra talla o sucursal'))),
          ],
        ]),
      ),
    );
  }
}
