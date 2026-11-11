import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../data/modelos.dart';
import 'comprobante_provisional_accion.dart';
import 'escaner_screen.dart';
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
  final _direccionEntrega = TextEditingController();
  final _nitCi = TextEditingController();
  final _razonSocial = TextEditingController();
  final _codigoReserva = TextEditingController();
  Map<String, dynamic>? _reserva; // reserva preparada o atendida que se está cobrando (copia descargada)
  List<PrendaLocal> _resultados = [];
  List<SucursalLocal> _sucursales = [];
  List<ClienteLocal> _clientes = [];
  final List<_Linea> _lineas = [];
  int? _sucursalId;
  String? _clienteEmail;
  DateTime? _visita;
  String _modo = 'RESERVA'; // el cliente reserva o compra
  String _tipoEntrega = 'RETIRO';
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
    final empresaId = c.sesion?.empresaId;
    final usuarioId = c.sesion?.usuarioId;
    final guardado = c.esCliente && empresaId != null && usuarioId != null
        ? await c.repo.carritoClienteLocal(empresaId, usuarioId)
        : null;
    final prendas = guardado == null
        ? <PrendaLocal>[]
        : await c.repo.buscar('', limite: 1000);
    if (!mounted) return;
    setState(() {
      _sucursales = sucursales;
      _clientes = clientes;
      _sucursalId = c.sesion?.sucursalId ??
          (sucursales.isNotEmpty ? sucursales.first.id : null);
      if (guardado != null) {
        _modo = 'COMPRA';
        _tipoEntrega = guardado['tipo_entrega'] as String? ?? 'RETIRO';
        _direccionEntrega.text = guardado['direccion_entrega'] as String? ?? '';
        _nitCi.text = guardado['nit_ci'] as String? ?? '';
        _razonSocial.text = guardado['razon_social'] as String? ?? '';
        _sucursalId = guardado['sucursal_id'] as int? ?? _sucursalId;
        for (final item in (guardado['items'] as List? ?? const [])
            .cast<Map<String, dynamic>>()) {
          final varianteId = item['variante_id'] as int;
          final prenda =
              prendas.where((p) => p.variante.id == varianteId).firstOrNull;
          if (prenda == null) continue;
          final linea = _Linea(prenda, prenda.variante.stockEn(_sucursalId))
            ..cantidad = (item['cantidad'] as int).clamp(1, 50).toInt();
          _lineas.add(linea);
        }
      }
    });
  }

  Future<void> _buscar(String q) async {
    if (q.trim().isEmpty) {
      setState(() => _resultados = []);
      return;
    }
    final r =
        await context.read<OfflineController>().repo.buscar(q, limite: 12);
    if (mounted) setState(() => _resultados = r);
  }

  /// B7: escanea el código de barras o QR y agrega la prenda a la operación (si el código no es único, se muestran las coincidencias).
  Future<void> _escanear() async {
    final codigo = await escanearCodigo(context);
    if (codigo == null || !mounted) return;
    _texto.text = codigo;
    final r = await context.read<OfflineController>().repo.buscar(codigo, limite: 12);
    if (!mounted) return;
    setState(() => _resultados = r);
    if (r.length == 1 && r.first.variante.stockEn(_sucursalId) > 0) _agregar(r.first);
    if (r.isEmpty) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('No hay una prenda con ese código en el catálogo guardado.')));
  }

  /// Cobrar una reserva sin conexión: sale de la copia descargada y solo se puede cobrar si ya está preparada o atendida (CU-29).
  /// Se cargan sus prendas tal como se reservaron; su stock ya estaba apartado, así que la venta no lo descuenta otra vez.
  Future<void> _cargarReserva() async {
    final c = context.read<OfflineController>();
    final codigo = _codigoReserva.text.trim().toUpperCase();
    final reserva = (await c.repo.reservasSucursal()).where((r) => '${r['codigo']}'.toUpperCase() == codigo).firstOrNull;
    if (reserva == null || !['PREPARADA', 'EN_PROBADOR'].contains(reserva['estado'])) {
      return setState(() => _error = 'El código de reserva no existe, no está lista para cobrar o no está en la copia de este dispositivo.');
    }
    final prendas = await c.repo.buscar('', limite: 100000);
    final lineas = <_Linea>[];
    for (final item in (reserva['items'] as List).cast<Map<String, dynamic>>().where((i) => i['estado'] == 'RESERVADO')) {
      final prenda = prendas.where((p) => p.variante.id == item['variante_id']).firstOrNull;
      if (prenda != null) lineas.add(_Linea(prenda, item['cantidad'] as int)..cantidad = item['cantidad'] as int);
    }
    if (!mounted) return;
    setState(() {
      _reserva = reserva;
      _lineas
        ..clear()
        ..addAll(lineas);
      _error = null;
      _codigoReserva.clear();
    });
  }

  void _agregar(PrendaLocal p) {
    final stock = p.variante.stockEn(_sucursalId);
    final existente =
        _lineas.where((l) => l.prenda.variante.id == p.variante.id).firstOrNull;
    setState(() {
      if (existente != null) {
        if (existente.cantidad < existente.max) existente.cantidad++;
      } else {
        _lineas.add(_Linea(p, stock));
      }
    });
    if (_modo == 'COMPRA') _guardarCarrito();
  }

  Future<void> _guardarCarrito() async {
    final c = context.read<OfflineController>();
    final sesion = c.sesion;
    final empresaId = sesion?.empresaId;
    final usuarioId = sesion?.usuarioId;
    if (!c.esCliente || empresaId == null || usuarioId == null) {
      return;
    }
    if (_modo != 'COMPRA' || _lineas.isEmpty || _sucursalId == null) {
      await c.repo.limpiarCarritoCliente(empresaId, usuarioId);
      return;
    }
    await c.repo.guardarCarritoCliente({
      'sucursal_id': _sucursalId,
      'tipo_entrega': _tipoEntrega,
      'direccion_entrega': _direccionEntrega.text.trim(),
      'nit_ci': _nitCi.text.trim(),
      'razon_social': _razonSocial.text.trim(),
      'items': [
        for (final l in _lineas)
          {'variante_id': l.prenda.variante.id, 'cantidad': l.cantidad}
      ],
    }, empresaId, usuarioId);
  }

  double get _total => _lineas.fold(0.0,
      (t, l) => t + double.parse(l.prenda.variante.precioFinal) * l.cantidad);

  Future<void> _elegirVisita() async {
    final ahora = DateTime.now();
    final fecha = await showDatePicker(
        context: context,
        initialDate: ahora.add(const Duration(days: 1)),
        firstDate: ahora,
        lastDate: ahora.add(const Duration(days: 14)));
    if (fecha == null || !mounted) return;
    final hora = await showTimePicker(
        context: context, initialTime: const TimeOfDay(hour: 11, minute: 0));
    if (hora == null) return;
    setState(() => _visita =
        DateTime(fecha.year, fecha.month, fecha.day, hora.hour, hora.minute));
  }

  Future<void> _registrar() async {
    final c = context.read<OfflineController>();
    final messenger = ScaffoldMessenger.of(context);
    if (_sucursalId == null) {
      return setState(() => _error = 'Elija una sucursal.');
    }
    if (c.esCliente && _modo == 'COMPRA' && _nitCi.text.trim().length < 3) {
      return setState(
          () => _error = 'Ingrese su NIT o CI para la facturación.');
    }
    if (c.esCliente &&
        _modo == 'COMPRA' &&
        _tipoEntrega == 'DELIVERY' &&
        _direccionEntrega.text.trim().isEmpty) {
      return setState(() => _error = 'Ingrese la dirección de entrega.');
    }
    OperacionLocal? venta;
    final items = [
      for (final l in _lineas)
        {'variante_id': l.prenda.variante.id, 'cantidad': l.cantidad}
    ];
    final detalle =
        _lineas.map((l) => '${l.cantidad}× ${l.prenda.texto}').join(', ');
    if (c.esCliente && _modo == 'COMPRA') {
      await c.registrar(
        tipo: 'COMPRA',
        payload: {
          'sucursal_id': _sucursalId,
          'tipo_entrega': _tipoEntrega,
          'direccion_entrega': _direccionEntrega.text.trim(),
          'nit_ci': _nitCi.text.trim(),
          'razon_social': _razonSocial.text.trim(),
          'items': items
        },
        sucursalId: _sucursalId!,
        resumen: 'Compra: $detalle',
      );
      final empresaId = c.sesion?.empresaId;
      final usuarioId = c.sesion?.usuarioId;
      if (empresaId != null && usuarioId != null) {
        await c.repo.limpiarCarritoCliente(empresaId, usuarioId);
      }
    } else if (c.esCliente) {
      if (_visita == null) {
        return setState(() => _error = 'Indique la fecha y hora de su visita.');
      }
      await c.registrar(
        tipo: 'RESERVA',
        payload: {
          'sucursal_id': _sucursalId,
          'programada_para': _visita!.toIso8601String(),
          'notas': _notas.text.trim(),
          'items': items
        },
        sucursalId: _sucursalId!,
        resumen: 'Reserva: $detalle',
      );
    } else {
      final recibido = double.tryParse(_recibido.text.replaceAll(',', '.'));
      if (recibido == null || recibido < _total) {
        return setState(() =>
            _error = 'El efectivo recibido es menor al total de la venta.');
      }
      venta = await c.registrar(
        tipo: 'VENTA_CONTADO',
        payload: {
          // el precio que se usó al registrar y la forma de pago viajan con la venta (§7.2)
          'items': [
            for (final l in _lineas)
              {'variante_id': l.prenda.variante.id, 'cantidad': l.cantidad, 'precio_unitario': l.prenda.variante.precioFinal}
          ],
          'forma_pago': 'EFECTIVO',
          'monto_recibido': recibido.toStringAsFixed(2),
          if (_reserva != null) 'reserva_codigo': _reserva!['codigo'] else 'cliente_email': _clienteEmail
        },
        sucursalId: _sucursalId!,
        resumen: '${_reserva != null ? 'Cobro de la reserva ${_reserva!['codigo']}' : 'Venta de contado'} Bs ${_total.toStringAsFixed(2)}: $detalle',
        comprometer: _reserva == null, // la reserva ya tenía su stock apartado
      );
      if (_reserva != null) await c.repo.actualizarReservaLocal(_reserva!['id'] as int, quitar: true); // ya se cobró: sale de la copia
    }
    final vendida = venta;
    messenger.showSnackBar(SnackBar(
        content: Text(c.enLinea
            ? 'Operación registrada; se está sincronizando.'
            : 'Operación guardada en este dispositivo. Se sincronizará al recuperar la conexión.'),
        duration: const Duration(seconds: 10),
        action: vendida == null ? null : SnackBarAction(label: 'Comprobante', onPressed: () => verComprobanteProvisional(context, vendida))));
    setState(() {
      _lineas.clear();
      _resultados = [];
      _texto.clear();
      _recibido.clear();
      _reserva = null;
      _notas.clear();
      _direccionEntrega.clear();
      _nitCi.clear();
      _razonSocial.clear();
      _error = null;
    });
    _cargar();
  }

  @override
  Widget build(BuildContext context) {
    final c = context.watch<OfflineController>();
    if (!c.hayCatalogo) {
      return const Center(
          child: Padding(
              padding: EdgeInsets.all(24),
              child: Text('Primero descargue el catálogo (pestaña «Catálogo»).',
                  textAlign: TextAlign.center)));
    }
    final cambio =
        (double.tryParse(_recibido.text.replaceAll(',', '.')) ?? 0) - _total;
    return ListView(padding: const EdgeInsets.all(16), children: [
      Text(
          !c.esCliente
              ? 'Venta de contado sin conexión'
              : (_modo == 'COMPRA'
                  ? 'Comprar sin conexión'
                  : 'Reservar sin conexión'),
          style: Theme.of(context).textTheme.titleMedium),
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
            DropdownMenuItem(
                value: 'RESERVA', child: Text('Reservar para probarme')),
            DropdownMenuItem(
                value: 'COMPRA',
                child: Text('Comprar (pago con tarjeta al sincronizar)')),
          ],
          onChanged: (v) {
            setState(() => _modo = v ?? 'RESERVA');
            _guardarCarrito();
          },
        ),
        const SizedBox(height: 8),
        if (_modo == 'COMPRA') ...[
          DropdownButtonFormField<String>(
            initialValue: _tipoEntrega,
            decoration: const InputDecoration(labelText: 'Tipo de entrega'),
            items: const [
              DropdownMenuItem(
                  value: 'RETIRO', child: Text('Retiro en sucursal')),
              DropdownMenuItem(
                  value: 'DELIVERY', child: Text('Entrega a domicilio'))
            ],
            onChanged: (v) {
              setState(() => _tipoEntrega = v ?? 'RETIRO');
              _guardarCarrito();
            },
          ),
          if (_tipoEntrega == 'DELIVERY')
            TextField(
                controller: _direccionEntrega,
                maxLength: 300,
                onChanged: (_) => _guardarCarrito(),
                decoration:
                    const InputDecoration(labelText: 'Dirección de entrega')),
          TextField(
              controller: _nitCi,
              maxLength: 20,
              onChanged: (_) => _guardarCarrito(),
              decoration: const InputDecoration(labelText: 'NIT o CI')),
          TextField(
              controller: _razonSocial,
              maxLength: 120,
              onChanged: (_) => _guardarCarrito(),
              decoration:
                  const InputDecoration(labelText: 'Razón social (opcional)')),
        ],
        DropdownButtonFormField<int>(
          initialValue:
              _sucursales.any((s) => s.id == _sucursalId) ? _sucursalId : null,
          decoration: const InputDecoration(labelText: 'Sucursal'),
          items: [
            for (final s in _sucursales)
              DropdownMenuItem(
                  value: s.id,
                  child: Text(
                      '${s.nombre}${s.ciudad != null ? ' · ${s.ciudad}' : ''}'))
          ],
          onChanged: (v) {
            setState(() {
              _sucursalId = v;
              _lineas.clear();
            });
            _guardarCarrito();
          },
        ),
        const SizedBox(height: 8),
        if (_modo == 'RESERVA')
          OutlinedButton.icon(
            onPressed: _elegirVisita,
            icon: const Icon(Icons.event),
            label: Text(_visita == null
                ? 'Elegir fecha y hora de visita'
                : 'Visita: ${_visita!.day}/${_visita!.month}/${_visita!.year} ${_visita!.hour.toString().padLeft(2, '0')}:${_visita!.minute.toString().padLeft(2, '0')}'),
          ),
        const SizedBox(height: 8),
      ],
      if (!c.esCliente)
        if (_reserva == null)
          Row(children: [
            Expanded(child: TextField(controller: _codigoReserva, textCapitalization: TextCapitalization.characters, decoration: const InputDecoration(labelText: 'Cobrar una reserva (código)'))),
            IconButton(tooltip: 'Cargar la reserva', icon: const Icon(Icons.event_available), onPressed: _cargarReserva),
          ])
        else
          Card(
            color: const Color(0xFFE8F3EC),
            child: ListTile(
              dense: true,
              title: Text('Reserva ${_reserva!['codigo']} de ${_reserva!['cliente'] ?? 'cliente'}'),
              subtitle: const Text('Se cobra lo reservado; su stock ya estaba apartado.'),
              trailing: IconButton(tooltip: 'Quitar la reserva', icon: const Icon(Icons.close), onPressed: () => setState(() { _reserva = null; _lineas.clear(); })),
            ),
          ),
      TextField(
          controller: _texto,
          onChanged: _buscar,
          decoration: InputDecoration(
              labelText: 'Buscar prenda (nombre, SKU o código de barras)',
              prefixIcon: const Icon(Icons.search),
              suffixIcon: IconButton(tooltip: 'Escanear código', icon: const Icon(Icons.qr_code_scanner), onPressed: _escanear))),
      Wrap(spacing: 6, children: [
        for (final r in _resultados)
          ActionChip(
            label: Text(
                '${r.texto} · Bs ${r.variante.precioFinal} (${r.variante.stockEn(_sucursalId)})'),
            onPressed:
                r.variante.stockEn(_sucursalId) == 0 ? null : () => _agregar(r),
          ),
      ]),
      for (final l in _lineas)
        ListTile(
          dense: true,
          title: Text(l.prenda.texto),
          subtitle: Text('Bs ${l.prenda.variante.precioFinal} c/u'),
          trailing: Row(mainAxisSize: MainAxisSize.min, children: [
            IconButton(
                icon: const Icon(Icons.remove_circle_outline),
                onPressed: l.cantidad > 1
                    ? () {
                        setState(() => l.cantidad--);
                        _guardarCarrito();
                      }
                    : null),
            Text('${l.cantidad}'),
            IconButton(
                icon: const Icon(Icons.add_circle_outline),
                onPressed: l.cantidad < l.max
                    ? () {
                        setState(() => l.cantidad++);
                        _guardarCarrito();
                      }
                    : null),
            IconButton(
                icon: const Icon(Icons.close),
                onPressed: () {
                  setState(() => _lineas.remove(l));
                  _guardarCarrito();
                }),
          ]),
        ),
      if (_lineas.isNotEmpty) ...[
        const Divider(),
        Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
          const Text('Total', style: TextStyle(fontWeight: FontWeight.bold)),
          Text('Bs ${_total.toStringAsFixed(2)}',
              style: const TextStyle(fontWeight: FontWeight.bold))
        ]),
        const SizedBox(height: 8),
        if (c.esCliente && _modo == 'COMPRA')
          const Text(
              'Si cuando sincronice la prenda ya se agotó, le avisaremos y no se le cobrará nada.')
        else if (c.esCliente)
          TextField(
              controller: _notas,
              decoration: const InputDecoration(labelText: 'Notas (opcional)'))
        else ...[
          TextField(
              controller: _recibido,
              keyboardType:
                  const TextInputType.numberWithOptions(decimal: true),
              onChanged: (_) => setState(() {}),
              decoration:
                  const InputDecoration(labelText: 'Efectivo recibido (Bs)')),
          Text(cambio < 0
              ? 'Cambio a entregar: —'
              : 'Cambio a entregar: Bs ${cambio.toStringAsFixed(2)}'),
          const SizedBox(height: 8),
          DropdownButtonFormField<String?>(
            initialValue: _clienteEmail,
            decoration: const InputDecoration(labelText: 'Cliente (opcional)'),
            items: [
              const DropdownMenuItem<String?>(
                  value: null, child: Text('Consumidor final')),
              for (final cl in _clientes)
                DropdownMenuItem<String?>(
                    value: cl.email, child: Text('${cl.nombre} · ${cl.email}')),
            ],
            onChanged: (v) => setState(() => _clienteEmail = v),
          ),
        ],
        if (_error != null)
          Padding(
              padding: const EdgeInsets.only(top: 8),
              child: Text(_error!, style: const TextStyle(color: Colors.red))),
        const SizedBox(height: 12),
        FilledButton(
            onPressed: _registrar,
            child: Text(!c.esCliente
                ? 'Registrar venta en el dispositivo'
                : (_modo == 'COMPRA'
                    ? 'Registrar compra en el dispositivo'
                    : 'Registrar reserva en el dispositivo'))),
      ],
    ]);
  }
}
