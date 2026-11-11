import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../../core/network/api_client.dart';
import '../../auth/data/auth_repository.dart';
import 'modo_offline_screen.dart' show fechaCorta;

String _bs(Object? valor) => valor == null ? '' : 'Bs ${(double.tryParse('$valor') ?? 0).toStringAsFixed(2)}';

/// CU-40 · Conflictos de sincronización del Encargado: ventas, compras y reservas hechas sin conexión que no alcanzaron en el inventario (no se descontó nada, RN14).
/// Para cada caso muestra qué pasó, qué pidió el dispositivo y cuánto hay que devolver si era una venta ya cobrada; el Encargado reintenta o descarta.
/// Resolver un conflicto es una decisión del servidor, así que esta pantalla necesita conexión.
class ConflictosScreen extends StatefulWidget {
  const ConflictosScreen({super.key, this.api});

  /// Solo para pruebas; en la app se usa el cliente de la sesión.
  final ApiClient? api;

  @override
  State<ConflictosScreen> createState() => _ConflictosScreenState();
}

class _ConflictosScreenState extends State<ConflictosScreen> {
  List<Map<String, dynamic>>? _conflictos;
  String? _error;
  bool _trabajando = false;

  ApiClient get _api => widget.api ?? context.read<AuthRepository>().api;

  @override
  void initState() {
    super.initState();
    _cargar();
  }

  Future<void> _cargar() async {
    try {
      final lista = (await _api.getLista('/offline/conflictos')).cast<Map<String, dynamic>>();
      if (mounted) setState(() { _conflictos = lista; _error = null; });
    } on ApiException catch (e) {
      if (mounted) setState(() => _error = e.sinConexion ? 'Sin conexión: los conflictos se resuelven cuando hay Internet.' : e.mensaje);
    }
  }

  Future<void> _resolver(Map<String, dynamic> c, Map<String, dynamic> cuerpo) async {
    final mensajes = ScaffoldMessenger.of(context);
    setState(() => _trabajando = true);
    try {
      final r = await _api.post('/offline/conflictos/${c['id']}/resolver', cuerpo);
      mensajes.showSnackBar(SnackBar(content: Text(cuerpo['accion'] == 'REINTENTAR' ? 'Operación confirmada${r['referencia'] != null ? ' (${r['referencia']})' : ''}.' : '${r['mensaje']}')));
    } on ApiException catch (e) {
      mensajes.showSnackBar(SnackBar(content: Text(e.mensaje)));
    }
    if (mounted) setState(() => _trabajando = false);
    await _cargar();
  }

  Future<void> _descartar(Map<String, dynamic> c) async {
    final motivo = TextEditingController();
    final esVenta = c['tipo'] == 'VENTA_CONTADO';
    var devolver = false;
    final condicion = {'sin_danos': false, 'sin_desgaste': false, 'con_etiquetas': false};
    final confirmado = await showDialog<bool>(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setLocal) {
          final completa = condicion.values.every((v) => v);
          return AlertDialog(
            title: const Text('Descartar la operación'),
            content: SingleChildScrollView(
              child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
                TextField(controller: motivo, maxLength: 200, decoration: const InputDecoration(labelText: 'Motivo del descarte', hintText: 'Por ejemplo: el cliente ya se fue'), onChanged: (_) => setLocal(() {})),
                if (esVenta) ...[
                  CheckboxListTile(
                      contentPadding: EdgeInsets.zero,
                      value: devolver,
                      onChanged: (v) => setLocal(() => devolver = v ?? false),
                      title: Text(c['monto_a_devolver'] != null ? 'Devolver el efectivo al cliente (${_bs(c['monto_a_devolver'])})' : 'Devolver el efectivo al cliente')),
                  if (devolver) ...[
                    const Text('Revisión de la prenda que vuelve', style: TextStyle(fontWeight: FontWeight.w600)),
                    for (final e in {'sin_danos': 'Sin daños', 'sin_desgaste': 'Sin desgaste ni señales de uso', 'con_etiquetas': 'Conserva sus etiquetas'}.entries)
                      CheckboxListTile(contentPadding: EdgeInsets.zero, dense: true, value: condicion[e.key], onChanged: (v) => setLocal(() => condicion[e.key] = v ?? false), title: Text(e.value)),
                  ],
                ],
              ]),
            ),
            actions: [
              TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancelar')),
              FilledButton(
                  onPressed: motivo.text.trim().isEmpty || (devolver && !completa) ? null : () => Navigator.pop(ctx, true),
                  child: Text(devolver && c['monto_a_devolver'] != null ? 'Descartar y devolver ${_bs(c['monto_a_devolver'])}' : 'Confirmar descarte')),
            ],
          );
        },
      ),
    );
    if (confirmado == true) {
      await _resolver(c, {'accion': 'DESCARTAR', 'motivo': motivo.text.trim(), if (devolver) 'devolver_dinero': true, if (devolver) 'condicion': condicion});
    }
  }

  String _tipo(String? t) => switch (t) { 'VENTA_CONTADO' => 'Venta de contado', 'COMPRA' => 'Compra del cliente', _ => 'Reserva' };

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Conflictos de sincronización'), actions: [IconButton(tooltip: 'Actualizar', icon: const Icon(Icons.refresh), onPressed: _cargar)]),
      body: ListView(padding: EdgeInsets.fromLTRB(16, 16, 16, MediaQuery.viewPaddingOf(context).bottom + 16), children: [
        const Text('Ventas, compras y reservas hechas sin conexión que no alcanzaron en el inventario. No se descontó nada del stock.'),
        const SizedBox(height: 8),
        if (_error != null) Text(_error!, style: const TextStyle(color: Colors.red)),
        if (_conflictos == null && _error == null) const Center(child: CircularProgressIndicator()),
        if (_conflictos != null && _conflictos!.isEmpty) const Padding(padding: EdgeInsets.all(24), child: Center(child: Text('No hay operaciones en conflicto.'))),
        for (final c in _conflictos ?? const <Map<String, dynamic>>[])
          Card(
            child: Padding(
              padding: const EdgeInsets.all(12),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('${_tipo(c['tipo'] as String?)} · ${c['sucursal']}', style: const TextStyle(fontWeight: FontWeight.w700)),
                Text('Registrada por ${c['usuario']} el ${fechaCorta(c['creada_en'] as String?)} · ${c['intentos']} intento(s)', style: Theme.of(context).textTheme.bodySmall),
                const SizedBox(height: 6),
                Text('Qué pasó: ${c['mensaje']}'),
                const SizedBox(height: 4),
                const Text('Qué pidió ese dispositivo:', style: TextStyle(fontWeight: FontWeight.w600)),
                for (final f in ((c['detalle'] as Map?)?['faltantes'] as List? ?? const []).cast<Map<String, dynamic>>())
                  Text('• ${f['producto']} (${f['talla']}, ${f['color']}): pidió ${f['solicitadas']}, hay hoy ${f['disponibles']}, faltan ${(f['solicitadas'] as int) - (f['disponibles'] as int)}'),
                if (c['tipo'] == 'VENTA_CONTADO' && c['monto_a_devolver'] != null)
                  Container(
                    margin: const EdgeInsets.only(top: 8),
                    padding: const EdgeInsets.all(8),
                    color: const Color(0xFFFBEFD9),
                    child: Text('El cliente entregó ${_bs(c['efectivo_recibido'])} en caja. Si descarta esta venta debe devolverle ${_bs(c['monto_a_devolver'])}.'),
                  ),
                const SizedBox(height: 8),
                Wrap(spacing: 8, children: [
                  FilledButton(onPressed: _trabajando ? null : () => _resolver(c, {'accion': 'REINTENTAR'}), child: const Text('Reintentar')),
                  OutlinedButton(onPressed: _trabajando ? null : () => _descartar(c), child: const Text('Descartar…')),
                ]),
              ]),
            ),
          ),
      ]),
    );
  }
}
