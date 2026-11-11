import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../features/offline/presentation/offline_controller.dart';

/// Al deslizar para actualizar: con red la pantalla recarga; sin red se avisa que lo que se ve es la copia guardada en el teléfono.
Future<void> refrescarConAviso(BuildContext context, Future<void> Function() recargar) async {
  final enLinea = context.read<OfflineController>().enLinea;
  await recargar();
  if (!enLinea && context.mounted) {
    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(const SnackBar(content: Text('Sin conexión, mostrando copia local.')));
  }
}
