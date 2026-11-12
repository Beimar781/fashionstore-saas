import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';

import 'offline_controller.dart';

/// «Última sincronización: hh:mm» y estado de la red, con un botón de refrescar que gira mientras trabaja y no bloquea la pantalla.
class EstadoSyncTile extends StatelessWidget {
  const EstadoSyncTile({super.key});

  static String hora(String? iso) {
    final f = DateTime.tryParse(iso ?? '')?.toLocal();
    if (f == null) return 'todavía no';
    String d(int n) => n.toString().padLeft(2, '0');
    return '${d(f.hour)}:${d(f.minute)}';
  }

  @override
  Widget build(BuildContext context) {
    final c = context.watch<OfflineController>();
    if (!c.habilitado) return const SizedBox.shrink();
    final trabajando = c.sincronizando || c.descargando;
    final copia = DateTime.tryParse(c.catalogoGeneradoEn ?? '');
    final vieja = copia != null && DateTime.now().difference(copia).inHours >= 24;
    return Column(children: [
      if (vieja) // aviso suave, no bloquea nada
        Card(
          color: const Color(0xFFFBEFD9),
          child: ListTile(
            leading: const Icon(Icons.history, color: Color(0xFF9A5B00)),
            title: const Text('Actualice el catálogo'),
            subtitle: const Text('La copia guardada tiene más de 24 horas.'),
            trailing: TextButton(onPressed: c.enLinea && !trabajando ? c.descargarCatalogo : null, child: const Text('Actualizar')),
          ),
        ),
      Card(
      child: ListTile(
        leading: Icon(c.enLinea ? Icons.cloud_done_outlined : Icons.cloud_off, color: c.enLinea ? Colors.green : Colors.orange),
        title: Text('Última sincronización: ${hora(c.ultimaSync)}'),
        subtitle: Text(c.enLinea ? 'En línea' : 'Sin conexión: se usa la copia guardada'),
        trailing: trabajando
            ? const SizedBox(width: 48, height: 48, child: Padding(padding: EdgeInsets.all(12), child: CircularProgressIndicator(strokeWidth: 2)))
            : IconButton(
                tooltip: 'Actualizar ahora',
                constraints: const BoxConstraints(minWidth: 48, minHeight: 48),
                icon: const Icon(Icons.refresh),
                onPressed: c.enLinea
                    ? () async {
                        HapticFeedback.lightImpact();
                        await c.sincronizar();
                        await c.descargarCatalogo();
                      }
                    : null),
      ),
    )]);
  }
}

/// Copia al portapapeles el diagnóstico para soporte: usuario, rol, empresa, hora de la copia, versión de la app, pendientes y conflictos.
class CopiarDiagnosticoTile extends StatelessWidget {
  const CopiarDiagnosticoTile({super.key});

  @override
  Widget build(BuildContext context) => Card(
        child: ListTile(
          leading: const Icon(Icons.copy_all_outlined),
          title: const Text('Copiar diagnóstico'),
          subtitle: const Text('Para enviarlo a soporte (sin contraseñas ni datos de tarjeta)'),
          onTap: () async {
            final mensajes = ScaffoldMessenger.of(context);
            final texto = await context.read<OfflineController>().diagnosticoCompleto();
            await Clipboard.setData(ClipboardData(text: texto));
            mensajes.showSnackBar(const SnackBar(content: Text('Diagnóstico copiado.')));
          },
        ),
      );
}
