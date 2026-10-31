import 'package:flutter/material.dart';

import '../data/comprobante_movil.dart';

/// «Ver comprobante»: descarga el PDF y lo abre con el visor del teléfono. Muestra un indicador y no se puede tocar mientras descarga.
class BotonComprobante extends StatefulWidget {
  const BotonComprobante({super.key, required this.comprobante, required this.pedidoId, required this.numero});

  final ComprobanteMovil comprobante;
  final int pedidoId;
  final String numero;

  @override
  State<BotonComprobante> createState() => _BotonComprobanteState();
}

class _BotonComprobanteState extends State<BotonComprobante> {
  bool _descargando = false;

  Future<void> _ver() async {
    final mensajes = ScaffoldMessenger.of(context);
    setState(() => _descargando = true);
    final error = await widget.comprobante.ver(widget.pedidoId, widget.numero);
    if (!mounted) return;
    setState(() => _descargando = false);
    if (error != null) mensajes.showSnackBar(SnackBar(content: Text(error)));
  }

  @override
  Widget build(BuildContext context) => TextButton.icon(
        onPressed: _descargando ? null : _ver,
        icon: _descargando
            ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2))
            : const Icon(Icons.picture_as_pdf_outlined),
        label: Text(_descargando ? 'Descargando…' : 'Ver comprobante'),
      );
}
