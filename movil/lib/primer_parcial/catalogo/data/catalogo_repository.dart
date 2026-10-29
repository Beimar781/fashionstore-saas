import '../../../core/network/api_client.dart';

/// Acceso a la API de catálogo (CU-03, CU-04) y a las opciones color × talla de una prenda. Es la misma API que usa la PWA.
class CatalogoRepository {
  CatalogoRepository(this._api);

  final ApiClient _api;

  /// Prendas del catálogo (con o sin texto de búsqueda). `items` trae lo que muestra la tarjeta del catálogo.
  Future<List<Map<String, dynamic>>> buscar(String texto, {int? sucursalId}) async {
    final q = texto.trim();
    final partes = ['tamano=30', if (q.isNotEmpty) 'q=${Uri.encodeQueryComponent(q)}', if (sucursalId != null) 'sucursal=$sucursalId'];
    final r = await _api.get('/catalogo/buscar?${partes.join('&')}');
    return (r['items'] as List).cast<Map<String, dynamic>>();
  }

  Future<List<Map<String, dynamic>>> sucursales() async => (await _api.getLista('/catalogo/sucursales')).cast<Map<String, dynamic>>();

  /// Un solo endpoint con las variantes y su disponibilidad: la app solo dibuja, no recalcula.
  Future<Map<String, dynamic>> opciones(int productoId, int? sucursalId) =>
      _api.get('/catalogo/productos/$productoId/opciones${sucursalId == null ? '' : '?sucursal=$sucursalId'}');

  Future<Map<String, dynamic>> agregarAlCarrito(int varianteId, int cantidad, int? sucursalId) =>
      _api.post('/carrito/items', {'variante_id': varianteId, 'cantidad': cantidad, if (sucursalId != null) 'sucursal_id': sucursalId});
}
