import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../data/comprobante_provisional.dart';
import '../data/modelos.dart';
import 'comprobante_provisional_accion.dart';
import 'modo_offline_screen.dart' show fechaCorta;
import 'offline_controller.dart';
import 'operacion_acciones.dart';
import 'operaciones_con_problema.dart';
import 'registrar_offline_screen.dart';
import 'resumen_turno_screen.dart';

/// Caja del Cajero y del Encargado en el teléfono (CU-29 con y sin conexión): la misma pantalla para vender, con el contador de ventas por sincronizar,
/// el estado de cada venta del turno y «Resumen de mi turno». Sin red la venta se guarda con su UUID y el comprobante provisional LOC-…;
/// con red se envía enseguida y recibe su comprobante CMP-… oficial.
class CajaScreen extends StatelessWidget {
  const CajaScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final c = context.watch<OfflineController>();
    final pendientes = ventasPorSincronizar(c.operaciones).length;
    return DefaultTabController(
      length: 2,
      child: Scaffold(
        appBar: AppBar(
          title: const Text('Caja'),
          actions: [
            IconButton(
                tooltip: 'Resumen de mi turno',
                icon: const Icon(Icons.receipt_long_outlined),
                onPressed: () => Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => const ResumenTurnoScreen()))),
          ],
          bottom: TabBar(tabs: [
            const Tab(text: 'Vender'),
            Tab(text: pendientes == 0 ? 'Mi turno' : 'Mi turno ($pendientes por sincronizar)'),
          ]),
        ),
        body: Column(children: [
          if (!c.enLinea)
            Container(
              width: double.infinity,
              color: const Color(0xFFFBEFD9),
              padding: const EdgeInsets.all(10),
              child: Text(c.hayCatalogo
                  ? 'Sin conexión: la venta se guarda en este dispositivo con un comprobante provisional y se envía sola al volver la red.'
                  : 'Sin conexión y sin copia del catálogo en este dispositivo: se descarga sola cuando hay conexión.'),
            ),
          const Expanded(child: TabBarView(children: [RegistrarOfflineTab(), MiTurnoTab()])),
        ]),
      ),
    );
  }
}

/// Ventas de contado del turno que todavía no llegaron al servidor.
List<OperacionLocal> ventasPorSincronizar(List<OperacionLocal> operaciones) => operaciones.where((o) => o.tipo == 'VENTA_CONTADO' && o.pendiente).toList();

/// Pestaña «Mi turno»: contador de ventas por sincronizar, estado de cada venta, ventas con problema y el resumen del turno.
class MiTurnoTab extends StatelessWidget {
  const MiTurnoTab({super.key});

  Color _color(String e) => switch (e) {
        Estado.confirmada => Colors.green.shade100,
        Estado.rechazada => Colors.red.shade100,
        Estado.enConflicto || Estado.enviada => Colors.orange.shade100,
        _ => Colors.blueGrey.shade100,
      };

  @override
  Widget build(BuildContext context) {
    final c = context.watch<OfflineController>();
    final ventas = c.operaciones.where((o) => o.tipo == 'VENTA_CONTADO').toList();
    final pendientes = ventasPorSincronizar(c.operaciones).length;
    return ListView(padding: EdgeInsets.fromLTRB(16, 16, 16, MediaQuery.viewPaddingOf(context).bottom + 16), children: [
      Card(
        child: ListTile(
          leading: Icon(pendientes == 0 ? Icons.cloud_done_outlined : Icons.cloud_upload_outlined),
          title: Text(pendientes == 0 ? 'Todas las ventas están sincronizadas' : '$pendientes venta(s) por sincronizar'),
          subtitle: Text('Última sincronización: ${fechaCorta(c.ultimaSync)}'),
          trailing: pendientes == 0
              ? null
              : TextButton(onPressed: c.sincronizando || !c.enLinea ? null : () => c.sincronizar(), child: Text(c.sincronizando ? 'Enviando…' : 'Sincronizar')),
        ),
      ),
      const OperacionesConProblema(tipos: ['VENTA_CONTADO'], titulo: 'Ventas con problema'),
      if (ventas.isEmpty)
        const Padding(padding: EdgeInsets.all(24), child: Center(child: Text('Todavía no registró ventas en este turno.'))),
      for (final o in ventas)
        Card(
          child: Column(children: [
            ListTile(
              title: Text(o.resumen, maxLines: 2, overflow: TextOverflow.ellipsis),
              subtitle: Text('${fechaCorta(o.creadoEn)} · ${o.comprobante ?? ComprobanteProvisional.numero(o.sucursalId, o.id)}'),
              trailing: Chip(label: Text(Estado.textos[o.estado] ?? o.estado), backgroundColor: _color(o.estado)),
              onTap: () => verComprobanteProvisional(context, o),
            ),
            Align(alignment: Alignment.centerLeft, child: Padding(padding: const EdgeInsets.only(left: 8, bottom: 4), child: AccionesOperacion(o))),
          ]),
        ),
      OutlinedButton.icon(
          onPressed: () => Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => const ResumenTurnoScreen())),
          icon: const Icon(Icons.receipt_long_outlined),
          label: const Text('Resumen de mi turno')),
    ]);
  }
}
