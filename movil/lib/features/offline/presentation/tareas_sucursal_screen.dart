import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../data/modelos.dart';
import 'escaner_screen.dart';
import 'modo_offline_screen.dart' show fechaCorta;
import 'offline_controller.dart';

const msgPlazoVencido = 'El plazo de devolución de esta venta venció.';

/// B3 a B6 · Tareas de la sucursal sin conexión. El Cajero devuelve prendas; el Encargado, además, recibe mercadería, ajusta el inventario y atiende reservas.
/// Cada tarea queda en la cola con su UUID y se envía sola al recuperar la red; el servidor vuelve a validar todo al sincronizar.
class TareasSucursalScreen extends StatelessWidget {
  const TareasSucursalScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final encargado = context.read<OfflineController>().sesion?.rol == 'Encargado';
    final pestanas = [
      const Tab(text: 'Devolución'),
      if (encargado) ...const [Tab(text: 'Recepción'), Tab(text: 'Ajuste'), Tab(text: 'Reservas')],
    ];
    return DefaultTabController(
      length: pestanas.length,
      child: Scaffold(
        appBar: AppBar(title: const Text('Tareas de la sucursal'), bottom: TabBar(isScrollable: true, tabs: pestanas)),
        body: TabBarView(children: [
          const DevolucionTab(),
          if (encargado) ...const [RecepcionTab(), AjusteTab(), ReservasTab()],
        ]),
      ),
    );
  }
}

/// Pantalla normal de Devoluciones (CU-41) para el Cajero y el Encargado: funciona igual con y sin conexión, con las mismas validaciones (plazo y lo ya devuelto).
class DevolucionesScreen extends StatelessWidget {
  const DevolucionesScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final enLinea = context.select<OfflineController, bool>((c) => c.enLinea);
    return Scaffold(
      appBar: AppBar(title: const Text('Devoluciones')),
      body: Column(children: [
        if (!enLinea)
          Container(
              width: double.infinity,
              color: const Color(0xFFFBEFD9),
              padding: const EdgeInsets.all(10),
              child: const Text('Sin conexión: la devolución se guarda en este dispositivo y se envía sola al volver la red.')),
        const Expanded(child: DevolucionTab()),
      ]),
    );
  }
}

/// Distingue «no hay copia descargada» de «hay copia y no hay ventas/reservas en el plazo» (y del filtro que no encuentra nada).
String textoSinFilas(OfflineController c, String que, bool conFiltro) {
  if (!c.hayCatalogo) return 'Todavía no se descargó el catálogo con las $que de esta sucursal: se descarga solo cuando hay conexión.';
  if (conFiltro) return 'No hay $que descargadas con ese texto.';
  return 'No hay $que de esta sucursal dentro del plazo hasta la última descarga (${fechaCorta(c.catalogoGeneradoEn)}).';
}

void _avisar(BuildContext c, String texto) => ScaffoldMessenger.of(c).showSnackBar(SnackBar(content: Text(texto)));

// ---------------- B3: devolución sin conexión ----------------
class DevolucionTab extends StatefulWidget {
  const DevolucionTab({super.key});

  @override
  State<DevolucionTab> createState() => _DevolucionTabState();
}

class _DevolucionTabState extends State<DevolucionTab> {
  final _buscar = TextEditingController();
  final _motivo = TextEditingController();
  int? _refrescoVisto;
  List<Map<String, dynamic>> _ventas = [];
  Map<String, dynamic>? _venta;
  final Map<int, int> _cantidades = {};
  bool _sinDanos = true, _sinDesgaste = true, _conEtiquetas = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _cargar();
  }

  Future<void> _cargar() async {
    final v = await context.read<OfflineController>().repo.ventasRecientes();
    if (mounted) setState(() => _ventas = v);
  }

  /// B3: se valida el plazo guardado en la descarga; el servidor lo vuelve a validar al sincronizar.
  Future<void> _registrar() async {
    final venta = _venta!;
    final elegidas = {for (final e in _cantidades.entries.where((e) => e.value > 0)) e.key: e.value};
    final vence = DateTime.tryParse('${venta['vence_el']}');
    if (vence != null && DateTime.now().isAfter(vence)) return setState(() => _error = msgPlazoVencido);
    if (elegidas.isEmpty) return setState(() => _error = 'Elija al menos una prenda y su cantidad.');
    final c = context.read<OfflineController>();
    final mensajes = ScaffoldMessenger.of(context);
    await c.registrarTarea(
      tipo: 'DEVOLUCION',
      payload: {
        'comprobante': venta['comprobante'],
        'motivo': _motivo.text.trim(),
        'items': [for (final e in elegidas.entries) {'pedido_item_id': e.key, 'cantidad': e.value}],
        'condicion': {'sin_danos': _sinDanos, 'sin_desgaste': _sinDesgaste, 'con_etiquetas': _conEtiquetas},
      },
      resumen: 'Devolución de ${venta['comprobante']}',
    );
    await c.repo.descontarDevolvible('${venta['comprobante']}', elegidas);
    mensajes.showSnackBar(const SnackBar(content: Text('Devolución guardada. Se enviará sola al recuperar la conexión.')));
    _motivo.clear();
    _cantidades.clear();
    _venta = null;
    await _cargar();
    if (mounted) setState(() => _error = null);
  }

  @override
  Widget build(BuildContext context) {
    final refresco = context.select<OfflineController, int>((c) => c.refresco);
    if (_refrescoVisto != null && _refrescoVisto != refresco) {
      WidgetsBinding.instance.addPostFrameCallback((_) { if (mounted) _cargar(); }); // al volver la red lo descargado se renueva y la lista se actualiza sola
    }
    _refrescoVisto = refresco;
    final q = _buscar.text.trim().toLowerCase();
    final visibles = _ventas.where((v) => q.isEmpty || '${v['comprobante']}'.toLowerCase().contains(q)).toList();
    final margen = MediaQuery.viewPaddingOf(context).bottom + 16;
    if (_venta != null) {
      final items = (_venta!['items'] as List).cast<Map<String, dynamic>>();
      return ListView(padding: EdgeInsets.fromLTRB(16, 16, 16, margen), children: [
        Text('Venta ${_venta!['comprobante']}', style: Theme.of(context).textTheme.titleMedium),
        Text('Plazo hasta ${fechaCorta('${_venta!['vence_el']}')}', style: Theme.of(context).textTheme.bodySmall),
        for (final i in items)
          ListTile(
            dense: true,
            title: Text('${i['producto']} (${i['talla']}, ${i['color']})'),
            subtitle: Text('Vendidas ${i['vendida']} · se pueden devolver ${i['devolvible']}'),
            trailing: Row(mainAxisSize: MainAxisSize.min, children: [
              IconButton(icon: const Icon(Icons.remove_circle_outline), onPressed: (_cantidades[i['pedido_item_id']] ?? 0) > 0 ? () => setState(() => _cantidades[i['pedido_item_id'] as int] = _cantidades[i['pedido_item_id']]! - 1) : null),
              Text('${_cantidades[i['pedido_item_id']] ?? 0}'),
              IconButton(icon: const Icon(Icons.add_circle_outline), onPressed: (_cantidades[i['pedido_item_id']] ?? 0) < (i['devolvible'] as int) ? () => setState(() => _cantidades[i['pedido_item_id'] as int] = (_cantidades[i['pedido_item_id']] ?? 0) + 1) : null),
            ]),
          ),
        TextField(controller: _motivo, maxLength: 200, decoration: const InputDecoration(labelText: 'Motivo de la devolución')),
        CheckboxListTile(dense: true, value: _sinDanos, onChanged: (v) => setState(() => _sinDanos = v ?? false), title: const Text('Sin daños')),
        CheckboxListTile(dense: true, value: _sinDesgaste, onChanged: (v) => setState(() => _sinDesgaste = v ?? false), title: const Text('Sin desgaste')),
        CheckboxListTile(dense: true, value: _conEtiquetas, onChanged: (v) => setState(() => _conEtiquetas = v ?? false), title: const Text('Con sus etiquetas')),
        if (_error != null) Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
        const SizedBox(height: 8),
        Row(children: [
          OutlinedButton(onPressed: () => setState(() { _venta = null; _error = null; }), child: const Text('Volver')),
          const SizedBox(width: 12),
          Expanded(child: FilledButton(onPressed: _registrar, child: const Text('Registrar devolución'))),
        ]),
      ]);
    }
    return ListView(padding: EdgeInsets.fromLTRB(16, 16, 16, margen), children: [
      Text('Solo ventas pagadas en esta sucursal (de caja o compras digitales) dentro del plazo de devolución, hasta la última descarga (${fechaCorta(context.read<OfflineController>().catalogoGeneradoEn)}). Las ventas posteriores aparecen al volver la conexión.'),
      TextField(controller: _buscar, onChanged: (_) => setState(() {}), decoration: const InputDecoration(labelText: 'Buscar por número de comprobante', prefixIcon: Icon(Icons.search))),
      if (visibles.isEmpty) Padding(padding: const EdgeInsets.all(24), child: Text(textoSinFilas(context.read<OfflineController>(), 'ventas', _buscar.text.trim().isNotEmpty))),
      for (final v in visibles)
        Card(child: ListTile(title: Text('${v['comprobante']} · Bs ${v['total']}'), subtitle: Text('${(v['items'] as List).length} línea(s) · ${fechaCorta('${v['pagado_en']}')}'), trailing: const Icon(Icons.chevron_right), onTap: () => setState(() => _venta = v))),
    ]);
  }
}

// ---------------- B5 y B6: buscar una prenda del catálogo local ----------------
class _BuscadorPrenda extends StatefulWidget {
  const _BuscadorPrenda({required this.alElegir});
  final void Function(PrendaLocal) alElegir;

  @override
  State<_BuscadorPrenda> createState() => _BuscadorPrendaState();
}

class _BuscadorPrendaState extends State<_BuscadorPrenda> {
  final _texto = TextEditingController();
  List<PrendaLocal> _resultados = [];

  Future<void> _buscar() async {
    final r = await context.read<OfflineController>().repo.buscar(_texto.text, limite: 20);
    if (mounted) setState(() => _resultados = r);
  }

  @override
  Widget build(BuildContext context) => Column(children: [
        TextField(
          controller: _texto,
          onChanged: (_) => _buscar(),
          decoration: InputDecoration(
            labelText: 'Buscar por nombre, SKU o código de barras',
            prefixIcon: const Icon(Icons.search),
            suffixIcon: IconButton(
              tooltip: 'Escanear código',
              icon: const Icon(Icons.qr_code_scanner),
              onPressed: () async {
                final codigo = await escanearCodigo(context);
                if (codigo == null) return;
                _texto.text = codigo;
                await _buscar();
              },
            ),
          ),
        ),
        for (final r in _resultados)
          ListTile(dense: true, title: Text(r.producto.nombre), subtitle: Text('${r.variante.talla} · ${r.variante.color} · ${r.variante.sku}'), onTap: () => widget.alElegir(r)),
      ]);
}

// ---------------- B5: recepción de mercadería ----------------
class RecepcionTab extends StatefulWidget {
  const RecepcionTab({super.key});

  @override
  State<RecepcionTab> createState() => _RecepcionTabState();
}

class _RecepcionTabState extends State<RecepcionTab> {
  PrendaLocal? _prenda;
  final _cantidad = TextEditingController(text: '1');
  final _referencia = TextEditingController();
  String? _error;

  Future<void> _registrar() async {
    final cantidad = int.tryParse(_cantidad.text);
    if (_prenda == null || cantidad == null || cantidad < 1) return setState(() => _error = 'Elija la prenda e indique una cantidad de 1 o más.');
    if (_referencia.text.trim().isEmpty) return setState(() => _error = 'Indique la referencia del envío o del proveedor.');
    final c = context.read<OfflineController>();
    final mensajes = ScaffoldMessenger.of(context);
    await c.registrarTarea(
      tipo: 'RECEPCION',
      payload: {'variante_id': _prenda!.variante.id, 'cantidad': cantidad, 'referencia': _referencia.text.trim()},
      resumen: 'Recepción de $cantidad× ${_prenda!.producto.nombre} (${_prenda!.variante.talla}, ${_prenda!.variante.color})',
    );
    await c.repo.moverStockLocal(_prenda!.variante.id, c.sesion!.sucursalId!, cantidad); // sube de forma provisional, marcado como pendiente
    mensajes.showSnackBar(const SnackBar(content: Text('Recepción guardada. El inventario sube de forma provisional hasta sincronizar.')));
    setState(() { _prenda = null; _error = null; _referencia.clear(); _cantidad.text = '1'; });
  }

  @override
  Widget build(BuildContext context) => ListView(padding: EdgeInsets.fromLTRB(16, 16, 16, MediaQuery.viewPaddingOf(context).bottom + 16), children: [
        if (_prenda == null) _BuscadorPrenda(alElegir: (p) => setState(() => _prenda = p)) else ListTile(title: Text(_prenda!.producto.nombre), subtitle: Text('${_prenda!.variante.talla} · ${_prenda!.variante.color}'), trailing: TextButton(onPressed: () => setState(() => _prenda = null), child: const Text('Cambiar'))),
        TextField(controller: _cantidad, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'Cantidad recibida')),
        TextField(controller: _referencia, maxLength: 100, decoration: const InputDecoration(labelText: 'Referencia del envío o proveedor')),
        if (_error != null) Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
        const SizedBox(height: 8),
        FilledButton(onPressed: _registrar, child: const Text('Registrar recepción')),
      ]);
}

// ---------------- B6: conteo físico y ajuste de inventario ----------------
class AjusteTab extends StatefulWidget {
  const AjusteTab({super.key});

  @override
  State<AjusteTab> createState() => _AjusteTabState();
}

class _AjusteTabState extends State<AjusteTab> {
  PrendaLocal? _prenda;
  final _diferencia = TextEditingController();
  final _nota = TextEditingController();
  String _motivo = 'CONTEO';
  String? _error;

  /// Se envía la DIFERENCIA y no el valor absoluto, para no pisar las ventas hechas mientras tanto.
  Future<void> _registrar() async {
    final diferencia = int.tryParse(_diferencia.text.replaceFirst('+', ''));
    if (_prenda == null || diferencia == null || diferencia == 0) return setState(() => _error = 'Elija la prenda e indique la diferencia (positiva o negativa, distinta de cero).');
    final c = context.read<OfflineController>();
    final mensajes = ScaffoldMessenger.of(context);
    await c.registrarTarea(
      tipo: 'AJUSTE_INVENTARIO',
      payload: {'variante_id': _prenda!.variante.id, 'diferencia': diferencia, 'motivo': _motivo, 'nota': _nota.text.trim()},
      resumen: 'Ajuste de ${diferencia > 0 ? '+' : ''}$diferencia× ${_prenda!.producto.nombre} ($_motivo)',
    );
    await c.repo.moverStockLocal(_prenda!.variante.id, c.sesion!.sucursalId!, diferencia);
    mensajes.showSnackBar(const SnackBar(content: Text('Ajuste guardado. Se enviará como diferencia al recuperar la conexión.')));
    setState(() { _prenda = null; _error = null; _diferencia.clear(); _nota.clear(); });
  }

  @override
  Widget build(BuildContext context) => ListView(padding: EdgeInsets.fromLTRB(16, 16, 16, MediaQuery.viewPaddingOf(context).bottom + 16), children: [
        if (_prenda == null) _BuscadorPrenda(alElegir: (p) => setState(() => _prenda = p)) else ListTile(title: Text(_prenda!.producto.nombre), subtitle: Text('${_prenda!.variante.talla} · ${_prenda!.variante.color} · stock local ${_prenda!.variante.stockEn(context.read<OfflineController>().sesion?.sucursalId)}'), trailing: TextButton(onPressed: () => setState(() => _prenda = null), child: const Text('Cambiar'))),
        TextField(controller: _diferencia, keyboardType: const TextInputType.numberWithOptions(signed: true), decoration: const InputDecoration(labelText: 'Diferencia (por ejemplo +3 o -2)')),
        DropdownButtonFormField<String>(
          initialValue: _motivo,
          decoration: const InputDecoration(labelText: 'Motivo (obligatorio)'),
          items: const [DropdownMenuItem(value: 'CONTEO', child: Text('Conteo físico')), DropdownMenuItem(value: 'MERMA', child: Text('Merma')), DropdownMenuItem(value: 'DAÑO', child: Text('Daño'))],
          onChanged: (v) => setState(() => _motivo = v ?? 'CONTEO'),
        ),
        TextField(controller: _nota, maxLength: 150, decoration: const InputDecoration(labelText: 'Nota (opcional)')),
        if (_error != null) Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
        const SizedBox(height: 8),
        FilledButton(onPressed: _registrar, child: const Text('Registrar ajuste')),
      ]);
}

// ---------------- B4: atención de reservas ----------------
class ReservasTab extends StatefulWidget {
  const ReservasTab({super.key});

  @override
  State<ReservasTab> createState() => _ReservasTabState();
}

class _ReservasTabState extends State<ReservasTab> {
  List<Map<String, dynamic>> _reservas = [];
  final _codigo = TextEditingController();

  @override
  void initState() {
    super.initState();
    _cargar();
  }

  int? _refrescoVisto;

  Future<void> _cargar() async {
    final r = await context.read<OfflineController>().repo.reservasSucursal();
    if (mounted) setState(() => _reservas = r);
  }

  Future<void> _tarea(Map<String, dynamic> r, String tipo, String resumen, Map<String, dynamic> extra, {String? estado, int? itemNoEncontrado, bool quitar = false}) async {
    final c = context.read<OfflineController>();
    await c.registrarTarea(tipo: tipo, payload: {'reserva_id': r['id'], ...extra}, resumen: '$resumen ${r['codigo']}');
    await c.repo.actualizarReservaLocal(r['id'] as int, estado: estado, itemNoEncontrado: itemNoEncontrado, quitar: quitar);
    await _cargar();
  }

  Future<void> _atender(Map<String, dynamic> r) async {
    final lleva = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text('Atender ${r['codigo']}'),
        content: const Text('¿El cliente llevará las prendas?'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Cancelar')),
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('No las lleva')),
          FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Sí las lleva')),
        ],
      ),
    );
    if (lleva == null) return;
    await _tarea(r, 'ATENDER_RESERVA', 'Atención de la reserva', {'llevara_prendas': lleva}, quitar: !lleva, estado: 'EN_PROBADOR');
    if (mounted && lleva) _avisar(context, 'Atención guardada. Registre ahora la venta de contado en «Modo sin conexión → Registrar».');
  }

  @override
  Widget build(BuildContext context) {
    final refresco = context.select<OfflineController, int>((c) => c.refresco);
    if (_refrescoVisto != null && _refrescoVisto != refresco) {
      WidgetsBinding.instance.addPostFrameCallback((_) { if (mounted) _cargar(); }); // al volver la red lo descargado se renueva y la lista se actualiza sola
    }
    _refrescoVisto = refresco;
    final q = _codigo.text.trim().toLowerCase();
    final visibles = _reservas.where((r) => q.isEmpty || '${r['codigo']}'.toLowerCase().contains(q)).toList();
    return ListView(padding: EdgeInsets.fromLTRB(16, 16, 16, MediaQuery.viewPaddingOf(context).bottom + 16), children: [
      TextField(controller: _codigo, onChanged: (_) => setState(() {}), decoration: const InputDecoration(labelText: 'Validar el código de la reserva', prefixIcon: Icon(Icons.qr_code))),
      if (visibles.isEmpty) Padding(padding: const EdgeInsets.all(24), child: Text(textoSinFilas(context.read<OfflineController>(), 'reservas', _codigo.text.trim().isNotEmpty))),
      for (final r in visibles)
        Card(
          child: Padding(
            padding: const EdgeInsets.all(12),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('${r['codigo']} · ${r['estado']}', style: Theme.of(context).textTheme.titleSmall),
              Text('Visita: ${fechaCorta('${r['programada_para']}')}', style: Theme.of(context).textTheme.bodySmall),
              for (final i in (r['items'] as List).cast<Map<String, dynamic>>())
                ListTile(
                  dense: true,
                  contentPadding: EdgeInsets.zero,
                  title: Text('${i['cantidad']}× ${i['producto']} (${i['talla']}, ${i['color']})'),
                  subtitle: Text('${i['estado']}'),
                  trailing: i['estado'] == 'RESERVADO' && r['estado'] != 'EN_PROBADOR'
                      ? TextButton(onPressed: () => _tarea(r, 'PRENDA_NO_ENCONTRADA', 'Prenda no encontrada de la reserva', {'item_id': i['id']}, itemNoEncontrado: i['id'] as int), child: const Text('No encontrada'))
                      : null,
                ),
              Wrap(spacing: 12, runSpacing: 8, children: [
                if (r['estado'] == 'PENDIENTE') OutlinedButton(onPressed: () => _tarea(r, 'PREPARAR_RESERVA', 'Preparación de la reserva', {}, estado: 'PREPARADA'), child: const Text('Preparar')),
                if (r['estado'] == 'PENDIENTE' || r['estado'] == 'PREPARADA') FilledButton(onPressed: () => _atender(r), child: const Text('Atender')),
              ]),
            ]),
          ),
        ),
    ]);
  }
}
