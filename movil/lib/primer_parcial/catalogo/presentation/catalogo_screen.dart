import 'dart:async';

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:sqflite/sqflite.dart';

import '../../../core/db/local_database.dart';
import '../../../core/network/api_client.dart';
import '../../../core/network/imagen_prenda.dart';
import '../../../features/auth/data/auth_repository.dart';
import '../../../features/auth/presentation/auth_controller.dart';
import '../../../features/offline/presentation/modo_offline_screen.dart'
    show fechaCorta;
import '../../../features/offline/data/carrito_sin_conexion.dart';
import '../../../features/offline/presentation/offline_controller.dart';
import '../../ia/vestidor/data/vestidor_repository.dart';
import '../../ia/vestidor/presentation/vestidor_screen.dart';
import '../../reservas/data/reserva_borrador.dart';
import '../data/catalogo_repository.dart';

/// Catálogo del cliente (CU-03, CU-04): busca en línea y, si no hay conexión, usa el catálogo descargado (CU-37) avisando de cuándo es (RN16).
class CatalogoScreen extends StatefulWidget {
  const CatalogoScreen(
      {super.key,
      this.integrado = false,
      this.soloPromociones = false,
      this.nombreEmpresa,
      this.consultaInicial});

  final bool integrado;
  final bool soloPromociones;
  final String? nombreEmpresa;

  /// Si viene, el catálogo abre buscando esa prenda y, con conexión, muestra su ficha (por ejemplo desde «Elegir otra talla o sucursal»).
  final String? consultaInicial;

  @override
  State<CatalogoScreen> createState() => _CatalogoScreenState();
}

class _CatalogoScreenState extends State<CatalogoScreen> {
  late final CatalogoRepository _repo =
      CatalogoRepository(context.read<AuthRepository>().api);
  final _texto = TextEditingController();
  List<Map<String, dynamic>> _items = [];
  List<Map<String, dynamic>> _sucursales = [];
  int? _sucursalId;
  int _pagina = 1;
  int _indicePromo = 0;
  int _total = 0;
  String? _categoria;
  final _lista = ScrollController();
  PageController? _carrusel;
  Timer? _temporizador;
  bool _mas = false;
  bool _cargando = true;
  bool _local = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _iniciar();
    _lista.addListener(_alFinal);
    _carrusel = PageController(viewportFraction: .9);
    _temporizador = Timer.periodic(const Duration(seconds: 5), (_) {
      if (mounted &&
          !_cargando &&
          _promociones.isNotEmpty &&
          (_carrusel?.hasClients ?? false)) {
        final siguiente =
            ((_carrusel!.page ?? 0).round() + 1) % _promociones.length;
        _carrusel!.animateToPage(siguiente,
            duration: const Duration(milliseconds: 350), curve: Curves.easeOut);
      }
    });
  }

  Future<void> _iniciar() async {
    try {
      final sesion = context.read<AuthController>().sesion;
      _sucursalId = sesion?.sucursalId;
      final empresa = sesion?.empresaId;
      if (empresa != null) {
        final db = await LocalDatabase.instance.database;
        final filas = await db.query('meta',
            where: 'clave = ?', whereArgs: ['cliente_sucursal_$empresa']);
        if (filas.isNotEmpty) {
          _sucursalId = int.tryParse(filas.first['valor'] as String);
        }
      }
    } catch (_) {}
    if (!mounted) return;
    if (widget.consultaInicial != null) _texto.text = widget.consultaInicial!;
    await _buscar();
    if (widget.consultaInicial != null && mounted && _items.isNotEmpty) await _detalle(_items.first);
  }

  List<Map<String, dynamic>> get _promociones =>
      _items.where((p) => p['promocion'] != null).toList();

  void _alFinal() {
    if (_lista.hasClients &&
        _lista.position.extentAfter < 300 &&
        !_cargando &&
        !_mas &&
        _items.length < _total) {
      _siguientePagina();
    }
  }

  Future<void> _buscar() async {
    setState(() {
      _cargando = true;
      _error = null;
      _pagina = 1;
      _items = [];
    });
    try {
      final respuesta = await _repo.buscarPagina(_texto.text,
          sucursalId: _sucursalId, pagina: 1, tamano: 20);
      final items = (respuesta['items'] as List).cast<Map<String, dynamic>>();
      if (_sucursales.isEmpty) _sucursales = await _repo.sucursales();
      if (mounted) {
        setState(() {
          _items = items;
          _total = respuesta['total'] as int? ?? items.length;
          _local = false;
          _categoria = null;
        });
      }
    } on ApiException catch (e) {
      if (!e.sinConexion) {
        if (mounted) setState(() => _error = e.mensaje);
      } else if (mounted) {
        // sin conexión: lo descargado en el dispositivo (CU-37)
        final prendas =
            await context.read<OfflineController>().repo.buscar(_texto.text);
        if (_sucursales.isEmpty) {
          try {
            _sucursales = [
              for (final s
                  in await context.read<OfflineController>().repo.sucursales())
                {'id': s.id, 'nombre': s.nombre, 'ciudad': s.ciudad}
            ];
          } catch (_) {}
        }
        if (mounted) {
          setState(() {
            _local = true;
            // una tarjeta por prenda (no por talla y color), para abrir su ficha con las variantes de la copia descargada
            final porProducto = <int, Map<String, dynamic>>{};
            for (final p in prendas) {
              final t = porProducto.putIfAbsent(p.producto.id, () => {
                'id': p.producto.id,
                'nombre': p.producto.nombre,
                'categoria': p.producto.categoria,
                'imagen': p.producto.imagen,
                'precio_final': p.variante.precioFinal,
                'tallas': <String>[],
                'local': true
              });
              if (!(t['tallas'] as List).contains(p.variante.talla)) (t['tallas'] as List).add(p.variante.talla);
            }
            _items = porProducto.values.toList();
            _total = _items.length;
          });
        }
      }
    }
    if (mounted) setState(() => _cargando = false);
  }

  Future<void> _siguientePagina() async {
    if (_local || _cargando || _mas) return;
    setState(() => _mas = true);
    try {
      final respuesta = await _repo.buscarPagina(_texto.text,
          sucursalId: _sucursalId, pagina: _pagina + 1, tamano: 20);
      if (mounted) {
        setState(() {
          _pagina++;
          _items.addAll(
              (respuesta['items'] as List).cast<Map<String, dynamic>>());
          _total = respuesta['total'] as int? ?? _total;
        });
      }
    } on ApiException {
      // Mantiene lo cargado; el gesto de refrescar permite reintentar.
    } finally {
      if (mounted) setState(() => _mas = false);
    }
  }

  Future<void> _elegirSucursal() async {
    if (_sucursales.isEmpty) {
      _sucursales = await _repo.sucursales();
    }
    if (!mounted) return;
    await showModalBottomSheet<void>(
        context: context,
        builder: (ctx) => SafeArea(
                child: ListView(shrinkWrap: true, children: [
              const ListTile(title: Text('Elegir sucursal')),
              for (final s in _sucursales)
                ListTile(
                    title: Text('${s['nombre']}'),
                    subtitle: Text('${s['ciudad'] ?? ''}'),
                    trailing:
                        _sucursalId == s['id'] ? const Icon(Icons.check) : null,
                    onTap: () {
                      Navigator.pop(ctx);
                      setState(() => _sucursalId = s['id'] as int);
                      _guardarSucursal();
                      _buscar();
                    }),
            ])));
  }

  Future<void> _guardarSucursal() async {
    final empresa = context.read<AuthController>().sesion?.empresaId;
    if (empresa == null || _sucursalId == null) return;
    final db = await LocalDatabase.instance.database;
    await db.insert(
        'meta', {'clave': 'cliente_sucursal_$empresa', 'valor': '$_sucursalId'},
        conflictAlgorithm: ConflictAlgorithm.replace);
  }

  Future<void> _detalle(Map<String, dynamic> prenda) async {
    await mostrarDetallePrenda(context, _repo, prenda, _sucursales);
  }

  @override
  void dispose() {
    _texto.dispose();
    _lista.dispose();
    _temporizador?.cancel();
    _carrusel?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final off = context.watch<OfflineController>();
    final categorias = _items
        .map((p) => '${p['categoria'] ?? ''}')
        .where((c) => c.isNotEmpty)
        .toSet()
        .toList()
      ..sort();
    final visibles = _items
        .where((p) =>
            (!widget.soloPromociones || p['promocion'] != null) &&
            (_categoria == null || p['categoria'] == _categoria))
        .toList();
    return Scaffold(
      appBar: widget.integrado ? null : AppBar(title: const Text('Catálogo')),
      body: Column(children: [
        Container(
            width: double.infinity,
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 14),
            decoration: const BoxDecoration(
                color: Color(0xFF1D1A22),
                borderRadius:
                    BorderRadius.vertical(bottom: Radius.circular(20))),
            child: Column(children: [
              Align(
                  alignment: Alignment.centerLeft,
                  child: TextButton.icon(
                      onPressed: _elegirSucursal,
                      style:
                          TextButton.styleFrom(foregroundColor: Colors.white),
                      icon: const Icon(Icons.location_on_outlined),
                      label: Text(_sucursales
                              .where((s) => s['id'] == _sucursalId)
                              .map((s) => '${s['nombre']}')
                              .firstOrNull ??
                          'Elegir sucursal'))),
              TextField(
                  controller: _texto,
                  onSubmitted: (_) => _buscar(),
                  decoration: InputDecoration(
                      hintText: 'Buscar prendas',
                      prefixIcon: const Icon(Icons.search),
                      suffixIcon: IconButton(
                          tooltip: 'Buscar',
                          icon: const Icon(Icons.arrow_forward),
                          onPressed: _buscar),
                      filled: true,
                      fillColor: Colors.white,
                      border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(24),
                          borderSide: BorderSide.none))),
            ])),
        if (_local)
          Container(
              width: double.infinity,
              color: const Color(0xFFFBEFD9),
              padding: const EdgeInsets.all(10),
              child: Text(off.hayCatalogo
                  ? 'Sin conexión · Datos al ${fechaCorta(off.catalogoGeneradoEn)}; pueden estar desactualizados'
                  : 'Sin conexión · Descargue el catálogo desde Perfil → Modo sin conexión.')),
        if (_error != null)
          Padding(
              padding: const EdgeInsets.all(12),
              child: Column(children: [
                const Text('No se pudo cargar el catálogo. Intente de nuevo.'),
                TextButton(onPressed: _buscar, child: const Text('Reintentar'))
              ])),
        Expanded(
          child: _cargando
              ? const _RejillaCargando()
              : _error != null
                  ? const SizedBox.shrink()
                  : _items.isEmpty
                      ? const Center(child: Text('No se encontraron prendas.'))
                      : RefreshIndicator(
                          onRefresh: _buscar,
                          child: CustomScrollView(
                              controller: _lista,
                              physics: const AlwaysScrollableScrollPhysics(),
                              slivers: [
                                SliverToBoxAdapter(
                                    child: SizedBox(
                                        height: 164,
                                        child: Column(children: [
                                          Expanded(
                                              child: GestureDetector(
                                                  onTapDown: (_) =>
                                                      _temporizador?.cancel(),
                                                  onPanDown: (_) =>
                                                      _temporizador?.cancel(),
                                                  child: PageView(
                                                      controller: _carrusel,
                                                      onPageChanged: (i) =>
                                                          setState(() =>
                                                              _indicePromo = i),
                                                      children:
                                                          _promociones.isEmpty
                                                              ? [
                                                                  _BannerTienda(
                                                                      nombre: widget
                                                                          .nombreEmpresa)
                                                                ]
                                                              : [
                                                                  for (final p
                                                                      in _promociones)
                                                                    _TarjetaPromo(
                                                                        prenda:
                                                                            p,
                                                                        alTocar:
                                                                            () =>
                                                                                _detalle(p))
                                                                ]))),
                                          Row(
                                              mainAxisAlignment:
                                                  MainAxisAlignment.center,
                                              children: [
                                                for (var i = 0;
                                                    i <
                                                        (_promociones.isEmpty
                                                            ? 1
                                                            : _promociones
                                                                .length);
                                                    i++)
                                                  Container(
                                                      width: 6,
                                                      height: 6,
                                                      margin: const EdgeInsets
                                                          .symmetric(
                                                          horizontal: 3,
                                                          vertical: 3),
                                                      decoration: BoxDecoration(
                                                          shape:
                                                              BoxShape.circle,
                                                          color: i ==
                                                                  _indicePromo
                                                              ? Theme.of(
                                                                      context)
                                                                  .colorScheme
                                                                  .primary
                                                              : Theme.of(
                                                                      context)
                                                                  .colorScheme
                                                                  .outlineVariant)),
                                              ]),
                                        ]))),
                                SliverToBoxAdapter(
                                    child: SizedBox(
                                        height: 100,
                                        child: ListView(
                                            scrollDirection: Axis.horizontal,
                                            padding: const EdgeInsets.symmetric(
                                                horizontal: 12, vertical: 8),
                                            children: [
                                              _Categoria(
                                                  nombre: 'Todas',
                                                  seleccionada:
                                                      _categoria == null,
                                                  alTocar: () => setState(
                                                      () => _categoria = null)),
                                              for (final c in categorias)
                                                _Categoria(
                                                    nombre: c,
                                                    seleccionada:
                                                        _categoria == c,
                                                    imagen: _items
                                                        .where((p) =>
                                                            p['categoria'] == c)
                                                        .map((p) => p['imagen']
                                                            as String?)
                                                        .firstOrNull,
                                                    alTocar: () => setState(
                                                        () => _categoria = c)),
                                            ]))),
                                if (widget.soloPromociones && visibles.isEmpty)
                                  const SliverFillRemaining(
                                      child: Center(
                                          child: Text(
                                              'No hay promociones vigentes.'))),
                                SliverPadding(
                                    padding: EdgeInsets.fromLTRB(
                                        12,
                                        4,
                                        12,
                                        MediaQuery.viewPaddingOf(context)
                                                .bottom +
                                            16),
                                    sliver: SliverGrid.builder(
                                        gridDelegate:
                                            const SliverGridDelegateWithFixedCrossAxisCount(
                                                crossAxisCount: 2,
                                                crossAxisSpacing: 12,
                                                mainAxisSpacing: 12,
                                                childAspectRatio: .60),
                                        itemCount: visibles.length,
                                        itemBuilder: (_, i) => _TarjetaPrenda(
                                            prenda: visibles[i],
                                            alTocar: () =>
                                                _detalle(visibles[i])))),
                                if (_mas)
                                  const SliverToBoxAdapter(
                                      child: Padding(
                                          padding: EdgeInsets.all(16),
                                          child: Center(
                                              child:
                                                  CircularProgressIndicator()))),
                              ])),
        ),
      ]),
    );
  }
}

class _TarjetaPrenda extends StatelessWidget {
  const _TarjetaPrenda({required this.prenda, required this.alTocar});
  final Map<String, dynamic> prenda;
  final VoidCallback alTocar;

  @override
  Widget build(BuildContext context) {
    final promo = prenda['promocion'];
    final tituloPromo = promo is Map
        ? '${promo['nombre'] ?? promo['titulo'] ?? 'Oferta'}'
        : promo?.toString();
    final precioOriginal = promo == null
        ? null
        : prenda['precio_original'] ??
            prenda['precio_antes'] ??
            prenda['precio'] ??
            (promo is Map ? promo['precio_original'] : null);
    return Card(
        clipBehavior: Clip.antiAlias,
        child: InkWell(
            onTap: alTocar,
            child:
                Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Expanded(
                  child: Stack(fit: StackFit.expand, children: [
                ImagenPrenda(ruta: prenda['imagen'] as String?),
                if (tituloPromo != null)
                  Positioned(
                      left: 6,
                      top: 6,
                      child: Container(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 7, vertical: 4),
                          decoration: BoxDecoration(
                              color: Theme.of(context).colorScheme.primary,
                              borderRadius: BorderRadius.circular(8)),
                          child: Text(tituloPromo,
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: const TextStyle(
                                  color: Colors.white, fontSize: 10)))),
                if (prenda['disponible'] == false)
                  const Positioned(
                      right: 6,
                      top: 6,
                      child: Chip(
                          label: Text('Agotado'),
                          visualDensity: VisualDensity.compact))
              ])),
              Padding(
                  padding: const EdgeInsets.fromLTRB(8, 6, 8, 8),
                  child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text('${prenda['nombre'] ?? 'Prenda'}',
                            maxLines: 2,
                            overflow: TextOverflow.ellipsis,
                            style: Theme.of(context).textTheme.titleSmall),
                        Text('${prenda['categoria'] ?? ''}',
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: Theme.of(context).textTheme.bodySmall),
                        Row(children: [
                          Text(
                              'Bs ${prenda['precio_final'] ?? prenda['precio'] ?? '—'}',
                              style:
                                  const TextStyle(fontWeight: FontWeight.bold)),
                          if (precioOriginal != null) ...[
                            const SizedBox(width: 5),
                            Flexible(
                                child: Text('Bs $precioOriginal',
                                    overflow: TextOverflow.ellipsis,
                                    style: const TextStyle(
                                        decoration: TextDecoration.lineThrough,
                                        fontSize: 11)))
                          ]
                        ]),
                        Text(
                            'Tallas ${(prenda['tallas'] as List? ?? const []).join(', ')}',
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: Theme.of(context).textTheme.labelSmall),
                      ])),
            ])));
  }
}

class _TarjetaPromo extends StatelessWidget {
  const _TarjetaPromo({required this.prenda, required this.alTocar});
  final Map<String, dynamic> prenda;
  final VoidCallback alTocar;
  @override
  Widget build(BuildContext context) => Padding(
      padding: const EdgeInsets.fromLTRB(8, 8, 4, 8),
      child: Card(
          clipBehavior: Clip.antiAlias,
          child: InkWell(
              onTap: alTocar,
              child: Stack(fit: StackFit.expand, children: [
                ImagenPrenda(ruta: prenda['imagen'] as String?),
                DecoratedBox(
                    decoration: BoxDecoration(
                        gradient: LinearGradient(
                            begin: Alignment.topCenter,
                            end: Alignment.bottomCenter,
                            colors: [
                      Colors.black.withValues(alpha: .05),
                      Colors.black87
                    ]))),
                Positioned(
                    left: 12,
                    right: 12,
                    bottom: 10,
                    child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                              '${_nombrePromo(prenda['promocion'])} · ${prenda['nombre']}',
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: const TextStyle(
                                  color: Colors.white,
                                  fontWeight: FontWeight.bold)),
                          Row(children: [
                            Text('Bs ${prenda['precio_final']}',
                                style: const TextStyle(
                                    color: Colors.white,
                                    fontWeight: FontWeight.bold)),
                            if (prenda['precio'] != null) ...[
                              const SizedBox(width: 8),
                              Text('Bs ${prenda['precio']}',
                                  style: const TextStyle(
                                      color: Colors.white70,
                                      decoration: TextDecoration.lineThrough))
                            ]
                          ])
                        ])),
              ]))));
}

String _nombrePromo(dynamic promo) => promo is Map
    ? '${promo['nombre'] ?? promo['titulo'] ?? 'Promoción'}'
    : '${promo ?? 'Promoción'}';

class _Categoria extends StatelessWidget {
  const _Categoria(
      {required this.nombre,
      required this.seleccionada,
      required this.alTocar,
      this.imagen});
  final String nombre;
  final String? imagen;
  final bool seleccionada;
  final VoidCallback alTocar;
  @override
  Widget build(BuildContext context) => SizedBox(
      width: 76,
      child: InkWell(
          onTap: alTocar,
          child: Column(children: [
            Container(
                width: 56,
                height: 56,
                clipBehavior: Clip.antiAlias,
                decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    border: Border.all(
                        color: seleccionada
                            ? Theme.of(context).colorScheme.primary
                            : Colors.transparent,
                        width: 2)),
                child: imagen == null
                    ? const Icon(Icons.checkroom)
                    : ImagenPrenda(ruta: imagen)),
            const SizedBox(height: 3),
            Text(nombre,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(
                    fontSize: 11,
                    fontWeight:
                        seleccionada ? FontWeight.bold : FontWeight.normal)),
          ])));
}

class _BannerTienda extends StatelessWidget {
  const _BannerTienda({this.nombre});
  final String? nombre;
  @override
  Widget build(BuildContext context) => Padding(
      padding: const EdgeInsets.all(8),
      child: Card(
          color: Theme.of(context).colorScheme.primaryContainer,
          child: Center(
              child: Text(nombre ?? 'Descubre la nueva colección',
                  style: const TextStyle(
                      fontSize: 20, fontWeight: FontWeight.bold)))));
}

class _RejillaCargando extends StatelessWidget {
  const _RejillaCargando();
  @override
  Widget build(BuildContext context) => GridView.builder(
      padding: const EdgeInsets.all(12),
      itemCount: 6,
      gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
          crossAxisCount: 2,
          crossAxisSpacing: 12,
          mainAxisSpacing: 12,
          childAspectRatio: .6),
      itemBuilder: (_, __) => const Card(color: Color(0xFFEAE8E5)));
}

/// Ficha de la prenda con sus tallas y colores. La abren el catálogo y el asistente de compras.
Future<void> mostrarDetallePrenda(BuildContext context, CatalogoRepository repo,
        Map<String, dynamic> prenda, List<Map<String, dynamic>> sucursales) =>
    showModalBottomSheet<void>(
        context: context,
        isScrollControlled: true,
        useSafeArea: true,
        builder: (_) =>
            _DetallePrenda(repo: repo, prenda: prenda, sucursales: sucursales));

class _DetallePrenda extends StatefulWidget {
  const _DetallePrenda(
      {required this.repo, required this.prenda, required this.sucursales});
  final CatalogoRepository repo;
  final Map<String, dynamic> prenda;
  final List<Map<String, dynamic>> sucursales;

  @override
  State<_DetallePrenda> createState() => _DetallePrendaState();
}

class _DetallePrendaState extends State<_DetallePrenda> {
  late final VestidorRepository _vestidor =
      VestidorRepository(context.read<AuthRepository>().api);
  int? _sucursalId;
  Map<String, dynamic>? _opciones;
  Map<String, dynamic>? _detallePrenda;
  Map<String, dynamic>? _varianteElegida;
  String? _mensaje;
  bool _cargandoOpciones = true;
  String? _datosAl; // sin conexión: fecha de la copia descargada de donde salen las variantes

  @override
  void initState() {
    super.initState();
    _cargar();
    _vestidor.precargar(widget.prenda['id']
        as int); // el PNG del vestidor queda listo mientras el cliente mira la ficha
  }

  void _probar() {
    Navigator.of(context).push(MaterialPageRoute<void>(
      builder: (_) => VestidorScreen(
          repo: _vestidor,
          productoId: widget.prenda['id'] as int,
          nombre: '${widget.prenda['nombre']}'),
    ));
  }

  /// Sin respuesta del servidor y sin copia de esta ficha: las variantes salen del catálogo descargado (SQLite), con su fecha.
  Future<void> _cargarLocal() async {
    final offline = context.read<OfflineController>();
    final o = await offline.repo.opcionesLocales(widget.prenda['id'] as int, _sucursalId);
    if (!mounted) return;
    setState(() {
      _opciones = o;
      _datosAl = o == null ? null : offline.catalogoGeneradoEn;
      _mensaje = o == null ? 'Sin conexión: esta prenda todavía no se descargó. Descargue el catálogo con conexión para verla sin Internet.' : null;
    });
  }

  Future<void> _cargar() async {
    setState(() => _cargandoOpciones = true);
    try {
      await _cargarDelServidor();
    } finally {
      if (mounted) setState(() => _cargandoOpciones = false);
    }
  }

  Future<void> _cargarDelServidor() async {
    try {
      final o =
          await widget.repo.opciones(widget.prenda['id'] as int, _sucursalId);
      if (mounted) setState(() { _opciones = o; _datosAl = ApiClient.lecturaLocalDesde; });
      try {
        final detalle = await widget.repo
            .detalle(widget.prenda['id'] as int, sucursalId: _sucursalId);
        if (mounted) setState(() => _detallePrenda = detalle);
      } on ApiException {
        // La ficha conserva su imagen principal si no se puede cargar la galería.
      }
    } on ApiException catch (e) {
      if (!mounted) return;
      if (e.sinConexion) {
        await _cargarLocal();
      } else {
        setState(() => _mensaje = e.mensaje);
      }
    }
  }

  void _reservar(Map<String, dynamic> v) {
    context.read<ReservaBorrador>().agregar(PrendaElegida(
          varianteId: v['variante_id'] as int,
          producto: '${widget.prenda['nombre']}',
          sku: '${v['sku'] ?? ''}',
          talla: '${v['talla']}',
          color: '${v['color']}',
          max: v['cantidad'] as int,
        ));
    setState(() => _mensaje =
        '${widget.prenda['nombre']} (${v['talla']}, ${v['color']}) agregada a su reserva. Confírmela en «Mis reservas».');
  }

  /// Sin conexión la prenda se agrega al carrito guardado en el teléfono; al volver la red se suma al del servidor.
  Future<void> _agregarSinConexion(Map<String, dynamic> v) async {
    final offline = context.read<OfflineController>();
    final sesion = offline.sesion;
    final prenda = (await offline.repo.buscar('', limite: 100000)).where((p) => p.variante.id == v['variante_id']).firstOrNull;
    final sucursal = _sucursalId ?? (await offline.repo.carritoClienteLocal(sesion!.empresaId!, sesion.usuarioId))?['sucursal_id'] as int? ?? (widget.sucursales.isEmpty ? (await offline.repo.sucursales()).firstOrNull?.id : widget.sucursales.first['id'] as int);
    if (prenda == null || sucursal == null) {
      if (mounted) setState(() => _mensaje = 'Descargue el catálogo con conexión antes de agregar prendas sin Internet.');
      return;
    }
    try {
      await CarritoSinConexion(offline.repo, empresaId: sesion!.empresaId!, usuarioId: sesion.usuarioId).agregar(prenda, sucursal);
      if (mounted) setState(() => _mensaje = '${widget.prenda['nombre']} (${v['talla']}, ${v['color']}) agregada a su carrito guardado en este teléfono; se enviará al volver la conexión.');
    } on ApiException catch (e) {
      if (mounted) setState(() => _mensaje = e.mensaje);
    }
  }

  Future<void> _agregar(Map<String, dynamic> v) async {
    if (!context.read<OfflineController>().enLinea) return _agregarSinConexion(v);
    try {
      await widget.repo
          .agregarAlCarrito(v['variante_id'] as int, 1, _sucursalId);
      if (mounted) {
        setState(() => _mensaje =
            '${widget.prenda['nombre']} (${v['talla']}, ${v['color']}) agregada al carrito.');
      }
    } on ApiException catch (e) {
      if (!mounted) return;
      if (e.sinConexion) {
        await _agregarSinConexion(v);
      } else {
        setState(() => _mensaje = e.mensaje);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final variantes = ((_opciones?['variantes'] as List?) ?? const [])
        .cast<Map<String, dynamic>>();
    final todasLasImagenes =
        ((_detallePrenda?['imagenes'] as List?) ?? const [])
            .cast<Map<String, dynamic>>();
    final colorSeleccionado = _varianteElegida?['color_id'];
    final imagenesColor = colorSeleccionado == null
        ? todasLasImagenes
        : todasLasImagenes
            .where((i) => i['color_id'] == colorSeleccionado)
            .toList();
    final imagenes = imagenesColor.isEmpty ? todasLasImagenes : imagenesColor;
    return ConstrainedBox(
      constraints:
          BoxConstraints(maxHeight: MediaQuery.sizeOf(context).height * .9),
      child: Padding(
        padding: EdgeInsets.fromLTRB(
            16,
            16,
            16,
            MediaQuery.viewInsetsOf(context).bottom +
                MediaQuery.viewPaddingOf(context).bottom +
                16),
        child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (imagenes.isNotEmpty)
                SizedBox(
                    height: 150,
                    width: double.infinity,
                    child: PageView(children: [
                      for (final imagen in imagenes)
                        ClipRRect(
                            borderRadius: BorderRadius.circular(14),
                            child: ImagenPrenda(ruta: imagen['url'] as String?))
                    ]))
              else if (widget.prenda['imagen'] is String)
                SizedBox(
                    height: 150,
                    width: double.infinity,
                    child: ClipRRect(
                        borderRadius: BorderRadius.circular(14),
                        child: ImagenPrenda(
                            ruta: widget.prenda['imagen'] as String?))),
              Text('${widget.prenda['nombre']}',
                  style: Theme.of(context).textTheme.titleLarge),
              const SizedBox(height: 4),
              Align(
                  alignment: Alignment.centerLeft,
                  child: TextButton.icon(
                      onPressed: _probar,
                      icon: const Icon(Icons.checkroom),
                      label: const Text('Probar en el vestidor'))),
              const SizedBox(height: 4),
              DropdownButtonFormField<int?>(
                initialValue: _sucursalId,
                decoration:
                    const InputDecoration(labelText: 'Disponibilidad en'),
                items: [
                  const DropdownMenuItem<int?>(
                      value: null, child: Text('Todas las sucursales')),
                  for (final s in widget.sucursales)
                    DropdownMenuItem<int?>(
                        value: s['id'] as int, child: Text('${s['nombre']}'))
                ],
                onChanged: (v) {
                  setState(() {
                    _sucursalId = v;
                    _opciones = null;
                    _varianteElegida = null;
                  });
                  _cargar();
                },
              ),
              const SizedBox(height: 8),
              if (_datosAl != null)
                Padding(
                    padding: const EdgeInsets.only(bottom: 6),
                    child: Text('Sin conexión · datos al ${fechaCorta(_datosAl)}; pueden estar desactualizados.', style: const TextStyle(fontSize: 12, color: Color(0xFF8A5A00)))),
              if (_opciones == null && _cargandoOpciones)
                const Center(child: CircularProgressIndicator()),
              Flexible(
                child: ListView(shrinkWrap: true, children: [
                  for (final v in variantes)
                    ListTile(
                      dense: true,
                      selected:
                          _varianteElegida?['variante_id'] == v['variante_id'],
                      onTap: () => setState(() => _varianteElegida = v),
                      title: Text('${v['talla']} · ${v['color']}'),
                      subtitle: Text(v['disponible'] == true
                          ? '${v['cantidad']} disponible(s)'
                          : 'Agotada'),
                      trailing: Text('Bs ${v['precio_final']}'),
                    ),
                ]),
              ),
              if (_mensaje != null)
                Padding(
                    padding: const EdgeInsets.only(top: 8),
                    child: Text(_mensaje!)),
              const Divider(),
              Row(children: [
                IconButton(
                    tooltip: 'Probar en el vestidor',
                    onPressed: _probar,
                    icon: const Icon(Icons.checkroom)),
                Expanded(
                    child: OutlinedButton.icon(
                        onPressed: _varianteElegida == null ||
                                _varianteElegida!['disponible'] != true
                            ? null
                            : () => _reservar(_varianteElegida!),
                        icon: const Icon(Icons.bookmark_add_outlined),
                        label: const Text('Reservar'))),
                const SizedBox(width: 8),
                Expanded(
                    child: FilledButton.icon(
                        onPressed: _varianteElegida == null ||
                                _varianteElegida!['disponible'] != true
                            ? null
                            : () => _agregar(_varianteElegida!),
                        icon: const Icon(Icons.add_shopping_cart),
                        label: const Text('Agregar'))),
              ]),
            ]),
      ),
    );
  }
}
