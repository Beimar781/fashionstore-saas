import 'package:flutter/material.dart';
import '../../../core/ui/refrescar.dart';
import 'lista_vacia.dart';
import 'package:provider/provider.dart';

import '../../../core/network/api_client.dart';
import '../../auth/data/auth_repository.dart';
import 'offline_controller.dart';
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
  bool _desdeCopia = false; // sin conexión: se ve la última lista guardada, pero resolver necesita Internet
  String? _fechaCopia;
  int? _refrescoVisto;
  final Map<String, int> _stockHoy = {}; // «producto|talla|color» → unidades que hay hoy según la copia local del Encargado

  ApiClient get _api => widget.api ?? context.read<AuthRepository>().api;

  @override
  void initState() {
    super.initState();
    _cargar();
  }

  Future<void> _cargar() async {
    try {
      ApiClient.lecturaLocalDesde = null;
      final lista = (await _api.getLista('/offline/conflictos')).cast<Map<String, dynamic>>();
      await _leerStockHoy(lista);
      if (mounted) setState(() { _conflictos = lista; _error = null; _fechaCopia = ApiClient.lecturaLocalDesde; _desdeCopia = _fechaCopia != null; });
    } on ApiException catch (e) {
      if (mounted) setState(() => _error = e.sinConexion ? 'Sin conexión: los conflictos se resuelven cuando hay Internet. Todavía no se guardó ninguna lista.' : e.mensaje);
    }
  }

  /// Busca en la copia local cuánto hay hoy de cada prenda en falta; si la prenda no está en la copia, se usa lo que informó el servidor.
  Future<void> _leerStockHoy(List<Map<String, dynamic>> lista) async {
    if (!mounted) return;
    OfflineController? c;
    try {
      c = context.read<OfflineController>();
    } catch (_) {
      return; // en las pruebas puede no haber controlador
    }
    final sucursal = c.sesion?.sucursalId;
    for (final conflicto in lista) {
      for (final f in ((conflicto['detalle'] as Map?)?['faltantes'] as List? ?? const []).cast<Map<String, dynamic>>()) {
        final prendas = await c.repo.buscar('${f['producto']}', limite: 50);
        final p = prendas.where((x) => x.variante.talla == f['talla'] && x.variante.color == f['color']).firstOrNull;
        if (p != null) _stockHoy['${f['producto']}|${f['talla']}|${f['color']}'] = p.variante.stockEn(sucursal);
      }
    }
  }

  int _hoyHay(Map<String, dynamic> f) => _stockHoy['${f['producto']}|${f['talla']}|${f['color']}'] ?? (f['disponibles'] as int);

  /// «Reintentar» solo tiene sentido si ahora alcanza para todo lo que se pidió.
  bool _sinStock(Map<String, dynamic> c) =>
      ((c['detalle'] as Map?)?['faltantes'] as List? ?? const []).cast<Map<String, dynamic>>().any((f) => _hoyHay(f) < (f['solicitadas'] as int));

  Future<void> _resolver(Map<String, dynamic> c, Map<String, dynamic> cuerpo) async {
    final mensajes = ScaffoldMessenger.of(context);
    setState(() => _trabajando = true);
    try {
      final r = await _api.post('/offline/conflictos/${c['id']}/resolver', cuerpo);
      mensajes.showSnackBar(SnackBar(content: Text(cuerpo['accion'] == 'REINTENTAR' ? 'Operación confirmada${r['referencia'] != null ? ' (${r['referencia']})' : ''}.' : '${r['mensaje']}')));
    } on ApiException catch (e) {
      mensajes.showSnackBar(SnackBar(content: Text(e.sinConexion ? 'Esta función necesita Internet.' : e.mensaje)));
    }
    if (mounted) setState(() => _trabajando = false);
    await _cargar();
    if (mounted) {
      try {
        await context.read<OfflineController>().refrescarConflictos();
      } catch (_) {}
    }
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
    // al volver la red la lista se recarga sola (en las pruebas puede no haber controlador)
    int? refresco;
    try {
      refresco = context.select<OfflineController, int>((c) => c.refresco);
    } catch (_) {
      refresco = null;
    }
    if (_refrescoVisto != null && refresco != null && _refrescoVisto != refresco) {
      WidgetsBinding.instance.addPostFrameCallback((_) { if (mounted) _cargar(); });
    }
    _refrescoVisto = refresco;
    return Scaffold(
      appBar: AppBar(title: const Text('Conflictos de sincronización'), actions: [IconButton(tooltip: 'Actualizar', icon: const Icon(Icons.refresh), onPressed: _cargar)]),
      body: RefreshIndicator(onRefresh: () => refrescarConAviso(context, _cargar), child: ListView(physics: const AlwaysScrollableScrollPhysics(), padding: EdgeInsets.fromLTRB(16, 16, 16, MediaQuery.viewPaddingOf(context).bottom + 16), children: [
        const Text('Ventas, compras y reservas hechas sin conexión que no alcanzaron en el inventario. No se descontó nada del stock.'),
        const SizedBox(height: 8),
        if (_error != null) Text(_error!, style: const TextStyle(color: Colors.red)),
        if (_desdeCopia)
          Padding(padding: const EdgeInsets.only(bottom: 8), child: Text('Sin conexión · datos al ${fechaCorta(_fechaCopia)}. Reintentar y descartar necesitan Internet.', style: const TextStyle(fontSize: 12, color: Color(0xFF8A5A00)))),
        if (_conflictos == null && _error == null) const Center(child: CircularProgressIndicator()),
        if (_conflictos != null && _conflictos!.isEmpty) const ListaVacia(icono: Icons.check_circle_outline, texto: 'No hay operaciones en conflicto.'),
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
                  Text('• ${f['producto']} (${f['talla']}, ${f['color']}): pidió ${f['solicitadas']}, hoy hay ${_hoyHay(f)}${_hoyHay(f) < (f['solicitadas'] as int) ? ', faltan ${(f['solicitadas'] as int) - _hoyHay(f)}' : ''}'),
                if (c['tipo'] == 'VENTA_CONTADO' && c['monto_a_devolver'] != null)
                  Container(
                    margin: const EdgeInsets.only(top: 8),
                    padding: const EdgeInsets.all(8),
                    color: const Color(0xFFFBEFD9),
                    child: Text('El cliente entregó ${_bs(c['efectivo_recibido'])} en caja. Si descarta esta venta debe devolverle ${_bs(c['monto_a_devolver'])}.'),
                  ),
                const SizedBox(height: 8),
                Wrap(spacing: 8, children: [
                  FilledButton(onPressed: _trabajando || _desdeCopia || _sinStock(c) ? null : () => _resolver(c, {'accion': 'REINTENTAR'}), child: const Text('Reintentar')),
                  if (_sinStock(c)) const Padding(padding: EdgeInsets.symmetric(vertical: 12), child: Text('Sin stock todavía', style: TextStyle(color: Color(0xFF9A5B00), fontWeight: FontWeight.w600))),
                  OutlinedButton(onPressed: _trabajando || _desdeCopia ? null : () => _descartar(c), child: const Text('Descartar…')),
                ]),
              ]),
            ),
          ),
      ])),
    );
  }
}
