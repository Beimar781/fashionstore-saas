import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../../../core/network/api_client.dart';
import '../../../../features/auth/data/auth_repository.dart';
import '../../../catalogo/data/catalogo_repository.dart';
import '../../../catalogo/presentation/catalogo_screen.dart'
    show mostrarDetallePrenda;
import '../data/asistente_repository.dart';
import 'chat_asistente.dart';
import '../../../../features/auth/presentation/auth_controller.dart';
import '../../../../features/offline/presentation/offline_controller.dart';

/// CU-07 · Asistente de compras (plan Profesional): el cliente pide prendas en lenguaje natural y el servidor responde con prendas reales con stock.
class AsistenteScreen extends StatefulWidget {
  const AsistenteScreen({super.key});

  @override
  State<AsistenteScreen> createState() => _AsistenteScreenState();
}

class _AsistenteScreenState extends State<AsistenteScreen> {
  late final CatalogoRepository _catalogo =
      CatalogoRepository(context.read<AuthRepository>().api);
  late final ChatAsistente _chat = ChatAsistente(
      AsistenteRepository(context.read<AuthRepository>().api),
      responderLocal: _responderLocal);
  final _texto = TextEditingController();
  final _desplazamiento = ScrollController();
  List<Map<String, dynamic>> _sucursales = [];
  int? _sucursalId;

  @override
  void initState() {
    super.initState();
    _chat.addListener(_alCambiar);
    _cargarSucursales();
  }

  @override
  void dispose() {
    _chat.dispose();
    _texto.dispose();
    _desplazamiento.dispose();
    super.dispose();
  }

  Future<void> _cargarSucursales() async {
    try {
      final s = await _catalogo.sucursales();
      if (mounted) setState(() => _sucursales = s);
    } on ApiException {
      // sin la lista el asistente igual funciona con «Cualquier sucursal»
    }
  }

  void _alCambiar() {
    if (!mounted) return;
    setState(() {});
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_desplazamiento.hasClients) {
        _desplazamiento.animateTo(_desplazamiento.position.maxScrollExtent,
            duration: const Duration(milliseconds: 200), curve: Curves.easeOut);
      }
    });
  }

  void _enviar(String texto) {
    if (!(context.read<AuthController>().sesion?.iaHabilitada ?? false)) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
          content: Text('Su plan no incluye el asistente de compras.')));
      return;
    }
    _texto.clear();
    _chat.enviar(texto, sucursalId: _sucursalId);
  }

  Future<MensajeChat> _responderLocal(String texto, int? sucursalId) async {
    final repo = context.read<OfflineController>().repo;
    if (!await repo.hayCatalogo()) {
      throw ApiException(
          'Descargue el catálogo con conexión para usar el asistente sin conexión.');
    }
    final normal = _normalizar(texto);
    final prendas = await repo.buscar('', limite: 1000);
    final categorias = prendas
        .map((x) => x.producto.categoria)
        .toSet()
        .where((x) => _contiene(normal, x))
        .toSet();
    final colores = prendas
        .map((x) => x.variante.color)
        .toSet()
        .where((x) => _contiene(normal, x))
        .toSet();
    final talla = RegExp(r'\btalla\s+([a-z0-9]{1,3})\b|\b(xs|xl|xxl)\b')
            .firstMatch(normal)
            ?.group(1) ??
        RegExp(r'\b(xs|xl|xxl)\b').firstMatch(normal)?.group(1);
    final max = RegExp(
            r'(?:menos de|hasta|maximo|no mas de|por debajo de|bajo)\s+(?:bs\.?\s*)?(\d+(?:[.,]\d+)?)')
        .firstMatch(normal)
        ?.group(1)
        ?.replaceAll(',', '.');
    final min = RegExp(
            r'(?:mas de|desde|minimo|por encima de)\s+(?:bs\.?\s*)?(\d+(?:[.,]\d+)?)')
        .firstMatch(normal)
        ?.group(1)
        ?.replaceAll(',', '.');
    final genero = RegExp(r'\b(nino|nina|infantil|kids)\b').hasMatch(normal)
        ? 'NINOS'
        : RegExp(r'\b(mujer|dama|femenin|chica)\b').hasMatch(normal)
            ? 'FEMENINO'
            : RegExp(r'\b(hombre|varon|masculin|caballero|chico)\b')
                    .hasMatch(normal)
                ? 'MASCULINO'
                : null;
    final oferta =
        RegExp(r'\b(oferta|promocion|descuento|rebaja)').hasMatch(normal);
    final ocasion = [
      'formal',
      'casual',
      'deportiv',
      'fiesta',
      'oficina',
      'playa',
      'invierno',
      'verano',
      'elegante'
    ].where(normal.contains).firstOrNull;
    final elegidas = <Map<String, dynamic>>[];
    final ids = <int>{};
    for (final item in prendas) {
      final p = item.producto, v = item.variante;
      if (ids.contains(p.id) ||
          v.stockEn(sucursalId) <= 0 ||
          (categorias.isNotEmpty && !categorias.contains(p.categoria)) ||
          (colores.isNotEmpty && !colores.contains(v.color)) ||
          (talla != null && v.talla.toUpperCase() != talla.toUpperCase()) ||
          (max != null &&
              double.tryParse(v.precioFinal) != null &&
              double.parse(v.precioFinal) > double.parse(max)) ||
          (min != null &&
              double.tryParse(v.precioFinal) != null &&
              double.parse(v.precioFinal) < double.parse(min)) ||
          (genero != null && p.genero != genero && p.genero != 'UNISEX') ||
          (oferta && v.promocion == null) ||
          (ocasion != null &&
              !_normalizar('${p.nombre} ${p.categoria}').contains(ocasion))) {
        continue;
      }
      ids.add(p.id);
      elegidas.add({
        'id': p.id,
        'nombre': p.nombre,
        'categoria': p.categoria,
        'promocion': v.promocion,
        'precio': v.precio,
        'precio_final': v.precioFinal,
        'imagen': p.imagen
      });
      if (elegidas.length == 6) break;
    }
    final detalle = [
      ...categorias,
      ...colores,
      if (talla != null) 'talla ${talla.toUpperCase()}',
      if (max != null) 'hasta Bs $max',
      if (min != null) 'desde Bs $min',
      if (ocasion != null) ocasion
    ].join(', ');
    final outfit =
        RegExp(r'\b(outfit|conjunto|combinar|combinacion|atuendo|look)\b')
            .hasMatch(normal);
    if (outfit && elegidas.length > 1) {
      final categoriasVistas = <String>{};
      elegidas
          .removeWhere((x) => !categoriasVistas.add(x['categoria'] as String));
    }
    final respuesta = elegidas.isEmpty
        ? (oferta
            ? 'No encontré ofertas con esas características.'
            : 'No encontré prendas con esas características.')
        : '${outfit ? 'Le armé un conjunto' : 'Encontré ${elegidas.length} prenda(s) disponible(s)'}${detalle.isEmpty ? '' : ' ($detalle)'}${outfit ? ': ${elegidas.map((x) => x['nombre']).join(', ')}.' : '.'}';
    return MensajeChat(
        esUsuario: false,
        texto: respuesta,
        productos: elegidas,
        sugerencias: elegidas.isEmpty
            ? const ['Quiero ropa formal', 'Arme un outfit casual']
            : const [
                'Muéstreme algo más económico',
                '¿Lo tiene en otro color?',
                'Muéstreme las ofertas'
              ],
        respuestaLocal: true);
  }

  String _normalizar(String valor) => valor
      .toLowerCase()
      .replaceAll(RegExp('[áàäâ]'), 'a')
      .replaceAll(RegExp('[éèëê]'), 'e')
      .replaceAll(RegExp('[íìïî]'), 'i')
      .replaceAll(RegExp('[óòöô]'), 'o')
      .replaceAll(RegExp('[úùüû]'), 'u')
      .replaceAll('ñ', 'n');
  bool _contiene(String texto, String termino) {
    final base = _normalizar(termino);
    final palabras = texto.split(RegExp(r'\W+'));
    return [base, base.replaceAll(RegExp(r's$'), ''), '${base}s', '${base}es']
        .any(palabras.contains);
  }

  @override
  Widget build(BuildContext context) {
    final esquema = Theme.of(context).colorScheme;
    return Scaffold(
      appBar: AppBar(title: const Text('Asistente de compras')),
      body: Column(children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(12, 8, 12, 0),
          child: DropdownButtonFormField<int?>(
            initialValue: _sucursalId,
            decoration:
                const InputDecoration(labelText: 'Ver prendas con stock en'),
            items: [
              const DropdownMenuItem<int?>(
                  value: null, child: Text('Cualquier sucursal')),
              for (final s in _sucursales)
                DropdownMenuItem<int?>(
                    value: s['id'] as int, child: Text('${s['nombre']}'))
            ],
            onChanged: (v) => setState(() => _sucursalId = v),
          ),
        ),
        Expanded(
          child: ListView(
              controller: _desplazamiento,
              padding: const EdgeInsets.all(12),
              children: [
                if (_chat.mensajes.isEmpty)
                  const Text(
                      'Cuénteme qué busca y le muestro prendas disponibles, por ejemplo «una camisa para el trabajo» o «recomiéndame algo».'),
                for (var i = 0; i < _chat.mensajes.length; i++)
                  _mensaje(_chat.mensajes[i],
                      esUltimo: i == _chat.mensajes.length - 1,
                      esquema: esquema),
                if (_chat.pensando) _burbuja('Buscando…', false, esquema),
                if (_chat.error != null)
                  Padding(
                      padding: const EdgeInsets.only(top: 8),
                      child: Text(_chat.error!,
                          style: TextStyle(color: esquema.error))),
              ]),
        ),
        SafeArea(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(12, 4, 12, 8),
            child: Row(children: [
              Expanded(
                  child: TextField(
                      controller: _texto,
                      maxLength: 500,
                      enabled: !_chat.pensando,
                      onSubmitted: _enviar,
                      decoration: const InputDecoration(
                          hintText: 'Escriba su consulta…', counterText: ''))),
              IconButton.filled(
                  onPressed: _chat.pensando ? null : () => _enviar(_texto.text),
                  icon: const Icon(Icons.send)),
            ]),
          ),
        ),
      ]),
    );
  }

  Widget _mensaje(MensajeChat m,
          {required bool esUltimo, required ColorScheme esquema}) =>
      Column(
        crossAxisAlignment:
            m.esUsuario ? CrossAxisAlignment.end : CrossAxisAlignment.start,
        children: [
          _burbuja(m.texto, m.esUsuario, esquema),
          if (m.respuestaLocal)
            const Padding(
                padding: EdgeInsets.only(left: 8),
                child: Text('Respuesta local, sin IA (sin conexión)',
                    style: TextStyle(fontSize: 12))),
          for (final p in m.productos)
            Card(
              child: ListTile(
                dense: true,
                title: Text('${p['nombre']}'),
                subtitle: Text(
                    '${p['categoria']}${p['promocion'] != null ? ' · ${p['promocion']}' : ''}'),
                trailing: Text('Bs ${p['precio_final']}',
                    style: const TextStyle(fontWeight: FontWeight.w600)),
                onTap: () =>
                    mostrarDetallePrenda(context, _catalogo, p, _sucursales),
              ),
            ),
          if (esUltimo && m.sugerencias.isNotEmpty)
            Wrap(spacing: 8, children: [
              for (final s in m.sugerencias)
                ActionChip(label: Text(s), onPressed: () => _enviar(s))
            ]),
        ],
      );

  Widget _burbuja(String texto, bool esUsuario, ColorScheme esquema) =>
      Container(
        margin: const EdgeInsets.symmetric(vertical: 4),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
        constraints:
            BoxConstraints(maxWidth: MediaQuery.of(context).size.width * 0.8),
        decoration: BoxDecoration(
            color:
                esUsuario ? esquema.primary : esquema.surfaceContainerHighest,
            borderRadius: BorderRadius.circular(14)),
        child: Text(texto,
            style: TextStyle(color: esUsuario ? esquema.onPrimary : null)),
      );
}
