import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../data/modelos.dart';
import 'offline_controller.dart';

class _Linea {
  _Linea(this.prenda, this.max);
  final PrendaLocal prenda;
  final int max;
  int cantidad = 1;
}

/// RF19 · Registrar sin conexión: el personal registra ventas de contado (RN13) y el cliente reserva. Todo usa el catálogo guardado y queda en la cola.
class RegistrarOfflineTab extends StatefulWidget {
  const RegistrarOfflineTab({super.key});

  @override
  State<RegistrarOfflineTab> createState() => _RegistrarOfflineTabState();
}

class _RegistrarOfflineTabState extends State<RegistrarOfflineTab> {
  final _texto = TextEditingController();
  final _recibido = TextEditingController();
  final _notas = TextEditingController();
  List<PrendaLocal> _resultados = [];
  List<SucursalLocal> _sucursales = [];
  List<ClienteLocal> _clientes = [];
  final List<_Linea> _lineas = [];
  int? _sucursalId;
  String? _clienteEmail;
  DateTime? _visita;
  String _modo = 'RESERVA'; // el cliente reserva o compra
  String? _error;

  @override
  void initState() {
    super.initState();
    _cargar();
  }

  Future<void> _cargar() async {
    final c = context.read<OfflineController>();
    final sucursales = await c.repo.sucursales();
    final clientes = await c.repo.clientes();
    if (!mounted) return;
    setState(() {
      _sucursales = sucursales;
      _clientes = clientes;
      _sucursalId = c.sesion?.sucursalId ?? (sucursales.isNotEmpty ? sucursales.first.id : null);
    });
  }

  Future<void> _buscar(String q) async {
    if (q.trim().isEmpty) {
      setState(() => _resultados = []);
      return;
    }
    final r = await context.read<OfflineController>().repo.buscar(q, limite: 12);
    if (mounted) setState(() => _resultados = r);
  }

  void _agregar(PrendaLocal p) {
    final stock = p.variante.stockEn(_sucursalId);
    final existente = _lineas.where((l) => l.prenda.variante.id == p.variante.id).firstOrNull;
    setState(() {
      if (existente != null) {
        if (existente.cantidad < existente.max) existente.cantidad++;
      } else {
        _lineas.add(_Linea(p, stock));
      }
    });
  }

  double get _total => _lineas.fold(0.0, (t, l) => t + double.parse(l.prenda.variante.precioFinal) * l.cantidad);

  Future<void> _elegirVisita() async {
    final ahora = DateTime.now();
    final fecha = await showDatePicker(context: context, initialDate: ahora.add(const Duration(days: 1)), firstDate: ahora, lastDate: ahora.add(const Duration(days: 14)));
    if (fecha == null || !mounted) return;
    final hora = await showTimePicker(context: context, initialTime: const TimeOfDay(hour: 11, minute: 0));
    if (hora == null) return;
    setState(() => _visita = DateTime(fecha.year, fecha.month, fecha.day, hora.hour, hora.minute));
  }

  Future<void> _registrar() async {
    final c = context.read<OfflineController>();
    final messenger = ScaffoldMessenger.of(context);
    if (_sucursalId == null) return setState(() => _error = 'Elija una sucursal.');
    final items = [for (final l in _lineas) {'variante_id': l.prenda.variante.id, 'cantidad': l.cantidad}];
    final detalle = _lineas.map((l) => '${l.cantidad}× ${l.prenda.texto}').join(', ');
    if (c.esCliente && _modo == 'COMPRA') {
      await c.registrar(
        tipo: 'COMPRA',
        payload: {'sucursal_id': _sucursalId, 'items': items},
        sucursalId: _sucursalId!,
        resumen: 'Compra: $detalle',
      );
    } else if (c.esCliente) {
      if (_visita == null) return setState(() => _error = 'Indique la fecha y hora de su visita.');
      await c.registrar(
        tipo: 'RESERVA',
        payload: {'sucursal_id': _sucursalId, 'programada_para': _visita!.toIso8601String(), 'notas': _notas.text.trim(), 'items': items},
        sucursalId: _sucursalId!,
        resumen: 'Reserva: $detalle',
      );
    } else {
      final recibido = double.tryParse(_recibido.text.replaceAll(',', '.'));
      if (recibido == null || recibido < _total) return setState(() => _error = 'El efectivo recibido es menor al total de la venta.');
      await c.registrar(
        tipo: 'VENTA_CONTADO',
        payload: {'items': items, 'monto_recibido': recibido.toStringAsFixed(2), 'cliente_email': _clienteEmail},
        sucursalId: _sucursalId!,
        resumen: 'Venta de contado Bs ${_total.toStringAsFixed(2)}: $detalle',
      );
    }
    messenger.showSnackBar(SnackBar(content: Text(c.enLinea ? 'Operación registrada; se está sincronizando.' : 'Operación guardada en este dispositivo. Se sincronizará al recuperar la conexión.')));
    _cargar();
    setState(() {
      _lineas.clear();
      _resultados = [];
      _texto.clear();
      _recibido.clear();
      _notas.clear();
      _error = null;
    });
  }

  @override
  Widget build(BuildContext context) {
    final c = context.watch<OfflineController>();
    if (!c.hayCatalogo) {
      return const Center(child: Padding(padding: EdgeInsets.all(24), child: Text('Primero descargue el catálogo (pestaña «Catálogo»).', textAlign: TextAlign.center)));
    }
    final cambio = (double.tryParse(_recibido.text.replaceAll(',', '.')) ?? 0) - _total;
    return ListView(padding: const EdgeInsets.all(16), children: [
      Text(!c.esCliente ? 'Venta de contado sin conexión' : (_modo == 'COMPRA' ? 'Comprar sin conexión' : 'Reservar sin conexión'), style: Theme.of(context).textTheme.titleMedium),
      Text(
        c.esCliente
            ? (_modo == 'COMPRA'
                ? 'La compra queda registrada en el dispositivo. Al recuperar la conexión verificamos que la prenda siga disponible y le avisamos para que la pague con tarjeta en «Mis compras»; no se cobra nada sin conexión.'
                : 'La reserva se confirma cuando el dispositivo recupere la conexión.')
            : 'Las ventas sin conexión son de contado. Recibir el efectivo aquí no significa que el servidor ya la aceptó: se confirma al sincronizar.',
        style: Theme.of(context).textTheme.bodySmall,
      ),
      const SizedBox(height: 8),
      if (c.esCliente) ...[
        DropdownButtonFormField<String>(
          initialValue: _modo,
          decoration: const InputDecoration(labelText: '¿Qué desea hacer?'),
          items: const [
            DropdownMenuItem(value: 'RESERVA', child: Text('Reservar para probarme')),
            DropdownMenuItem(value: 'COMPRA', child: Text('Comprar (pago con tarjeta al sincronizar)')),
          ],
          onChanged: (v) => setState(() => _modo = v ?? 'RESERVA'),
        ),
        const SizedBox(height: 8),
        DropdownButtonFormField<int>(
          initialValue: _sucursales.any((s) => s.id == _sucursalId) ? _sucursalId : null,
          decoration: const InputDecoration(labelText: 'Sucursal'),
          items: [for (final s in _sucursales) DropdownMenuItem(value: s.id, child: Text('${s.nombre}${s.ciudad != null ? ' · ${s.ciudad}' : ''}'))],
          onChanged: (v) => setState(() {
            _sucursalId = v;
            _lineas.clear();
          }),
        ),
        const SizedBox(height: 8),
        if (_modo == 'RESERVA') OutlinedButton.icon(
          onPressed: _elegirVisita,
          icon: const Icon(Icons.event),
          label: Text(_visita == null ? 'Elegir fecha y hora de visita' : 'Visita: ${_visita!.day}/${_visita!.month}/${_visita!.year} ${_visita!.hour.toString().padLeft(2, '0')}:${_visita!.minute.toString().padLeft(2, '0')}'),
        ),
        const SizedBox(height: 8),
      ],
      TextField(controller: _texto, onChanged: _buscar, decoration: const InputDecoration(labelText: 'Buscar prenda (nombre, SKU o código de barras)', prefixIcon: Icon(Icons.search))),
      Wrap(spacing: 6, children: [
        for (final r in _resultados)
          ActionChip(
            label: Text('${r.texto} · Bs ${r.variante.precioFinal} (${r.variante.stockEn(_sucursalId)})'),
            onPressed: r.variante.stockEn(_sucursalId) == 0 ? null : () => _agregar(r),
          ),
      ]),
      for (final l in _lineas)
        ListTile(
          dense: true,
          title: Text(l.prenda.texto),
          subtitle: Text('Bs ${l.prenda.variante.precioFinal} c/u'),
          trailing: Row(mainAxisSize: MainAxisSize.min, children: [
            IconButton(icon: const Icon(Icons.remove_circle_outline), onPressed: l.cantidad > 1 ? () => setState(() => l.cantidad--) : null),
            Text('${l.cantidad}'),
            IconButton(icon: const Icon(Icons.add_circle_outline), onPressed: l.cantidad < l.max ? () => setState(() => l.cantidad++) : null),
            IconButton(icon: const Icon(Icons.close), onPressed: () => setState(() => _lineas.remove(l))),
          ]),
        ),
      if (_lineas.isNotEmpty) ...[
        const Divider(),
        Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [const Text('Total', style: TextStyle(fontWeight: FontWeight.bold)), Text('Bs ${_total.toStringAsFixed(2)}', style: const TextStyle(fontWeight: FontWeight.bold))]),
        const SizedBox(height: 8),
        if (c.esCliente && _modo == 'COMPRA')
          const Text('Si cuando sincronice la prenda ya se agotó, le avisaremos y no se le cobrará nada.')
        else if (c.esCliente)
          TextField(controller: _notas, decoration: const InputDecoration(labelText: 'Notas (opcional)'))
        else ...[
          TextField(controller: _recibido, keyboardType: const TextInputType.numberWithOptions(decimal: true), onChanged: (_) => setState(() {}), decoration: const InputDecoration(labelText: 'Efectivo recibido (Bs)')),
          Text(cambio < 0 ? 'Cambio a entregar: —' : 'Cambio a entregar: Bs ${cambio.toStringAsFixed(2)}'),
          const SizedBox(height: 8),
          DropdownButtonFormField<String?>(
            initialValue: _clienteEmail,
            decoration: const InputDecoration(labelText: 'Cliente (opcional)'),
            items: [
              const DropdownMenuItem<String?>(value: null, child: Text('Consumidor final')),
              for (final cl in _clientes) DropdownMenuItem<String?>(value: cl.email, child: Text('${cl.nombre} · ${cl.email}')),
            ],
            onChanged: (v) => setState(() => _clienteEmail = v),
          ),
        ],
        if (_error != null) Padding(padding: const EdgeInsets.only(top: 8), child: Text(_error!, style: const TextStyle(color: Colors.red))),
        const SizedBox(height: 12),
        FilledButton(onPressed: _registrar, child: Text(!c.esCliente ? 'Registrar venta en el dispositivo' : (_modo == 'COMPRA' ? 'Registrar compra en el dispositivo' : 'Registrar reserva en el dispositivo'))),
      ],
    ]);
  }
}
