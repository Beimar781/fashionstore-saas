import 'package:flutter/material.dart';
import 'package:open_filex/open_filex.dart';
import 'package:path_provider/path_provider.dart';
import 'package:provider/provider.dart';

import '../data/comprobante_provisional.dart';
import '../data/modelos.dart';
import 'offline_controller.dart';

/// B1 · El PDF «Comprobante provisional» LOC-… se arma en el teléfono, sin conexión, y se abre con el visor del dispositivo.
/// Lo usan la pantalla de Caja (al terminar la venta y en «Mi turno») y la lista de operaciones del diagnóstico.
Future<void> verComprobanteProvisional(BuildContext context, OperacionLocal o) async {
  final c = context.read<OfflineController>();
  final mensajes = ScaffoldMessenger.of(context);
  final ruta = await ComprobanteProvisional.aPdf(
    o,
    carpeta: (await getTemporaryDirectory()).path,
    empresa: c.sesion?.empresaNombre ?? 'FashionStore',
    nombreDe: (id) => c.nombreDeVariante(id),
  );
  final abierto = await OpenFilex.open(ruta);
  if (abierto.type != ResultType.done) mensajes.showSnackBar(const SnackBar(content: Text('No hay una aplicación para abrir PDF en este teléfono.')));
}
