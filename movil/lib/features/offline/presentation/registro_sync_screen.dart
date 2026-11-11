import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';

import 'lista_vacia.dart';
import 'offline_controller.dart';

/// RNF10 · Registro de sincronización: cada intento de enviar una operación, con su resultado, código y motivo técnico (sin datos personales).
/// «Copiar diagnóstico» deja el texto en el portapapeles para pegarlo en un mensaje a soporte.
class RegistroSyncScreen extends StatefulWidget {
  const RegistroSyncScreen({super.key});

  @override
  State<RegistroSyncScreen> createState() => _RegistroSyncScreenState();
}

class _RegistroSyncScreenState extends State<RegistroSyncScreen> {
  List<Map<String, Object?>>? _filas;

  @override
  void initState() {
    super.initState();
    _cargar();
  }

  Future<void> _cargar() async {
    final filas = await context.read<OfflineController>().repo.registroSincronizacion();
    if (mounted) setState(() => _filas = filas);
  }

  Future<void> _copiar() async {
    final texto = await context.read<OfflineController>().diagnosticoCompleto();
    await Clipboard.setData(ClipboardData(text: texto));
    if (mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Diagnóstico copiado.')));
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: const Text('Registro de sincronización'), actions: [
          IconButton(tooltip: 'Copiar diagnóstico', icon: const Icon(Icons.copy_all_outlined), onPressed: _copiar),
        ]),
        body: RefreshIndicator(
          onRefresh: _cargar,
          child: ListView(padding: EdgeInsets.fromLTRB(12, 12, 12, MediaQuery.viewPaddingOf(context).bottom + 16), children: [
            if (_filas == null) const Center(child: CircularProgressIndicator()),
            if (_filas != null && _filas!.isEmpty) const ListaVacia(icono: Icons.sync_disabled_outlined, texto: 'Todavía no se intentó sincronizar nada.'),
            for (final f in _filas ?? const <Map<String, Object?>>[])
              Card(
                child: ListTile(
                  leading: Icon(f['resultado'] == 'SIN_RESPUESTA' ? Icons.cloud_off : Icons.sync_alt),
                  title: Text('${f['tipo']} · intento ${f['intento']} · ${f['resultado']} (${f['codigo']})'),
                  subtitle: Text('${f['fecha']}\n${f['operacion_id']}${(f['motivo'] as String).isEmpty ? '' : '\n${f['motivo']}'}'),
                  isThreeLine: true,
                ),
              ),
            FilledButton.icon(onPressed: _copiar, icon: const Icon(Icons.copy_all_outlined), label: const Text('Copiar diagnóstico')),
          ]),
        ),
      );
}
