import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../../core/network/api_client.dart';
import '../../auth/data/auth_repository.dart';

const msgPlanSinOffline = 'Su plan no incluye el modo sin conexión: la Caja funciona solo con Internet.';
const msgCajaNecesitaInternet = 'Esta función necesita Internet.';

/// CU-28 a CU-30 · Caja con conexión para el Cajero y el Encargado cuando el plan de la empresa NO incluye el modo sin conexión.
/// Usa el servidor directamente (buscar la prenda, registrar la venta y cobrarla en efectivo); sin Internet lo dice en vez de fallar.
class CajaEnLineaScreen extends StatefulWidget {
  const CajaEnLineaScreen({super.key, this.api});

  /// Solo para pruebas; en la app se usa el cliente de la sesión.
  final ApiClient? api;

  @override
  State<CajaEnLineaScreen> createState() => _CajaEnLineaScreenState();
}

class _Linea {
  _Linea(this.prenda);
  final Map<String, dynamic> prenda;
  int cantidad = 1;
  double get subtotal => (double.tryParse('${prenda['precio_final']}') ?? 0) * cantidad;
}

class _CajaEnLineaScreenState extends State<CajaEnLineaScreen> {
  final _texto = TextEditingController();
  final _recibido = TextEditingController();
  final List<_Linea> _lineas = [];
  List<Map<String, dynamic>> _resultados = [];
  String? _error;
  String? _comprobante;
  bool _trabajando = false;

  ApiClient get _api => widget.api ?? context.read<AuthRepository>().api;

  double get _total => _lineas.fold(0.0, (t, l) => t + l.subtotal);

  String _mensaje(ApiException e) => e.sinConexion ? '$msgCajaNecesitaInternet $msgPlanSinOffline' : e.mensaje;

  Future<void> _buscar() async {
    final q = _texto.text.trim();
    if (q.isEmpty) return setState(() => _resultados = []);
    setState(() { _trabajando = true; _error = null; });
    try {
      final r = (await _api.getLista('/caja/productos?q=${Uri.encodeQueryComponent(q)}')).cast<Map<String, dynamic>>();
      if (mounted) setState(() => _resultados = r);
    } on ApiException catch (e) {
      if (mounted) setState(() => _error = _mensaje(e));
    }
    if (mounted) setState(() => _trabajando = false);
  }

  void _agregar(Map<String, dynamic> p) {
    if ((p['disponible'] as int? ?? 0) <= 0) return setState(() => _error = '${p['producto']} (${p['talla']}, ${p['color']}) no tiene stock en esta sucursal.');
    final existente = _lineas.where((l) => l.prenda['variante_id'] == p['variante_id']).firstOrNull;
    setState(() {
      _error = null;
      _comprobante = null;
      if (existente == null) {
        _lineas.add(_Linea(p));
      } else if (existente.cantidad < (p['disponible'] as int)) {
        existente.cantidad++;
      }
    });
  }

  Future<void> _cobrar() async {
    if (_lineas.isEmpty) return setState(() => _error = 'Agregue al menos una prenda.');
    final recibido = double.tryParse(_recibido.text.replaceAll(',', '.'));
    if (recibido == null || recibido < _total) return setState(() => _error = 'El efectivo recibido no cubre el total (Bs ${_total.toStringAsFixed(2)}).');
    setState(() { _trabajando = true; _error = null; });
    try {
      final venta = await _api.post('/caja/ventas', {'items': [for (final l in _lineas) {'variante_id': l.prenda['variante_id'], 'cantidad': l.cantidad}]});
      final cobro = await _api.post('/caja/ventas/${venta['id']}/cobrar', {'metodo': 'EFECTIVO', 'monto_recibido': recibido});
      final pedido = (cobro['pedido'] as Map?) ?? const {};
      if (mounted) {
        setState(() {
          _comprobante = 'Venta cobrada. Comprobante ${pedido['comprobante_numero'] ?? ''}. Cambio: Bs ${cobro['cambio'] ?? '0.00'}.';
          _lineas.clear();
          _resultados = [];
          _recibido.clear();
        });
      }
    } on ApiException catch (e) {
      if (mounted) setState(() => _error = _mensaje(e));
    }
    if (mounted) setState(() => _trabajando = false);
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: const Text('Caja')),
        body: ListView(padding: EdgeInsets.fromLTRB(16, 16, 16, MediaQuery.viewPaddingOf(context).bottom + 16), children: [
          Card(color: const Color(0xFFFBEFD9), child: const Padding(padding: EdgeInsets.all(12), child: Text(msgPlanSinOffline))),
          const SizedBox(height: 8),
          TextField(
            controller: _texto,
            onSubmitted: (_) => _buscar(),
            decoration: InputDecoration(labelText: 'Buscar prenda (nombre, SKU o código)', prefixIcon: const Icon(Icons.search), suffixIcon: IconButton(tooltip: 'Buscar', icon: const Icon(Icons.arrow_forward), onPressed: _trabajando ? null : _buscar)),
          ),
          if (_error != null) Padding(padding: const EdgeInsets.only(top: 8), child: Text(_error!, style: const TextStyle(color: Colors.red))),
          if (_comprobante != null) Padding(padding: const EdgeInsets.only(top: 8), child: Text(_comprobante!, style: const TextStyle(fontWeight: FontWeight.w600))),
          for (final p in _resultados)
            ListTile(
              dense: true,
              title: Text('${p['producto']} (${p['talla']}, ${p['color']})'),
              subtitle: Text('${p['sku']} · ${(p['disponible'] as int? ?? 0) == 0 ? 'Sin stock' : '${p['disponible']} disponibles'}'),
              trailing: Text('Bs ${p['precio_final']}'),
              onTap: () => _agregar(p),
            ),
          if (_lineas.isNotEmpty) ...[
            const Divider(),
            for (final l in _lineas)
              ListTile(
                dense: true,
                title: Text('${l.cantidad}× ${l.prenda['producto']} (${l.prenda['talla']}, ${l.prenda['color']})'),
                trailing: IconButton(tooltip: 'Quitar', icon: const Icon(Icons.delete_outline), onPressed: () => setState(() => _lineas.remove(l))),
                subtitle: Text('Bs ${l.subtotal.toStringAsFixed(2)}'),
              ),
            Text('Total: Bs ${_total.toStringAsFixed(2)}', style: Theme.of(context).textTheme.titleMedium),
            TextField(controller: _recibido, keyboardType: const TextInputType.numberWithOptions(decimal: true), decoration: const InputDecoration(labelText: 'Efectivo recibido (Bs)')),
            const SizedBox(height: 8),
            FilledButton.icon(onPressed: _trabajando ? null : _cobrar, icon: const Icon(Icons.point_of_sale), label: Text(_trabajando ? 'Procesando…' : 'Cobrar en efectivo')),
          ],
        ]),
      );
}
