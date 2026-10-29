import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../data/modelos.dart';
import 'offline_controller.dart';
import 'registrar_offline_screen.dart';

String fechaCorta(String? iso) {
  if (iso == null) return '—';
  final f = DateTime.tryParse(iso)?.toLocal();
  if (f == null) return iso;
  String d(int n) => n.toString().padLeft(2, '0');
  return '${d(f.day)}/${d(f.month)}/${f.year} ${d(f.hour)}:${d(f.minute)}';
}

/// Modo sin conexión: catálogo descargado (CU-37), registro de ventas de contado o reservas (RF19) y la cola de operaciones con su estado (CU-38, CU-39).
class ModoOfflineScreen extends StatelessWidget {
  const ModoOfflineScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final c = context.watch<OfflineController>();
    return DefaultTabController(
      length: 3,
      child: Scaffold(
        appBar: AppBar(
          title: const Text('Modo sin conexión'),
          bottom: TabBar(tabs: [
            const Tab(text: 'Catálogo'),
            const Tab(text: 'Registrar'),
            Tab(text: c.pendientes.isEmpty ? 'Operaciones' : 'Operaciones (${c.pendientes.length})'),
          ]),
        ),
        body: Column(children: [
          if (!c.enLinea)
            Container(
              width: double.infinity,
              color: const Color(0xFFFBEFD9),
              padding: const EdgeInsets.all(10),
              child: const Text('Sin conexión con el servidor. Lo que registre se guarda en este dispositivo y se envía solo al volver Internet.'),
            ),
          const Expanded(child: TabBarView(children: [_CatalogoTab(), RegistrarOfflineTab(), _OperacionesTab()])),
        ]),
      ),
    );
  }
}

class _CatalogoTab extends StatefulWidget {
  const _CatalogoTab();

  @override
  State<_CatalogoTab> createState() => _CatalogoTabState();
}

class _CatalogoTabState extends State<_CatalogoTab> {
  final _texto = TextEditingController();
  List<PrendaLocal> _resultados = [];

  @override
  void initState() {
    super.initState();
    _buscar();
  }

  Future<void> _buscar() async {
    final r = await context.read<OfflineController>().repo.buscar(_texto.text);
    if (mounted) setState(() => _resultados = r);
  }

  Future<void> _descargar() async {
    final c = context.read<OfflineController>();
    await c.descargarCatalogo();
    await _buscar();
    if (mounted && c.error == null) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Catálogo descargado: ya puede consultarlo sin conexión.')));
    }
  }

  @override
  Widget build(BuildContext context) {
    final c = context.watch<OfflineController>();
    final antiguo = c.catalogoGeneradoEn != null &&
        (!c.enLinea || DateTime.now().difference(DateTime.tryParse(c.catalogoGeneradoEn!) ?? DateTime.now()).inHours > 24);
    return ListView(padding: const EdgeInsets.all(16), children: [
      Card(
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('Catálogo en este dispositivo', style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 4),
            Text(c.catalogoGeneradoEn == null
                ? 'Todavía no descargó el catálogo. Descárguelo con conexión para consultar y vender sin Internet.'
                : 'Descargado el ${fechaCorta(c.catalogoGeneradoEn)}.'),
            if (antiguo) // RN16
              const Padding(padding: EdgeInsets.only(top: 6), child: Text('Esta información puede estar desactualizada.', style: TextStyle(color: Color(0xFF8A5A00)))),
            if (c.error != null) Padding(padding: const EdgeInsets.only(top: 6), child: Text(c.error!, style: const TextStyle(color: Colors.red))),
            const SizedBox(height: 10),
            FilledButton.icon(
              onPressed: c.descargando ? null : _descargar,
              icon: const Icon(Icons.download),
              label: Text(c.descargando ? 'Descargando…' : c.catalogoGeneradoEn == null ? 'Descargar catálogo' : 'Actualizar catálogo'),
            ),
          ]),
        ),
      ),
      if (c.hayCatalogo) ...[
        const SizedBox(height: 12),
        TextField(controller: _texto, onChanged: (_) => _buscar(), decoration: const InputDecoration(labelText: 'Buscar en el catálogo guardado', prefixIcon: Icon(Icons.search))),
        const SizedBox(height: 8),
        for (final r in _resultados)
          ListTile(
            title: Text(r.producto.nombre),
            subtitle: Text('${r.variante.talla} · ${r.variante.color} · ${r.variante.sku}\nStock: ${r.variante.stockEn(c.sesion?.sucursalId)}'),
            isThreeLine: true,
            trailing: Text('Bs ${r.variante.precioFinal}', style: const TextStyle(fontWeight: FontWeight.w600)),
          ),
        if (_resultados.isEmpty) const Padding(padding: EdgeInsets.all(16), child: Text('No hay prendas con ese texto.')),
      ],
    ]);
  }
}

class _OperacionesTab extends StatelessWidget {
  const _OperacionesTab();

  Color _color(String e) => switch (e) {
        Estado.confirmada => Colors.green.shade100,
        Estado.rechazada => Colors.red.shade100,
        Estado.enConflicto || Estado.enviada => Colors.orange.shade100,
        _ => Colors.blueGrey.shade100,
      };

  @override
  Widget build(BuildContext context) {
    final c = context.watch<OfflineController>();
    return ListView(padding: const EdgeInsets.all(16), children: [
      Text('Última sincronización: ${fechaCorta(c.ultimaSync)} · ${c.pendientes.length} pendiente(s) de enviar.'), // RN16
      const SizedBox(height: 8),
      Wrap(spacing: 8, children: [
        FilledButton.icon(
          onPressed: c.sincronizando || c.pendientes.isEmpty ? null : () => c.sincronizar(),
          icon: const Icon(Icons.sync),
          label: Text(c.sincronizando ? 'Sincronizando…' : 'Sincronizar ahora'),
        ),
        OutlinedButton(onPressed: c.limpiarTerminadas, child: const Text('Quitar confirmadas y rechazadas')),
      ]),
      if (c.error != null) Padding(padding: const EdgeInsets.only(top: 8), child: Text(c.error!, style: const TextStyle(color: Colors.red))),
      const SizedBox(height: 8),
      if (c.operaciones.isEmpty) const Padding(padding: EdgeInsets.all(24), child: Center(child: Text('No hay operaciones registradas en este dispositivo.'))),
      for (final o in c.operaciones)
        Card(
          child: Padding(
            padding: const EdgeInsets.all(12),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
                Chip(label: Text(Estado.textos[o.estado] ?? o.estado), backgroundColor: _color(o.estado)),
                Text(fechaCorta(o.creadoEn), style: Theme.of(context).textTheme.bodySmall),
              ]),
              Text(o.resumen),
              if (o.referencia != null) Text('${o.referencia}${o.comprobante != null ? ' · comprobante ${o.comprobante}' : ''}', style: const TextStyle(fontWeight: FontWeight.w600)),
              if (o.mensaje.isNotEmpty) Text(o.mensaje, style: Theme.of(context).textTheme.bodySmall),
              for (final f in o.faltantes) Text('• ${f['producto']} (${f['talla']}, ${f['color']}): pidió ${f['solicitadas']}, hay ${f['disponibles']}', style: Theme.of(context).textTheme.bodySmall),
              if (o.estado == Estado.registradaLocal && o.intentos > 0) Text('${o.intentos} intento(s) de envío', style: Theme.of(context).textTheme.bodySmall),
              Text(o.id, style: Theme.of(context).textTheme.labelSmall),
            ]),
          ),
        ),
    ]);
  }
}
