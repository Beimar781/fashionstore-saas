import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'modo_offline_screen.dart';
import 'offline_controller.dart';

/// Indicador permanente de la barra superior: en línea, sin conexión o sincronizando, con el número de operaciones pendientes. Al tocarlo abre el detalle de la cola.
/// Solo aparece para quien trabaja sin conexión (Cliente, Cajero y Encargado con plan que lo incluye).
class EstadoConexionChip extends StatelessWidget {
  const EstadoConexionChip({super.key});

  @override
  Widget build(BuildContext context) {
    final c = context.watch<OfflineController>();
    if (!c.habilitado) return const SizedBox.shrink();
    final pendientes = c.pendientes.length;
    final (texto, color) = c.sincronizando
        ? ('Sincronizando…', Colors.blue)
        : c.enLinea
            ? ('En línea', Colors.green)
            : ('Sin conexión', Colors.orange);
    return Tooltip(
      message: '$texto${pendientes > 0 ? ' · $pendientes operación(es) por sincronizar' : ''}. Toque para ver el detalle.',
      child: ActionChip(
        visualDensity: VisualDensity.compact,
        avatar: Icon(Icons.circle, size: 12, color: color),
        label: Text(pendientes > 0 ? '$texto · $pendientes' : texto, style: const TextStyle(fontSize: 12)),
        onPressed: () => Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => const ModoOfflineScreen(pestana: 2))),
      ),
    );
  }
}
