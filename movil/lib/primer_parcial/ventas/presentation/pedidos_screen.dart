import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../../core/network/api_client.dart';
import '../../../features/auth/data/auth_repository.dart';
import '../../../features/offline/presentation/modo_offline_screen.dart'
    show fechaCorta;
import '../data/comprobante_movil.dart';
import '../data/ventas_repository.dart';
import '../../reservas/data/hoja_de_pago.dart';
import '../../reservas/data/pago_movil.dart';
import '../../reservas/data/reservas_repository.dart';
import 'boton_comprobante.dart';

/// Historial de compras del cliente (CU-12): compras digitales y de mostrador, con su estado y comprobante.
class PedidosScreen extends StatefulWidget {
  const PedidosScreen({super.key, this.integrado = false});
  final bool integrado;

  @override
  State<PedidosScreen> createState() => _PedidosScreenState();
}

class _PedidosScreenState extends State<PedidosScreen> {
  late final VentasRepository _repo =
      VentasRepository(context.read<AuthRepository>().api);
  late final ComprobanteMovil _comprobante = ComprobanteMovil(_repo);
  late final ReservasRepository _reservas =
      ReservasRepository(context.read<AuthRepository>().api);
  late final PagoMovil _pago = PagoMovil(_reservas, HojaDePagoStripe());
  List<Map<String, dynamic>>? _compras;
  String? _error;

  @override
  void initState() {
    super.initState();
    _cargar();
  }

  Future<void> _cargar() async {
    try {
      final c = await _repo.compras();
      if (mounted) {
        setState(() {
          _compras = c;
          _error = null;
        });
      }
    } on ApiException catch (e) {
      if (mounted) {
        setState(() => _error = e.sinConexion
            ? 'Sin conexión: no se puede consultar el historial.'
            : e.mensaje);
      }
    }
  }

  Future<void> _ver(Map<String, dynamic> c) async {
    try {
      final p = await _repo.detalle(c['id'] as int);
      if (!mounted) return;
      await showDialog<void>(
        context: context,
        builder: (ctx) => AlertDialog(
          title: Text('${p['codigo']}'),
          content: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                for (final i
                    in (p['items'] as List).cast<Map<String, dynamic>>())
                  Text(
                      '${i['cantidad']}× ${i['producto']} (${i['talla']}, ${i['color']}) · Bs ${i['subtotal']}'),
                const Divider(),
                Text('Total Bs ${p['total']}',
                    style: const TextStyle(fontWeight: FontWeight.bold)),
                if (p['comprobante_numero'] != null)
                  Text('Comprobante ${p['comprobante_numero']}'),
              ]),
          actions: [
            if (p['estado'] == 'PENDIENTE_PAGO')
              FilledButton.icon(
                onPressed: () {
                  Navigator.pop(ctx);
                  _pagar(p);
                },
                icon: const Icon(Icons.credit_card),
                label: const Text('Pagar con tarjeta'),
              ),
            if (p['comprobante_numero'] != null)
              BotonComprobante(
                  comprobante: _comprobante,
                  pedidoId: p['id'] as int,
                  numero: '${p['comprobante_numero']}'),
            TextButton(
                onPressed: () => Navigator.pop(ctx),
                child: const Text('Cerrar')),
          ],
        ),
      );
    } on ApiException catch (e) {
      if (mounted) setState(() => _error = e.mensaje);
    }
  }

  Future<void> _pagar(Map<String, dynamic> pedido) async {
    final resultado = await _pago.pagarPedido(
      pedidoId: pedido['id'] as int,
      pedidoCodigo: pedido['codigo'] as String?,
      pedirTarjeta: _pedirTarjeta,
    );
    if (!mounted) return;
    await showDialog<void>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Pago de la compra'),
        content: Text(resultado.mensaje),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(ctx), child: const Text('Cerrar'))
        ],
      ),
    );
    await _cargar();
  }

  Future<Map<String, dynamic>?> _pedirTarjeta(String total) {
    final numero = TextEditingController(text: '4242 4242 4242 4242');
    final cvc = TextEditingController(text: '123');
    return showDialog<Map<String, dynamic>>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text('Pagar Bs $total'),
        content: Column(mainAxisSize: MainAxisSize.min, children: [
          const Text('Pasarela de pruebas: no se cobra dinero real.'),
          TextField(
              controller: numero,
              keyboardType: TextInputType.number,
              decoration:
                  const InputDecoration(labelText: 'Número de tarjeta')),
          TextField(
              controller: cvc,
              keyboardType: TextInputType.number,
              decoration: const InputDecoration(labelText: 'CVC')),
        ]),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(ctx),
              child: const Text('Cancelar')),
          FilledButton(
              onPressed: () => Navigator.pop(ctx, {
                    'numero': numero.text,
                    'mes': 12,
                    'anio': DateTime.now().year + 3,
                    'cvc': cvc.text,
                    'titular': 'Cliente'
                  }),
              child: const Text('Pagar')),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar:
          widget.integrado ? null : AppBar(title: const Text('Mis compras')),
      body: RefreshIndicator(
        onRefresh: _cargar,
        child: ListView(
            padding: EdgeInsets.fromLTRB(
                16, 16, 16, MediaQuery.viewPaddingOf(context).bottom + 16),
            children: [
              if (_error != null)
                Text(_error!, style: const TextStyle(color: Colors.red)),
              if (_compras == null && _error == null)
                const Center(child: CircularProgressIndicator()),
              if (_compras != null && _compras!.isEmpty)
                const Padding(
                    padding: EdgeInsets.all(24),
                    child: Center(child: Text('Todavía no tiene compras.'))),
              for (final c in _compras ?? const <Map<String, dynamic>>[])
                Card(
                  child: ListTile(
                    onTap: () => _ver(c),
                    title: Text('${c['codigo']} · Bs ${c['total']}'),
                    trailing: c['comprobante_numero'] == null
                        ? null
                        : BotonComprobante(
                            comprobante: _comprobante,
                            pedidoId: c['id'] as int,
                            numero: '${c['comprobante_numero']}'),
                    subtitle: Text(
                        '${c['estado']} · ${c['sucursal']} · ${fechaCorta(c['fecha'] as String?)}${c['comprobante_numero'] != null ? '\n${c['comprobante_numero']}' : ''}'),
                    isThreeLine: c['comprobante_numero'] != null,
                  ),
                ),
            ]),
      ),
    );
  }
}
