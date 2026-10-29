import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../../core/network/api_client.dart';
import '../../../features/auth/data/auth_repository.dart';
import '../data/reservas_repository.dart';

/// Carrito del cliente (CU-08) y pago de la compra digital (CU-11, CU-32). El stock se descuenta recién cuando el pago se aprueba.
class CarritoScreen extends StatefulWidget {
  const CarritoScreen({super.key});

  @override
  State<CarritoScreen> createState() => _CarritoScreenState();
}

class _CarritoScreenState extends State<CarritoScreen> {
  late final ReservasRepository _repo = ReservasRepository(context.read<AuthRepository>().api);
  Map<String, dynamic>? _carrito;
  String? _error;
  String? _resultado;
  bool _trabajando = false;

  @override
  void initState() {
    super.initState();
    _cargar();
  }

  Future<void> _cargar() async {
    try {
      final c = await _repo.carrito();
      if (mounted) setState(() { _carrito = c; _error = null; });
    } on ApiException catch (e) {
      if (mounted) setState(() => _error = e.sinConexion ? 'Sin conexión: el carrito necesita Internet.' : e.mensaje);
    }
  }

  Future<void> _accion(Future<Map<String, dynamic>> Function() f) async {
    try {
      final c = await f();
      if (mounted) setState(() { _carrito = c; _error = null; });
    } on ApiException catch (e) {
      if (mounted) setState(() => _error = e.mensaje);
    }
  }

  Future<void> _pagar() async {
    setState(() { _trabajando = true; _error = null; _resultado = null; });
    try {
      final pedido = await _repo.checkout();
      final pago = await _repo.iniciarPago(pedido['id'] as int);
      if (pago['modo'] == 'stripe') {
        setState(() => _resultado = 'El pedido ${pedido['codigo']} quedó pendiente de pago. Este entorno usa Stripe: termine el pago desde la versión web.');
      } else {
        final tarjeta = await _pedirTarjeta(pago['monto'] as String);
        if (tarjeta == null) {
          setState(() => _resultado = 'El pedido ${pedido['codigo']} quedó pendiente de pago.');
        } else {
          final r = await _repo.confirmarPago(pago['pago_id'] as int, tarjeta);
          setState(() => _resultado = r['aprobado'] == true ? '✔ Pago aprobado. Comprobante ${(r['pedido'] as Map)['comprobante_numero']}.' : '${r['mensaje']}');
        }
      }
    } on ApiException catch (e) {
      setState(() => _error = e.mensaje);
    }
    await _cargar();
    if (mounted) setState(() => _trabajando = false);
  }

  Future<Map<String, dynamic>?> _pedirTarjeta(String total) {
    final numero = TextEditingController(text: '4242 4242 4242 4242');
    final cvc = TextEditingController(text: '123');
    return showDialog<Map<String, dynamic>>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text('Pagar Bs $total'),
        content: Column(mainAxisSize: MainAxisSize.min, children: [
          const Text('Pasarela de pruebas: no se cobra dinero real. La tarjeta 4000 0000 0000 9995 se rechaza por fondos insuficientes.', style: TextStyle(fontSize: 12)),
          TextField(controller: numero, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'Número de tarjeta')),
          TextField(controller: cvc, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'CVC')),
        ]),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Cancelar')),
          FilledButton(
            onPressed: () => Navigator.pop(ctx, {'numero': numero.text, 'mes': 12, 'anio': DateTime.now().year + 3, 'cvc': cvc.text, 'titular': 'Cliente'}),
            child: const Text('Pagar'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final items = ((_carrito?['items'] as List?) ?? const []).cast<Map<String, dynamic>>();
    return Scaffold(
      appBar: AppBar(title: const Text('Mi carrito')),
      body: RefreshIndicator(
        onRefresh: _cargar,
        child: ListView(padding: const EdgeInsets.all(16), children: [
          if (_error != null) Text(_error!, style: const TextStyle(color: Colors.red)),
          if (_resultado != null) Card(child: Padding(padding: const EdgeInsets.all(12), child: Text(_resultado!))),
          if (_carrito == null && _error == null) const Center(child: CircularProgressIndicator()),
          if (_carrito != null && items.isEmpty) const Padding(padding: EdgeInsets.all(24), child: Center(child: Text('Su carrito está vacío.'))),
          for (final a in ((_carrito?['avisos'] as List?) ?? const [])) Text('$a', style: const TextStyle(color: Color(0xFF8A5A00))),
          for (final it in items)
            Card(
              child: ListTile(
                title: Text('${it['producto']}'),
                subtitle: Text('${it['talla']} · ${it['color']} · Bs ${it['precio_final']} c/u · ${it['disponible']} disponibles'),
                trailing: Row(mainAxisSize: MainAxisSize.min, children: [
                  IconButton(icon: const Icon(Icons.remove_circle_outline), onPressed: (it['cantidad'] as int) > 1 ? () => _accion(() => _repo.cambiarCantidad(it['id'] as int, (it['cantidad'] as int) - 1)) : null),
                  Text('${it['cantidad']}'),
                  IconButton(icon: const Icon(Icons.add_circle_outline), onPressed: () => _accion(() => _repo.cambiarCantidad(it['id'] as int, (it['cantidad'] as int) + 1))),
                  IconButton(icon: const Icon(Icons.delete_outline), onPressed: () => _accion(() => _repo.quitar(it['id'] as int))),
                ]),
              ),
            ),
          if (items.isNotEmpty) ...[
            const Divider(),
            Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [const Text('Total', style: TextStyle(fontWeight: FontWeight.bold)), Text('Bs ${_carrito!['total']}', style: const TextStyle(fontWeight: FontWeight.bold))]),
            Text('Retiro en ${_carrito!['sucursal'] ?? 'la sucursal elegida'} · IVA incluido Bs ${_carrito!['iva_incluido']}', style: Theme.of(context).textTheme.bodySmall),
            const SizedBox(height: 12),
            FilledButton.icon(onPressed: _trabajando || _carrito!['puede_pagar'] != true ? null : _pagar, icon: const Icon(Icons.credit_card), label: Text(_trabajando ? 'Procesando…' : 'Pagar con tarjeta')),
          ],
        ]),
      ),
    );
  }
}
