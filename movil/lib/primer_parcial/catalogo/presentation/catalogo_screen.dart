import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../../core/network/api_client.dart';
import '../../../features/auth/data/auth_repository.dart';
import '../../../features/offline/presentation/modo_offline_screen.dart' show fechaCorta;
import '../../../features/offline/presentation/offline_controller.dart';
import '../../ia/vestidor/data/vestidor_repository.dart';
import '../../ia/vestidor/presentation/vestidor_screen.dart';
import '../data/catalogo_repository.dart';

/// Catálogo del cliente (CU-03, CU-04): busca en línea y, si no hay conexión, usa el catálogo descargado (CU-37) avisando de cuándo es (RN16).
class CatalogoScreen extends StatefulWidget {
  const CatalogoScreen({super.key});

  @override
  State<CatalogoScreen> createState() => _CatalogoScreenState();
}

class _CatalogoScreenState extends State<CatalogoScreen> {
  late final CatalogoRepository _repo = CatalogoRepository(context.read<AuthRepository>().api);
  final _texto = TextEditingController();
  List<Map<String, dynamic>> _items = [];
  List<Map<String, dynamic>> _sucursales = [];
  bool _cargando = true;
  bool _local = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _buscar();
  }

  Future<void> _buscar() async {
    setState(() {
      _cargando = true;
      _error = null;
    });
    try {
      final items = await _repo.buscar(_texto.text);
      if (_sucursales.isEmpty) _sucursales = await _repo.sucursales();
      if (mounted) setState(() { _items = items; _local = false; });
    } on ApiException catch (e) {
      if (!e.sinConexion) {
        if (mounted) setState(() => _error = e.mensaje);
      } else if (mounted) {
        // sin conexión: lo descargado en el dispositivo (CU-37)
        final prendas = await context.read<OfflineController>().repo.buscar(_texto.text);
        if (mounted) {
          setState(() {
            _local = true;
            _items = [
              for (final p in prendas)
                {'id': p.producto.id, 'nombre': p.producto.nombre, 'categoria': p.producto.categoria, 'precio_final': p.variante.precioFinal, 'tallas': [p.variante.talla], 'local': true},
            ];
          });
        }
      }
    }
    if (mounted) setState(() => _cargando = false);
  }

  Future<void> _detalle(Map<String, dynamic> prenda) async {
    if (prenda['local'] == true) return;
    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      builder: (_) => _DetallePrenda(repo: _repo, prenda: prenda, sucursales: _sucursales),
    );
  }

  @override
  Widget build(BuildContext context) {
    final off = context.watch<OfflineController>();
    return Scaffold(
      appBar: AppBar(title: const Text('Catálogo')),
      body: Column(children: [
        Padding(
          padding: const EdgeInsets.all(12),
          child: TextField(controller: _texto, onSubmitted: (_) => _buscar(), decoration: InputDecoration(labelText: 'Buscar prendas', prefixIcon: const Icon(Icons.search), suffixIcon: IconButton(icon: const Icon(Icons.arrow_forward), onPressed: _buscar))),
        ),
        if (_local)
          Container(
            width: double.infinity,
            color: const Color(0xFFFBEFD9),
            padding: const EdgeInsets.all(10),
            child: Text(off.hayCatalogo
                ? 'Sin conexión: se muestra el catálogo descargado el ${fechaCorta(off.catalogoGeneradoEn)}. Puede estar desactualizado.'
                : 'Sin conexión y sin catálogo descargado. Descárguelo en «Modo sin conexión» cuando tenga Internet.'),
          ),
        if (_error != null) Padding(padding: const EdgeInsets.all(12), child: Text(_error!, style: const TextStyle(color: Colors.red))),
        Expanded(
          child: _cargando
              ? const Center(child: CircularProgressIndicator())
              : _items.isEmpty
                  ? const Center(child: Text('No se encontraron prendas.'))
                  : ListView.separated(
                      itemCount: _items.length,
                      separatorBuilder: (_, __) => const Divider(height: 1),
                      itemBuilder: (_, i) {
                        final p = _items[i];
                        final promo = p['promocion'] as String?;
                        return ListTile(
                          onTap: () => _detalle(p),
                          title: Text('${p['nombre']}'),
                          subtitle: Text('${p['categoria']} · tallas ${(p['tallas'] as List).join(', ')}${promo != null ? '\n$promo' : ''}'),
                          isThreeLine: promo != null,
                          trailing: Text('Bs ${p['precio_final']}', style: const TextStyle(fontWeight: FontWeight.w600)),
                        );
                      },
                    ),
        ),
      ]),
    );
  }
}

class _DetallePrenda extends StatefulWidget {
  const _DetallePrenda({required this.repo, required this.prenda, required this.sucursales});
  final CatalogoRepository repo;
  final Map<String, dynamic> prenda;
  final List<Map<String, dynamic>> sucursales;

  @override
  State<_DetallePrenda> createState() => _DetallePrendaState();
}

class _DetallePrendaState extends State<_DetallePrenda> {
  late final VestidorRepository _vestidor = VestidorRepository(context.read<AuthRepository>().api);
  int? _sucursalId;
  Map<String, dynamic>? _opciones;
  String? _mensaje;

  @override
  void initState() {
    super.initState();
    _cargar();
    _vestidor.precargar(widget.prenda['id'] as int);  // el PNG del vestidor queda listo mientras el cliente mira la ficha
  }

  void _probar() {
    Navigator.of(context).push(MaterialPageRoute<void>(
      builder: (_) => VestidorScreen(repo: _vestidor, productoId: widget.prenda['id'] as int, nombre: '${widget.prenda['nombre']}'),
    ));
  }

  Future<void> _cargar() async {
    try {
      final o = await widget.repo.opciones(widget.prenda['id'] as int, _sucursalId);
      if (mounted) setState(() => _opciones = o);
    } on ApiException catch (e) {
      if (mounted) setState(() => _mensaje = e.mensaje);
    }
  }

  Future<void> _agregar(Map<String, dynamic> v) async {
    try {
      await widget.repo.agregarAlCarrito(v['variante_id'] as int, 1, _sucursalId);
      if (mounted) setState(() => _mensaje = '${widget.prenda['nombre']} (${v['talla']}, ${v['color']}) agregada al carrito.');
    } on ApiException catch (e) {
      if (mounted) setState(() => _mensaje = e.mensaje);
    }
  }

  @override
  Widget build(BuildContext context) {
    final variantes = ((_opciones?['variantes'] as List?) ?? const []).cast<Map<String, dynamic>>();
    return Padding(
      padding: EdgeInsets.fromLTRB(16, 16, 16, MediaQuery.of(context).viewInsets.bottom + 16),
      child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text('${widget.prenda['nombre']}', style: Theme.of(context).textTheme.titleLarge),
        const SizedBox(height: 4),
        Align(alignment: Alignment.centerLeft, child: TextButton.icon(onPressed: _probar, icon: const Icon(Icons.checkroom), label: const Text('Probar en el vestidor'))),
        const SizedBox(height: 4),
        DropdownButtonFormField<int?>(
          initialValue: _sucursalId,
          decoration: const InputDecoration(labelText: 'Disponibilidad en'),
          items: [const DropdownMenuItem<int?>(value: null, child: Text('Todas las sucursales')), for (final s in widget.sucursales) DropdownMenuItem<int?>(value: s['id'] as int, child: Text('${s['nombre']}'))],
          onChanged: (v) {
            setState(() {
              _sucursalId = v;
              _opciones = null;
            });
            _cargar();
          },
        ),
        const SizedBox(height: 8),
        if (_opciones == null) const Center(child: CircularProgressIndicator()),
        Flexible(
          child: ListView(shrinkWrap: true, children: [
            for (final v in variantes)
              ListTile(
                dense: true,
                title: Text('${v['talla']} · ${v['color']}'),
                subtitle: Text(v['disponible'] == true ? '${v['cantidad']} disponible(s)' : 'Agotada'),
                trailing: Row(mainAxisSize: MainAxisSize.min, children: [
                  Text('Bs ${v['precio_final']}'),
                  IconButton(icon: const Icon(Icons.add_shopping_cart), onPressed: v['disponible'] == true ? () => _agregar(v) : null),
                ]),
              ),
          ]),
        ),
        if (_mensaje != null) Padding(padding: const EdgeInsets.only(top: 8), child: Text(_mensaje!)),
      ]),
    );
  }
}
