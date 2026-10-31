import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../../core/network/api_client.dart';
import '../../../features/auth/data/auth_repository.dart';
import '../../../features/offline/presentation/modo_offline_screen.dart' show fechaCorta;
import '../data/reserva_borrador.dart';
import '../data/reservas_repository.dart';
import 'mi_reserva_screen.dart';

/// Reservas del cliente (CU-10): consulta y cancelación con motivo. «Mi reserva» confirma una reserva nueva; sin conexión se reserva desde «Modo sin conexión».
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

  Future<String?> _pedirMotivo() {
    final motivo = TextEditingController();
    return showDialog<String>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Cancelar reserva'),
        content: TextField(controller: motivo, maxLength: 200, decoration: const InputDecoration(labelText: 'Motivo (opcional)')),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Volver')),
          FilledButton(onPressed: () => Navigator.pop(ctx, motivo.text), child: const Text('Cancelar reserva')),
        ],
      ),
    );
  }

  Future<void> _nuevaReserva() async {
    await Navigator.push<bool>(context, MaterialPageRoute(builder: (_) => const MiReservaScreen()));
    await _cargar();
  }

  Future<void> _cancelar(Map<String, dynamic> r) async {
    final motivo = await _pedirMotivo();
    if (motivo == null) return; // el cliente se arrepintió
    try {
      await _repo.cancelar(r['id'] as int, motivo: motivo);
      await _cargar();
    } on ApiException catch (e) {
      if (mounted) setState(() => _error = e.mensaje);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Mis reservas')),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _nuevaReserva,
        icon: const Icon(Icons.bookmark_add_outlined),
        label: Text('Mi reserva (${context.watch<ReservaBorrador>().total})'),
      ),
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
