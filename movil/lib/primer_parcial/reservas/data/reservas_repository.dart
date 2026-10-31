import '../../../core/network/api_client.dart';
import 'datos_entrega.dart';

/// Acceso a la API del carrito (CU-08), las reservas del cliente (CU-10) y el pago de la compra digital (CU-11, CU-32).
class ReservasRepository {
  ReservasRepository(this._api);

  final ApiClient _api;

  // ---- carrito (CU-08) ----
  Future<Map<String, dynamic>> carrito() => _api.get('/carrito');
  Future<Map<String, dynamic>> cambiarCantidad(int itemId, int cantidad) => _api.put('/carrito/items/$itemId', {'cantidad': cantidad});
  Future<Map<String, dynamic>> quitar(int itemId) => _api.delete('/carrito/items/$itemId');

  // ---- compra digital: checkout y pago con tarjeta de prueba (CU-11, CU-32) ----
  Future<Map<String, dynamic>> checkout(DatosEntrega datos) => _api.post('/compras/checkout', datos.aCuerpo());

  /// Inicia el pago. Con Stripe devuelve la clave pública y el `client_secret` para la hoja de pago; con la pasarela simulada se confirma con una tarjeta de prueba.
  Future<Map<String, dynamic>> iniciarPago(int pedidoId) => _api.post('/pagos/pedidos/$pedidoId/iniciar', {});

  /// Con Stripe la tarjeta ya se confirmó en la hoja de pago: `tarjeta` va vacía y el servidor lee el resultado en Stripe.
  Future<Map<String, dynamic>> confirmarPago(int pagoId, Map<String, dynamic>? tarjeta) => _api.post('/pagos/$pagoId/confirmar', {'tarjeta': tarjeta});

  Future<Map<String, dynamic>> reconciliarPago(int pagoId) => _api.post('/pagos/$pagoId/reconciliar', {});

  // ---- reservas (CU-10) ----
  Future<List<Map<String, dynamic>>> reservas() async => (await _api.getLista('/reservas')).cast<Map<String, dynamic>>();
  Future<Map<String, dynamic>> reservar(Map<String, dynamic> cuerpo) => _api.post('/reservas', cuerpo);
  Future<Map<String, dynamic>> cancelar(int reservaId, {String motivo = ''}) => _api.post('/reservas/$reservaId/cancelar', {'motivo': motivo.trim()});
}
