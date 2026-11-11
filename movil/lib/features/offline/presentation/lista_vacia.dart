import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'modo_offline_screen.dart' show fechaCorta;
import 'offline_controller.dart';

/// Estado vacío de una lista: icono, qué pasa y qué hacer. Con `conCopia` muestra de cuándo es la copia local y, con red, el botón «Actualizar ahora».
class ListaVacia extends StatelessWidget {
  const ListaVacia({super.key, required this.texto, this.icono = Icons.inbox_outlined, this.conCopia = false});

  final String texto;
  final IconData icono;
  final bool conCopia;

  @override
  Widget build(BuildContext context) {
    final c = conCopia ? context.watch<OfflineController>() : null;
    return Padding(
      padding: const EdgeInsets.all(24),
      child: Column(children: [
        Icon(icono, size: 48, color: Colors.black38),
        const SizedBox(height: 8),
        Text(texto, textAlign: TextAlign.center),
        if (c != null && c.hayCatalogo) ...[
          const SizedBox(height: 4),
          Text('Copia local de ${fechaCorta(c.catalogoGeneradoEn)}', style: Theme.of(context).textTheme.bodySmall),
        ],
        if (c != null && c.enLinea) ...[
          const SizedBox(height: 8),
          OutlinedButton.icon(
              onPressed: c.descargando ? null : c.descargarCatalogo,
              icon: const Icon(Icons.refresh),
              label: Text(c.descargando ? 'Actualizando…' : 'Actualizar ahora')),
        ],
      ]),
    );
  }
}
