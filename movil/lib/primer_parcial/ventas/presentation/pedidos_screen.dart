import 'package:flutter/material.dart';
import '../../../core/ui/refrescar.dart';
import '../../../features/offline/presentation/lista_vacia.dart';
import '../../../features/offline/data/estado_legible.dart';
import 'package:provider/provider.dart';

import '../../../core/network/api_client.dart';
import '../../../features/auth/data/auth_repository.dart';
import '../../../features/offline/presentation/modo_offline_screen.dart'
    show fechaCorta;
import '../../../features/offline/presentation/offline_controller.dart';
import '../../../features/offline/presentation/operacion_acciones.dart';
import '../data/comprobante_movil.dart';
import '../data/ventas_repository.dart';
import '../../reservas/data/hoja_de_pago.dart';
import '../../reservas/data/pago_movil.dart';
import '../../reservas/data/reservas_repository.dart';
import '../../../features/offline/presentation/operaciones_con_problema.dart';
import '../../catalogo/presentation/catalogo_screen.dart';
import 'boton_comprobante.dart';

String _estadoCompra(Object? e) => const {'PENDIENTE_PAGO': 'Por pagar', 'PENDIENTE_CONFIRMACION': 'Pago por confirmar', 'PAGADO': 'Pagado'}['$e'] ?? '$e';

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

  int? _refrescoVisto;

  Future<void> _cargar() async {
    try {
      final vistas = await _repo.compras();
      final c = await _conPendientes(vistas);
      if (!mounted) return; // la pantalla se cerró mientras llegaban las compras
      final sesion = context.read<OfflineController>().sesion;
      if (sesion?.empresaId != null) {
        await context
            .read<OfflineController>()
            .repo
            .guardarComprasVistas(vistas, sesion!.usuarioId, sesion.empresaId!);
      }
      if (mounted) {
        setState(() {
          _compras = c;
          _error = null;
        });
      }
    } on ApiException catch (e) {
      if (!mounted) return;
      final offline = context.read<OfflineController>();
      final sesion = offline.sesion;
      final vistas = sesion?.empresaId == null
          ? <Map<String, dynamic>>[]
          : await offline.repo
              .comprasVistas(sesion!.usuarioId, sesion.empresaId!);
      final locales = await _conPendientes(vistas);
      if (mounted) {
        setState(() => _error = e.sinConexion
            ? (locales.isNotEmpty
                ? null
                : 'Sin conexión: todavía no se descargó el historial de compras.')
            : e.mensaje);
        if (locales.isNotEmpty) _compras = locales;
      }
    }
  }

  Future<List<Map<String, dynamic>>> _conPendientes(
      List<Map<String, dynamic>> compras) async {
    final offline = context.read<OfflineController>();
    final sesion = offline.sesion;
    if (sesion == null || sesion.empresaId == null) return compras;
    final operaciones =
        await offline.repo.operaciones(sesion.usuarioId, sesion.empresaId!);
    final pendientes =
        operaciones.where((o) => o.tipo == 'COMPRA' && o.pendiente);
    if (pendientes.isEmpty) return compras;
    final prendas = await offline.repo.buscar('', limite: 1000);
    final sucursales = await offline.repo.sucursales();
    final resultado = [...compras];
    for (final operacion in pendientes) {
      final items = (operacion.payload['items'] as List? ?? const [])
          .cast<Map<String, dynamic>>();
      final total = items.fold<double>(0, (suma, item) {
        final variante = prendas
            .where((p) => p.variante.id == item['variante_id'])
            .firstOrNull
            ?.variante;
        final precio = double.tryParse(variante?.precioFinal ?? '') ?? 0;
        return suma + precio * (item['cantidad'] as int? ?? 1);
      });
      resultado.add({
        'id': operacion.id,
        'codigo': operacion.referencia ?? 'En este dispositivo',
        'estado': operacion.estado,
        'leyenda': estadoLegible(operacion),
        'fecha': operacion.creadoEn,
        'sucursal': sucursales
                .where((s) => s.id == operacion.sucursalId)
                .firstOrNull
                ?.nombre ??
            'Sucursal',
        'total': total.toStringAsFixed(2),
        'total_unidades': items.fold<int>(
            0, (suma, item) => suma + (item['cantidad'] as int? ?? 1)),
        'comprobante_numero': null,
        'pendiente_local': true,
        'resumen': operacion.resumen,
      });
    }
    return resultado;
  }

  Widget? _botonDeshacer(Map<String, dynamic> c) {
    final operacion = context.read<OfflineController>().operaciones.where((o) => o.id == c['id']).firstOrNull;
    if (operacion == null || !context.read<OfflineController>().puedeDeshacer(operacion)) return null;
    return TextButton(
        style: TextButton.styleFrom(foregroundColor: Colors.red, minimumSize: const Size(48, 48)),
        onPressed: () => deshacerConConfirmacion(context, operacion, alDeshacer: _cargar),
        child: const Text('Deshacer'));
  }

  Future<void> _ver(Map<String, dynamic> c) async {
    if (c['pendiente_local'] == true) {
      final operacion = context.read<OfflineController>().operaciones.where((o) => o.id == c['id']).firstOrNull;
      await showDialog<void>(
          context: context,
          builder: (ctx) => AlertDialog(
                  title: const Text('Compra pendiente de sincronizar'),
                  content: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text('${c['resumen']}\nEstado: ${c['estado']}\nSe enviará al recuperar la conexión.'),
                    if (operacion != null) AccionesOperacion(operacion, alDeshacer: () { Navigator.pop(ctx); _cargar(); }),
                  ]),
                  actions: [
                    TextButton(
                        onPressed: () => Navigator.pop(ctx),
                        child: const Text('Cerrar'))
                  ]));
      return;
    }
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
    final refresco = context.select<OfflineController, int>((c) => c.refresco);
    if (_refrescoVisto != null && _refrescoVisto != refresco) {
      WidgetsBinding.instance.addPostFrameCallback((_) { if (mounted) _cargar(); }); // tras sincronizar o al volver la red, la lista se actualiza sola
    }
    _refrescoVisto = refresco;
    return Scaffold(
      appBar:
          widget.integrado ? null : AppBar(title: const Text('Mis compras')),
      body: RefreshIndicator(
        onRefresh: () => refrescarConAviso(context, _cargar),
        child: ListView(
            padding: EdgeInsets.fromLTRB(
                16, 16, 16, MediaQuery.viewPaddingOf(context).bottom + 16),
            children: [
              OperacionesConProblema(tipos: const ['COMPRA'], titulo: 'Compras que no se pudieron realizar', alElegirOtra: (prenda) => Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => CatalogoScreen(consultaInicial: prenda)))),
              if (_error != null)
                Text(_error!, style: const TextStyle(color: Colors.red)),
              if (_compras == null && _error == null)
                const Center(child: CircularProgressIndicator()),
              if (_compras != null && _compras!.isEmpty)
                const ListaVacia(icono: Icons.receipt_long_outlined, texto: 'Todavía no tiene compras. Cuando compre, las verá aquí.'),
              for (final c in _compras ?? const <Map<String, dynamic>>[])
                Card(
                  child: ListTile(
                    onTap: () => _ver(c),
                    title: Text('${c['codigo']} · Bs ${c['total']}'),
                    trailing: c['pendiente_local'] == true
                        ? _botonDeshacer(c)
                        : c['comprobante_numero'] == null
                        ? null
                        : BotonComprobante(
                            comprobante: _comprobante,
                            pedidoId: c['id'] as int,
                            numero: '${c['comprobante_numero']}'),
                    subtitle: Text(
                        '${c['pendiente_local'] == true ? c['leyenda'] : _estadoCompra(c['estado'])} · ${c['sucursal']} · ${fechaCorta(c['fecha'] as String?)}${c['comprobante_numero'] != null ? '\n${c['comprobante_numero']}' : ''}'),
                    isThreeLine: c['comprobante_numero'] != null,
                  ),
                ),
            ]),
      ),
    );
  }
}
