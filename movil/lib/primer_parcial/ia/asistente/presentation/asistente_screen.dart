import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../../../core/network/api_client.dart';
import '../../../../features/auth/data/auth_repository.dart';
import '../../../catalogo/data/catalogo_repository.dart';
import '../../../catalogo/presentation/catalogo_screen.dart' show mostrarDetallePrenda;
import '../data/asistente_repository.dart';
import 'chat_asistente.dart';

/// CU-07 · Asistente de compras (plan Profesional): el cliente pide prendas en lenguaje natural y el servidor responde con prendas reales con stock.
class AsistenteScreen extends StatefulWidget {
  const AsistenteScreen({super.key});

  @override
  State<AsistenteScreen> createState() => _AsistenteScreenState();
}

class _AsistenteScreenState extends State<AsistenteScreen> {
  late final CatalogoRepository _catalogo = CatalogoRepository(context.read<AuthRepository>().api);
  late final ChatAsistente _chat = ChatAsistente(AsistenteRepository(context.read<AuthRepository>().api));
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
      if (_desplazamiento.hasClients) _desplazamiento.animateTo(_desplazamiento.position.maxScrollExtent, duration: const Duration(milliseconds: 200), curve: Curves.easeOut);
    });
  }

  void _enviar(String texto) {
    _texto.clear();
    _chat.enviar(texto, sucursalId: _sucursalId);
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
            decoration: const InputDecoration(labelText: 'Ver prendas con stock en'),
            items: [const DropdownMenuItem<int?>(value: null, child: Text('Cualquier sucursal')), for (final s in _sucursales) DropdownMenuItem<int?>(value: s['id'] as int, child: Text('${s['nombre']}'))],
            onChanged: (v) => setState(() => _sucursalId = v),
          ),
        ),
        Expanded(
          child: ListView(controller: _desplazamiento, padding: const EdgeInsets.all(12), children: [
            if (_chat.mensajes.isEmpty) const Text('Cuénteme qué busca y le muestro prendas disponibles, por ejemplo «una camisa para el trabajo» o «recomiéndame algo».'),
            for (var i = 0; i < _chat.mensajes.length; i++) _mensaje(_chat.mensajes[i], esUltimo: i == _chat.mensajes.length - 1, esquema: esquema),
            if (_chat.pensando) _burbuja('Buscando…', false, esquema),
            if (_chat.error != null) Padding(padding: const EdgeInsets.only(top: 8), child: Text(_chat.error!, style: TextStyle(color: esquema.error))),
          ]),
        ),
        SafeArea(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(12, 4, 12, 8),
            child: Row(children: [
              Expanded(child: TextField(controller: _texto, maxLength: 500, enabled: !_chat.pensando, onSubmitted: _enviar, decoration: const InputDecoration(hintText: 'Escriba su consulta…', counterText: ''))),
              IconButton.filled(onPressed: _chat.pensando ? null : () => _enviar(_texto.text), icon: const Icon(Icons.send)),
            ]),
          ),
        ),
      ]),
    );
  }

  Widget _mensaje(MensajeChat m, {required bool esUltimo, required ColorScheme esquema}) => Column(
        crossAxisAlignment: m.esUsuario ? CrossAxisAlignment.end : CrossAxisAlignment.start,
        children: [
          _burbuja(m.texto, m.esUsuario, esquema),
          for (final p in m.productos)
            Card(
              child: ListTile(
                dense: true,
                title: Text('${p['nombre']}'),
                subtitle: Text('${p['categoria']}${p['promocion'] != null ? ' · ${p['promocion']}' : ''}'),
                trailing: Text('Bs ${p['precio_final']}', style: const TextStyle(fontWeight: FontWeight.w600)),
                onTap: () => mostrarDetallePrenda(context, _catalogo, p, _sucursales),
              ),
            ),
          if (esUltimo && m.sugerencias.isNotEmpty) Wrap(spacing: 8, children: [for (final s in m.sugerencias) ActionChip(label: Text(s), onPressed: () => _enviar(s))]),
        ],
      );

  Widget _burbuja(String texto, bool esUsuario, ColorScheme esquema) => Container(
        margin: const EdgeInsets.symmetric(vertical: 4),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
        constraints: BoxConstraints(maxWidth: MediaQuery.of(context).size.width * 0.8),
        decoration: BoxDecoration(color: esUsuario ? esquema.primary : esquema.surfaceContainerHighest, borderRadius: BorderRadius.circular(14)),
        child: Text(texto, style: TextStyle(color: esUsuario ? esquema.onPrimary : null)),
      );
}
