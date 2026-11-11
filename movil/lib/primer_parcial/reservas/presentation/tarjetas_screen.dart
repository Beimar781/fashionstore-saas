import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../../core/network/api_client.dart';
import '../../../features/auth/data/auth_repository.dart';
import '../../../features/offline/presentation/modo_offline_screen.dart' show fechaCorta;
import '../../../features/offline/presentation/offline_controller.dart';
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
  bool _cargando = true;
  String? _copiaDel; // sin conexión: fecha de la lista guardada (solo se pueden ver, no quitar)
  @override
  void initState() {
    super.initState();
    _cargar();
  }

  Future<void> _cargar() async {
    try {
      ApiClient.lecturaLocalDesde = null;
      final tarjetas = await _repo.tarjetasGuardadas();
      if (mounted) {
        setState(() {
          _tarjetas = tarjetas;
          _error = null;
          _copiaDel = ApiClient.lecturaLocalDesde;
        });
      }
    } on Exception catch (e) {
      // sin conexión y sin lectura guardada: se usa la lista que dejó la última compra con red (sirve para pagar sin conexión)
      final locales = e is ApiException && e.sinConexion ? await context.read<OfflineController>().repo.tarjetasLocales() : const <Map<String, dynamic>>[];
      if (mounted) {
        setState(() {
          _tarjetas = [for (final j in locales) TarjetaGuardada.desdeJson(j)];
          _copiaDel = locales.isEmpty ? null : DateTime.now().toIso8601String();
          _error = locales.isEmpty ? _mensaje(e) : null;
        });
      }
    }
    if (mounted) setState(() => _cargando = false);
  }

  Future<void> _eliminar(TarjetaGuardada tarjeta) async {
    if (_copiaDel != null) return setState(() => _error = 'Esta función necesita Internet.');
    try {
      await _repo.eliminarTarjeta(tarjeta.id);
      if (mounted) {
        setState(() => _tarjetas.removeWhere((t) => t.id == tarjeta.id));
      }
    } on Exception catch (e) {
      if (mounted) setState(() => _error = _mensaje(e));
    }
  }

  /// Guardar, ver y quitar tarjetas depende de Internet (CU-32): sin red se explica con un mensaje claro.
  String _mensaje(Object e) => e is ApiException && e.sinConexion ? 'Sin conexión: las tarjetas guardadas necesitan Internet.' : '$e';

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
                if (_copiaDel != null)
                  Padding(padding: const EdgeInsets.only(bottom: 8), child: Text('Sin conexión · datos al ${fechaCorta(_copiaDel)}. Quitar una tarjeta necesita Internet.', style: const TextStyle(fontSize: 12, color: Color(0xFF8A5A00)))),
                if (_cargando && _error == null) const Center(child: CircularProgressIndicator()),
                if (!_cargando && _tarjetas.isEmpty && _error == null)
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
                              onPressed: _copiaDel != null ? null : () => _eliminar(tarjeta)))),
              ])));
}
