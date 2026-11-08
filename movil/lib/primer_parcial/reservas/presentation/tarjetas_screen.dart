import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../../features/auth/data/auth_repository.dart';
import '../data/medio_de_pago.dart';
import '../data/reservas_repository.dart';

/// Consulta y permite quitar las tarjetas guardadas del cliente.
class TarjetasScreen extends StatefulWidget {
  const TarjetasScreen({super.key});
  @override
  State<TarjetasScreen> createState() => _TarjetasScreenState();
}

class _TarjetasScreenState extends State<TarjetasScreen> {
  late final _repo = ReservasRepository(context.read<AuthRepository>().api);
  List<TarjetaGuardada> _tarjetas = [];
  String? _error;
  @override
  void initState() {
    super.initState();
    _cargar();
  }

  Future<void> _cargar() async {
    try {
      final tarjetas = await _repo.tarjetasGuardadas();
      if (mounted) {
        setState(() {
          _tarjetas = tarjetas;
          _error = null;
        });
      }
    } on Exception catch (e) {
      if (mounted) setState(() => _error = '$e');
    }
  }

  Future<void> _eliminar(TarjetaGuardada tarjeta) async {
    try {
      await _repo.eliminarTarjeta(tarjeta.id);
      if (mounted) {
        setState(() => _tarjetas.removeWhere((t) => t.id == tarjeta.id));
      }
    } on Exception catch (e) {
      if (mounted) setState(() => _error = '$e');
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
      appBar: AppBar(title: const Text('Tarjetas guardadas')),
      body: RefreshIndicator(
          onRefresh: _cargar,
          child: ListView(
              padding: EdgeInsets.fromLTRB(
                  12, 12, 12, MediaQuery.viewPaddingOf(context).bottom + 16),
              children: [
                if (_error != null) Text(_error!),
                if (_tarjetas.isEmpty && _error == null)
                  const Padding(
                      padding: EdgeInsets.all(24),
                      child: Text('No tiene tarjetas guardadas.')),
                for (final tarjeta in _tarjetas)
                  Card(
                      child: ListTile(
                          leading: const Icon(Icons.credit_card),
                          title: Text(tarjeta.descripcion),
                          trailing: IconButton(
                              tooltip: 'Eliminar tarjeta',
                              icon: const Icon(Icons.delete_outline),
                              onPressed: () => _eliminar(tarjeta)))),
              ])));
}
