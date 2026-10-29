import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../../core/network/api_client.dart';
import '../../../features/auth/data/auth_repository.dart';
import '../../../features/offline/presentation/modo_offline_screen.dart' show fechaCorta;
import '../data/reservas_repository.dart';

/// Reservas del cliente (CU-10): consulta y cancelación. Para reservar prendas (con o sin conexión) se usa «Modo sin conexión».
class ReservasScreen extends StatefulWidget {
  const ReservasScreen({super.key});

  @override
  State<ReservasScreen> createState() => _ReservasScreenState();
}

class _ReservasScreenState extends State<ReservasScreen> {
  late final ReservasRepository _repo = ReservasRepository(context.read<AuthRepository>().api);
  List<Map<String, dynamic>>? _reservas;
  String? _error;

  @override
  void initState() {
    super.initState();
    _cargar();
  }

  Future<void> _cargar() async {
    try {
      final r = await _repo.reservas();
      if (mounted) setState(() { _reservas = r; _error = null; });
    } on ApiException catch (e) {
      if (mounted) setState(() => _error = e.sinConexion ? 'Sin conexión: no se pueden consultar las reservas del servidor.' : e.mensaje);
    }
  }

  Future<void> _cancelar(Map<String, dynamic> r) async {
    try {
      await _repo.cancelar(r['id'] as int);
      await _cargar();
    } on ApiException catch (e) {
      if (mounted) setState(() => _error = e.mensaje);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Mis reservas')),
      body: RefreshIndicator(
        onRefresh: _cargar,
        child: ListView(padding: const EdgeInsets.all(16), children: [
          if (_error != null) Text(_error!, style: const TextStyle(color: Colors.red)),
          if (_reservas == null && _error == null) const Center(child: CircularProgressIndicator()),
          if (_reservas != null && _reservas!.isEmpty) const Padding(padding: EdgeInsets.all(24), child: Center(child: Text('Todavía no tiene reservas.'))),
          for (final r in _reservas ?? const <Map<String, dynamic>>[])
            Card(
              child: ListTile(
                title: Text('${r['codigo']} · ${r['estado']}'),
                subtitle: Text('${r['sucursal']} · ${fechaCorta(r['programada_para'] as String?)}\n${((r['items'] as List?) ?? const []).map((i) => '${(i as Map)['cantidad']}× ${i['producto']}').join(', ')}'),
                isThreeLine: true,
                trailing: r['puede_cancelar'] == true ? TextButton(onPressed: () => _cancelar(r), child: const Text('Cancelar')) : null,
              ),
            ),
        ]),
      ),
    );
  }
}
