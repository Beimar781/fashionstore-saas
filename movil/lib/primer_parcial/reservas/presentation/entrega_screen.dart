import 'dart:async';

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../../core/network/api_client.dart';
import '../../../features/offline/presentation/offline_controller.dart';
import '../data/datos_entrega.dart';
import '../data/medio_de_pago.dart';
import '../data/reservas_repository.dart';

/// Lo que el cliente eligió antes de pagar: la entrega y facturación, y con qué tarjeta paga.
typedef EleccionDeCompra = ({DatosEntrega datos, MedioDePago medio});

/// CU-11 y CU-32 · Entrega, facturación y tarjeta, antes de pagar. Devuelve la elección con `Navigator.pop`; si el cliente vuelve atrás, devuelve null.
class EntregaScreen extends StatefulWidget {
  const EntregaScreen({super.key, required this.repo, this.sucursal, this.total});

  final ReservasRepository repo;
  final String? sucursal;

  /// Total del carrito: sin conexión se usa para pedir la autorización del cobro con la tarjeta guardada.
  final String? total;

  @override
  State<EntregaScreen> createState() => _EntregaScreenState();
}

class _EntregaScreenState extends State<EntregaScreen> {
  final _direccion = TextEditingController();
  final _nit = TextEditingController();
  final _razon = TextEditingController();
  bool _domicilio = false;
  List<TarjetaGuardada> _tarjetas = [];
  int? _tarjetaId; // null = tarjeta nueva
  bool _guardar = false;
  bool _autorizo = false;
  String? _error;
  bool get _sinConexion => !context.read<OfflineController>().enLinea;

  @override
  void initState() {
    super.initState();
    _cargarTarjetas();
  }

  @override
  void dispose() {
    _direccion.dispose();
    _nit.dispose();
    _razon.dispose();
    super.dispose();
  }

  Future<void> _cargarTarjetas() async {
    if (_sinConexion) {
      // sin conexión solo se ofrecen las guardadas la última vez con red y no vencidas; una tarjeta nueva necesita Internet
      final locales = [for (final j in await context.read<OfflineController>().repo.tarjetasLocales()) TarjetaGuardada.desdeJson(j)].where((t) => t.vigente(DateTime.now())).toList();
      if (mounted) setState(() { _tarjetas = locales; _tarjetaId = null; });
      return;
    }
    try {
      final t = await widget.repo.tarjetasGuardadas();
      if (mounted) unawaited(context.read<OfflineController>().repo.guardarTarjetas([for (final x in t) x.aJson()])); // copia para comprar sin conexión
      if (mounted) setState(() { _tarjetas = t; _tarjetaId = t.isEmpty ? null : t.first.id; });
    } on ApiException {
      // sin la lista el cliente igual puede pagar con una tarjeta nueva
    }
  }

  Future<void> _eliminar(TarjetaGuardada t) async {
    try {
      await widget.repo.eliminarTarjeta(t.id);
      if (mounted) await context.read<OfflineController>().repo.quitarTarjetaLocal(t.id);
      if (!mounted) return;
      setState(() {
        _tarjetas = _tarjetas.where((x) => x.id != t.id).toList();
        if (_tarjetaId == t.id) _tarjetaId = null;
      });
    } on ApiException catch (e) {
      if (mounted) setState(() => _error = e.mensaje);
    }
  }

  void _continuar() {
    final datos = DatosEntrega(domicilio: _domicilio, direccion: _direccion.text, nitCi: _nit.text, razonSocial: _razon.text);
    final error = datos.validar();
    if (error != null) {
      setState(() => _error = error);
      return;
    }
    if (_sinConexion && _tarjetaId != null && !_autorizo) {
      setState(() => _error = 'Confirme la autorización del cobro para pagar con la tarjeta guardada.');
      return;
    }
    Navigator.pop<EleccionDeCompra>(context, (datos: datos, medio: MedioDePago(tarjetaGuardadaId: _tarjetaId, guardar: _guardar)));
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: const Text('Entrega, facturación y pago')),
        body: ListView(padding: const EdgeInsets.all(16), children: [
          SegmentedButton<bool>(
            segments: [
              ButtonSegment(value: false, icon: const Icon(Icons.store_outlined), label: Text('Retiro en ${widget.sucursal ?? 'la sucursal'}')),
              const ButtonSegment(value: true, icon: Icon(Icons.local_shipping_outlined), label: Text('A domicilio')),
            ],
            selected: {_domicilio},
            onSelectionChanged: (s) => setState(() => _domicilio = s.first),
          ),
          if (_domicilio) ...[
            const SizedBox(height: 12),
            TextField(
              controller: _direccion,
              maxLength: 300,
              decoration: const InputDecoration(labelText: 'Dirección de entrega', hintText: 'Calle, número, barrio y referencia'),
            ),
          ],
          const SizedBox(height: 12),
          TextField(controller: _nit, maxLength: 20, onChanged: (_) => setState(() => _error = null), decoration: const InputDecoration(labelText: 'NIT o CI')),
          TextField(controller: _razon, maxLength: 120, decoration: const InputDecoration(labelText: 'Razón social (opcional)')),
          const SizedBox(height: 8),
          Text('Tarjeta', style: Theme.of(context).textTheme.titleMedium),
          RadioGroup<int?>(
            groupValue: _tarjetaId,
            onChanged: (v) => setState(() => _tarjetaId = v),
            child: Column(children: [
              for (final t in _tarjetas)
                RadioListTile<int?>(
                  value: t.id,
                  contentPadding: EdgeInsets.zero,
                  title: Text(t.descripcion),
                  subtitle: _sinConexion && t.expAnio == DateTime.now().year && t.expMes == DateTime.now().month ? const Text('Vence este mes: si la compra se envía después, quedará por pagar. Puede elegir «Dejar la compra por pagar».', style: TextStyle(fontSize: 12)) : null,
                  secondary: IconButton(tooltip: 'Eliminar tarjeta', icon: const Icon(Icons.delete_outline), onPressed: () => _eliminar(t)),
                ),
              RadioListTile<int?>(value: null, contentPadding: EdgeInsets.zero, title: Text(_sinConexion ? 'Dejar la compra por pagar' : 'Usar otra tarjeta')),
            ]),
          ),
          if (_sinConexion)
            const Padding(
              padding: EdgeInsets.only(bottom: 8),
              child: Text('Para usar una tarjeta nueva necesita Internet. Puede pagar con una tarjeta guardada o dejar la compra por pagar.', style: TextStyle(fontSize: 12)),
            ),
          if (_sinConexion && _tarjetaId != null)
            CheckboxListTile(
              contentPadding: EdgeInsets.zero,
              controlAffinity: ListTileControlAffinity.leading,
              title: Text('Autorizo el cobro de Bs ${widget.total ?? ''} a esta tarjeta cuando se confirme mi compra.'),
              value: _autorizo,
              onChanged: (v) => setState(() => _autorizo = v ?? false),
            ),
          if (!_sinConexion && _tarjetaId == null)
            CheckboxListTile(
              contentPadding: EdgeInsets.zero,
              controlAffinity: ListTileControlAffinity.leading,
              title: const Text('Guardar esta tarjeta para mis próximas compras'),
              value: _guardar,
              onChanged: (v) => setState(() => _guardar = v ?? false),
            ),
          if (_error != null) Padding(padding: const EdgeInsets.only(top: 8), child: Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error))),
          const SizedBox(height: 16),
          FilledButton(onPressed: _continuar, child: Text(_sinConexion ? 'Guardar compra para sincronizar' : 'Continuar al pago')),
        ]),
      );
}
