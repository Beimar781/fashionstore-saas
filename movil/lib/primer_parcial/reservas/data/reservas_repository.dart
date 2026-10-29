import '../../../core/network/api_client.dart';

/// Acceso a la API del carrito (CU-08), las reservas del cliente (CU-10) y el pago de la compra digital (CU-11, CU-32).
class ReservasRepository {
  ReservasRepository(this._api);

  final ApiClient _api;

  // ---- carrito (CU-08) ----
  Future<Map<String, dynamic>> carrito() => _api.get('/carrito');
  Future<Map<String, dynamic>> cambiarCantidad(int itemId, int cantidad) => _api.put('/carrito/items/$itemId', {'cantidad': cantidad});
  Future<Map<String, dynamic>> quitar(int itemId) => _api.delete('/carrito/items/$itemId');

  // ---- compra digital: checkout y pago con tarjeta de prueba (CU-11, CU-32) ----
  Future<Map<String, dynamic>> checkout() => _api.post('/compras/checkout', {'tipo_entrega': 'RETIRO', 'nit_ci': '0', 'razon_social': 'Sin nombre'});

  /// Inicia el pago. Con Stripe la tarjeta se captura en la web; con la pasarela de pruebas se confirma con una tarjeta de prueba.
  Future<Map<String, dynamic>> iniciarPago(int pedidoId) => _api.post('/pagos/pedidos/$pedidoId/iniciar', {});

  Future<Map<String, dynamic>> confirmarPago(int pagoId, Map<String, dynamic> tarjeta) => _api.post('/pagos/$pagoId/confirmar', {'tarjeta': tarjeta});

  // ---- reservas (CU-10) ----
  Future<List<Map<String, dynamic>>> reservas() async => (await _api.getLista('/reservas')).cast<Map<String, dynamic>>();
  Future<Map<String, dynamic>> cancelar(int reservaId) => _api.post('/reservas/$reservaId/cancelar', {});
}
