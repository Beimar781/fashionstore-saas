import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../../core/network/api_client.dart';
import '../../../features/auth/data/auth_repository.dart';
import '../../../features/offline/data/carrito_sin_conexion.dart';
import '../../../features/offline/presentation/modo_offline_screen.dart' show fechaCorta;
import '../../../features/offline/presentation/offline_controller.dart';
import '../../ventas/data/comprobante_movil.dart';
import '../../ventas/data/ventas_repository.dart';
import '../../ventas/presentation/boton_comprobante.dart';
import '../data/hoja_de_pago.dart';
import '../data/medio_de_pago.dart';
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
  bool _cargando = true;
  bool _desdeCopia = false; // sin conexión: lo que se ve es la copia del servidor más los cambios hechos en el teléfono
  String? _compraPendiente;
  int? _refrescoVisto;

  CarritoSinConexion? get _sin {
    final offline = context.read<OfflineController>();
    final s = offline.sesion;
    return s?.empresaId == null ? null : CarritoSinConexion(offline.repo, empresaId: s!.empresaId!, usuarioId: s.usuarioId);
  }

  @override
  void initState() {
    super.initState();
    _cargar();
  }

  /// Con conexión: primero se aplican al servidor los cambios hechos sin conexión y luego se muestra su carrito.
  /// Sin conexión: la copia del servidor + los cambios del teléfono (nunca un spinner infinito ni un carrito «que necesita Internet»).
  Future<void> _cargar() async {
    final sin = _sin;
    setState(() => _cargando = true);
    try {
      if (sin != null && context.read<OfflineController>().enLinea) {
        try {
          final rechazados = await sin.reenviar(_repo);
          if (rechazados > 0 && mounted) setState(() => _error = 'No se pudieron aplicar $rechazados cambio(s) del carrito hechos sin conexión (la prenda ya no está o no hay stock).');
        } on ApiException catch (e) {
          if (!e.sinConexion) rethrow;
        }
      }
      final c = await _repo.carrito();
      final vista = sin == null ? c : await sin.vista(c);
      if (mounted) {
        setState(() {
          _carrito = vista;
          _desdeCopia = ApiClient.lecturaLocalDesde != null || !context.read<OfflineController>().enLinea;
          if (_error?.startsWith('No se pudieron') != true) _error = null;
        });
      }
    } on ApiException catch (e) {
      final vista = e.sinConexion ? await _sin?.vista(null) : null;
      if (mounted) {
        setState(() {
          _carrito = vista;
          _desdeCopia = vista != null;
          _error = e.sinConexion ? (vista == null ? 'Sin conexión: su carrito no está guardado en este teléfono. Ábralo con conexión una vez.' : null) : e.mensaje;
        });
      }
    }
    if (mounted) setState(() => _cargando = false);
  }

  /// Con conexión la acción va al servidor; sin conexión (o si el servidor no responde) se guarda en el teléfono y se aplicará al volver la red.
  Future<void> _accion(Future<Map<String, dynamic>> Function() servidor, Future<void> Function(CarritoSinConexion) local) async {
    final sin = _sin;
    try {
      if (sin != null && !context.read<OfflineController>().enLinea) throw ApiException('Sin conexión con el servidor.', sinConexion: true);
      final c = await servidor();
      if (mounted) setState(() { _carrito = c; _error = null; });
    } on ApiException catch (e) {
      if (e.sinConexion && sin != null) {
        try {
          await local(sin);
          final vista = await sin.vista(_carrito);
          if (mounted) setState(() { _carrito = vista; _desdeCopia = true; _error = null; });
        } on ApiException catch (x) {
          if (mounted) setState(() => _error = x.mensaje);
        }
      } else if (mounted) {
        setState(() => _error = e.mensaje);
      }
    }
  }

  /// Sin conexión: la compra se guarda con su UUID y, si eligió una tarjeta guardada, solo viaja su identificador y el total que autorizó (D4).
  Future<void> _pagarSinConexion() async {
    final offline = context.read<OfflineController>();
    final sin = _sin;
    final carrito = _carrito;
    if (sin == null || carrito == null) return;
    final eleccion = await Navigator.push<EleccionDeCompra>(context, MaterialPageRoute(builder: (_) => EntregaScreen(repo: _repo, sucursal: carrito['sucursal'] as String?, total: '${carrito['total']}')));
    if (eleccion == null || !mounted) return;
    final tarjeta = [for (final j in await offline.repo.tarjetasLocales()) TarjetaGuardada.desdeJson(j)].where((t) => t.id == eleccion.medio.tarjetaGuardadaId).firstOrNull;
    final items = (carrito['items'] as List).cast<Map<String, dynamic>>();
    final detalle = items.map((i) => '${i['cantidad']}× ${i['producto']} (${i['talla']}, ${i['color']})').join(', ');
    await offline.registrar(
      tipo: 'COMPRA',
      payload: {
        'sucursal_id': carrito['sucursal_id'],
        ...eleccion.datos.aCuerpo(),
        'items': [for (final i in items) {'variante_id': i['variante_id'], 'cantidad': i['cantidad']}],
        if (tarjeta != null) 'tarjeta_guardada_id': tarjeta.id,
        if (tarjeta != null) 'total_autorizado': double.parse('${carrito['total']}').toStringAsFixed(2),
      },
      sucursalId: carrito['sucursal_id'] as int,
      resumen: 'Compra: $detalle${tarjeta == null ? '' : ' · se cobrará a ${tarjeta.marca} terminada en ${tarjeta.ultimos4}'}',
    );
    await sin.alComprar();
    if (!mounted) return;
    setState(() {
      _carrito = null;
      _compraPendiente = tarjeta == null
          ? 'Compra guardada en este teléfono. Al recuperar la conexión verificamos que las prendas sigan disponibles y le avisamos para que la pague desde Mis compras.'
          : 'Compra guardada en este teléfono. Al recuperar la conexión se cobrará a su ${tarjeta.marca} terminada en ${tarjeta.ultimos4}; si no se puede cobrar, quedará por pagar en Mis compras.';
    });
  }

  Future<void> _pagar() async {
    if (!context.read<OfflineController>().enLinea) return _pagarSinConexion();
    final eleccion = await Navigator.push<EleccionDeCompra>(context, MaterialPageRoute(builder: (_) => EntregaScreen(repo: _repo, sucursal: _carrito?['sucursal'] as String?)));
    if (eleccion == null || !mounted) return; // el cliente volvió sin continuar
    setState(() { _trabajando = true; _error = null; _resultado = null; });
    await _mostrar(await _pago.pagar(datos: eleccion.datos, medio: eleccion.medio, pedirTarjeta: _pedirTarjeta));
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
    final off = context.watch<OfflineController>();
    if (_refrescoVisto != null && _refrescoVisto != off.refresco) {
      WidgetsBinding.instance.addPostFrameCallback((_) { if (mounted) _cargar(); }); // al volver la red el carrito se actualiza solo
    }
    _refrescoVisto = off.refresco;
    final items = ((_carrito?['items'] as List?) ?? const []).cast<Map<String, dynamic>>();
    return Scaffold(
      appBar: AppBar(title: const Text('Mi carrito')),
      body: RefreshIndicator(
        onRefresh: _cargar,
        child: ListView(padding: const EdgeInsets.all(16), children: [
          if (_error != null) Text(_error!, style: const TextStyle(color: Colors.red)),
          if (_compraPendiente != null) Card(color: const Color(0xFFFBEFD9), child: Padding(padding: const EdgeInsets.all(12), child: Text(_compraPendiente!))),
          if (_desdeCopia && _carrito != null)
            Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: Text('Sin conexión · datos al ${fechaCorta(ApiClient.lecturaLocalDesde ?? off.ultimaSync)}; los cambios de su carrito se guardan en este teléfono y se aplicarán al volver Internet.', style: const TextStyle(fontSize: 12, color: Color(0xFF8A5A00)))),
          if (_resultado != null) _tarjetaResultado(_resultado!),
          if (_cargando && _carrito == null && _error == null) const Center(child: CircularProgressIndicator()),
          if (!_cargando && _carrito != null && items.isEmpty) const Padding(padding: EdgeInsets.all(24), child: Center(child: Text('Su carrito está vacío.'))),
          for (final a in ((_carrito?['avisos'] as List?) ?? const [])) Text('$a', style: const TextStyle(color: Color(0xFF8A5A00))),
          for (final it in items)
            Card(
              child: ListTile(
                title: Text('${it['producto']}'),
                subtitle: Text('${it['talla']} · ${it['color']} · Bs ${it['precio_final']} c/u · ${it['disponible']} disponibles'),
                trailing: Row(mainAxisSize: MainAxisSize.min, children: [
                  IconButton(icon: const Icon(Icons.remove_circle_outline), onPressed: (it['cantidad'] as int) > 1 ? () => _accion(() => _repo.cambiarCantidad(it['id'] as int, (it['cantidad'] as int) - 1), (s) => s.cambiarCantidad(it, (it['cantidad'] as int) - 1)) : null),
                  Text('${it['cantidad']}'),
                  IconButton(icon: const Icon(Icons.add_circle_outline), onPressed: () => _accion(() => _repo.cambiarCantidad(it['id'] as int, (it['cantidad'] as int) + 1), (s) => s.cambiarCantidad(it, (it['cantidad'] as int) + 1))),
                  IconButton(icon: const Icon(Icons.delete_outline), onPressed: () => _accion(() => _repo.quitar(it['id'] as int), (s) => s.quitar(it))),
                ]),
              ),
            ),
          if (items.isNotEmpty) ...[
            const Divider(),
            Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [const Text('Total', style: TextStyle(fontWeight: FontWeight.bold)), Text('Bs ${_carrito!['total']}', style: const TextStyle(fontWeight: FontWeight.bold))]),
            Text('Retiro en ${_carrito!['sucursal'] ?? 'la sucursal elegida'} · IVA incluido Bs ${_carrito!['iva_incluido']}', style: Theme.of(context).textTheme.bodySmall),
            const SizedBox(height: 12),
            FilledButton.icon(onPressed: _trabajando || _carrito!['puede_pagar'] != true ? null : _pagar, icon: const Icon(Icons.credit_card), label: Text(_trabajando ? 'Procesando…' : off.enLinea ? 'Pagar con tarjeta' : 'Guardar compra para sincronizar')),
          ],
        ]),
      ),
    );
  }
}
