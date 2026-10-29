import '../../../core/network/api_client.dart';

/// Acceso a la API del historial de compras del cliente (CU-12).
class VentasRepository {
  VentasRepository(this._api);

  final ApiClient _api;

  Future<List<Map<String, dynamic>>> compras() async {
    final r = await _api.get('/compras');
    return (r['compras'] as List).cast<Map<String, dynamic>>();
  }

  Future<Map<String, dynamic>> detalle(int pedidoId) => _api.get('/compras/$pedidoId');
}
