import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../../core/network/api_client.dart';
import '../../../features/auth/data/auth_repository.dart';
import '../../ventas/data/comprobante_movil.dart';
import '../../ventas/data/ventas_repository.dart';
import '../../ventas/presentation/boton_comprobante.dart';
import '../data/datos_entrega.dart';
import '../data/hoja_de_pago.dart';
import '../data/pago_movil.dart';
import '../data/reservas_repository.dart';
import 'entrega_screen.dart';

/// Carrito del cliente (CU-08) y pago de la compra digital (CU-11, CU-32). El stock se descuenta recién cuando el pago se aprueba.
class CarritoScreen extends StatefulWidget {
  const CarritoScreen({super.key});

  @override
  State<CarritoScreen> createState() => _CarritoScreenState();
}

class _CarritoScreenState extends State<CarritoScreen> {
  late final ReservasRepository _repo = ReservasRepository(context.read<AuthRepository>().api);
  late final PagoMovil _pago = PagoMovil(_repo, HojaDePagoStripe());
  late final ComprobanteMovil _comprobante = ComprobanteMovil(VentasRepository(context.read<AuthRepository>().api));
  Map<String, dynamic>? _carrito;
  String? _error;
  ResultadoPagoMovil? _resultado;
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
    final datos = await Navigator.push<DatosEntrega>(context, MaterialPageRoute(builder: (_) => EntregaScreen(sucursal: _carrito?['sucursal'] as String?)));
    if (datos == null || !mounted) return; // el cliente volvió sin continuar
    setState(() { _trabajando = true; _error = null; _resultado = null; });
    await _mostrar(await _pago.pagar(datos: datos, pedirTarjeta: _pedirTarjeta));
  }

  Future<void> _verificar(int pagoId) async {
    setState(() => _trabajando = true);
    await _mostrar(await _pago.verificar(pagoId));
  }

  Future<void> _mostrar(ResultadoPagoMovil r) async {
    if (!mounted) return;
    setState(() => _resultado = r);
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

  Widget _tarjetaResultado(ResultadoPagoMovil r) => Card(
        color: switch (r.tipo) {
          TipoPago.aprobado => const Color(0xFFE6F4EA),
          TipoPago.rechazado || TipoPago.error => const Color(0xFFFDE7E7),
          _ => null,
        },
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(r.mensaje),
            if (r.tipo == TipoPago.aprobado && r.pedidoId != null)
              BotonComprobante(comprobante: _comprobante, pedidoId: r.pedidoId!, numero: r.comprobante ?? ''),
            if (r.tipo == TipoPago.pendiente && r.pagoId != null)
              TextButton(onPressed: _trabajando ? null : () => _verificar(r.pagoId!), child: const Text('Verificar estado del pago')),
          ]),
        ),
      );

  @override
  Widget build(BuildContext context) {
    final items = ((_carrito?['items'] as List?) ?? const []).cast<Map<String, dynamic>>();
    return Scaffold(
      appBar: AppBar(title: const Text('Mi carrito')),
      body: RefreshIndicator(
        onRefresh: _cargar,
        child: ListView(padding: const EdgeInsets.all(16), children: [
          if (_error != null) Text(_error!, style: const TextStyle(color: Colors.red)),
          if (_resultado != null) _tarjetaResultado(_resultado!),
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
