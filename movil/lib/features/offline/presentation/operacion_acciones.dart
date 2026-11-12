import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';

import '../data/linea_de_tiempo.dart';
import '../data/modelos.dart';
import 'modo_offline_screen.dart' show fechaCorta;
import 'offline_controller.dart';

/// Botones «Línea de tiempo» y «Deshacer» de una operación guardada en el dispositivo (D5). Funcionan sin conexión.
class AccionesOperacion extends StatelessWidget {
  const AccionesOperacion(this.operacion, {super.key, this.alDeshacer});
  final OperacionLocal operacion;
  final VoidCallback? alDeshacer;

  @override
  Widget build(BuildContext context) {
    final c = context.read<OfflineController>();
    return Wrap(spacing: 8, children: [
      TextButton.icon(onPressed: () => verLineaDeTiempo(context, operacion), icon: const Icon(Icons.timeline, size: 18), label: const Text('Línea de tiempo')),
      if (c.puedeDeshacer(operacion))
        TextButton.icon(
          style: TextButton.styleFrom(foregroundColor: Colors.red),
          onPressed: () => deshacerConConfirmacion(context, operacion, alDeshacer: alDeshacer),
          icon: const Icon(Icons.undo, size: 18),
          label: const Text('Deshacer'),
        ),
    ]);
  }
}

/// Muestra la historia de la operación: registrada → cada envío con su resultado → resuelta.
Future<void> verLineaDeTiempo(BuildContext context, OperacionLocal o) async {
  final registro = await context.read<OfflineController>().repo.registroSincronizacion(limite: 500);
  if (!context.mounted) return;
  final pasos = lineaDeTiempo(o, registro);
  Color color(String t) => switch (t) { 'ok' => Colors.green.shade800, 'warn' => Colors.orange.shade800, 'danger' => Colors.red.shade700, _ => Colors.blueGrey };
  await showDialog<void>(
    context: context,
    builder: (_) => AlertDialog(
      title: const Text('Línea de tiempo'),
      content: SingleChildScrollView(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(o.resumen, style: const TextStyle(fontWeight: FontWeight.w600)),
          const SizedBox(height: 8),
          for (final p in pasos)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 3),
              child: Text('${p.fecha != null ? '${fechaCorta(p.fecha)} · ' : ''}${p.texto}', style: TextStyle(color: color(p.tipo))),
            ),
        ]),
      ),
      actions: [TextButton(onPressed: () => Navigator.of(context, rootNavigator: true).pop(), child: const Text('Cerrar'))],
    ),
  );
}

/// Pregunta antes de deshacer y, si el usuario acepta, quita la operación y devuelve el inventario local a como estaba.
Future<void> deshacerConConfirmacion(BuildContext context, OperacionLocal operacion, {VoidCallback? alDeshacer}) async {
  final c = context.read<OfflineController>();
  final seguir = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
            title: const Text('¿Deshacer esta operación?'),
            content: Text('${operacion.resumen}\nSe quitará de este teléfono y el inventario local volverá a como estaba.'),
            actions: [
              TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Volver')),
              FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Sí, deshacer')),
            ],
          ));
  if (seguir == true) HapticFeedback.lightImpact();
  if (seguir == true && await c.deshacer(operacion)) alDeshacer?.call();
}
