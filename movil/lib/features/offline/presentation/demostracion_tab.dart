import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../data/modelos.dart';
import 'modo_offline_screen.dart' show fechaCorta;
import 'offline_controller.dart';

/// Pantalla de demostración para la defensa: «Simular sin conexión», la cola en vivo y el registro de sincronización en una sola vista.
class DemostracionTab extends StatelessWidget {
  const DemostracionTab({super.key});

  Color _color(String e) => switch (e) {
        Estado.confirmada => Colors.green.shade100,
        Estado.rechazada => Colors.red.shade100,
        Estado.enConflicto || Estado.enviada => Colors.orange.shade100,
        _ => Colors.blueGrey.shade100,
      };

  @override
  Widget build(BuildContext context) {
    final c = context.watch<OfflineController>();
    int cuantas(Set<String> estados) => c.operaciones.where((o) => estados.contains(o.estado)).length;
    return ListView(padding: const EdgeInsets.all(16), children: [
      Card(
        child: SwitchListTile(
          secondary: const Icon(Icons.airplanemode_active),
          title: const Text('Simular sin conexión'),
          subtitle: Text(c.simulado ? 'Modo sin conexión simulado: apáguelo para sincronizar.' : 'Fuerza el modo sin conexión aunque haya Internet.'),
          value: c.simulado,
          onChanged: c.simularSinConexion,
        ),
      ),
      Wrap(spacing: 8, runSpacing: 4, children: [
        Chip(label: Text(c.sincronizando ? 'Sincronizando…' : c.enLinea ? 'En línea' : 'Sin conexión')),
        Chip(label: Text('Pendientes: ${cuantas({Estado.registradaLocal, Estado.enviada})}')),
        Chip(label: Text('Confirmadas: ${cuantas({Estado.confirmada})}')),
        Chip(label: Text('En conflicto: ${cuantas({Estado.enConflicto})}')),
        Chip(label: Text('Rechazadas: ${cuantas({Estado.rechazada})}')),
        ActionChip(avatar: const Icon(Icons.sync, size: 16), label: const Text('Sincronizar ahora'), onPressed: c.sincronizando || !c.enLinea || c.pendientes.isEmpty ? null : () => c.sincronizar()),
      ]),
      const SizedBox(height: 12),
      Text('Cola en vivo', style: Theme.of(context).textTheme.titleMedium),
      if (c.operaciones.isEmpty) const Padding(padding: EdgeInsets.symmetric(vertical: 8), child: Text('La cola está vacía.')),
      for (final o in c.operaciones.take(8))
        ListTile(dense: true, contentPadding: EdgeInsets.zero, title: Text(o.resumen, maxLines: 1, overflow: TextOverflow.ellipsis), subtitle: Text(fechaCorta(o.creadoEn)), trailing: Chip(label: Text(Estado.textos[o.estado] ?? o.estado, style: const TextStyle(fontSize: 11)), backgroundColor: _color(o.estado))),
      const SizedBox(height: 12),
      Text('Registro de sincronización', style: Theme.of(context).textTheme.titleMedium),
      // la clave cambia con cada sincronización y con cada cambio de la cola: el registro se vuelve a leer solo
      FutureBuilder<List<Map<String, Object?>>>(
        key: ValueKey('${c.refresco}-${c.operaciones.length}'),
        future: c.repo.registroSincronizacion(limite: 8),
        builder: (context, snap) {
          final filas = snap.data ?? const <Map<String, Object?>>[];
          if (filas.isEmpty) return const Padding(padding: EdgeInsets.symmetric(vertical: 8), child: Text('Todavía no se intentó sincronizar nada.'));
          return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            for (final f in filas) Padding(padding: const EdgeInsets.symmetric(vertical: 2), child: Text('${f['tipo']} · intento ${f['intento']} · ${f['resultado']} (${f['codigo']})', style: Theme.of(context).textTheme.bodySmall)),
          ]);
        },
      ),
    ]);
  }
}
