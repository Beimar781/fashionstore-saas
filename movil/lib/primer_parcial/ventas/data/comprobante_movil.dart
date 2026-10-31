import '../../../core/network/api_client.dart';
import 'ventas_repository.dart';

const msgSinConexionComprobante = 'Sin conexión: no se puede descargar el comprobante. Inténtelo de nuevo cuando tenga red.';
const msgComprobanteNoEncontrado = 'No se encontró el comprobante de esta compra.';
const msgSinVisorPdf = 'No hay una aplicación para abrir PDF en este teléfono.';

/// Ver el comprobante PDF de una compra: lo descarga y lo abre con el visor del teléfono (desde ahí se comparte o se guarda).
class ComprobanteMovil {
  ComprobanteMovil(this._repo, {Future<bool> Function(String ruta)? abrir}) : _abrir = abrir ?? abrirConVisor;

  final VentasRepository _repo;
  final Future<bool> Function(String ruta) _abrir;

  /// Devuelve null si el PDF se abrió; si no, el mensaje de error para mostrar al cliente.
  Future<String?> ver(int pedidoId, String numero) async {
    try {
      final ruta = await _repo.descargarComprobante(pedidoId, numero);
      return await _abrir(ruta) ? null : msgSinVisorPdf;
    } on ApiException catch (e) {
      if (e.sinConexion) return msgSinConexionComprobante;
      return msgComprobanteNoEncontrado; // 404 o 403: no es una compra de este cliente o no tiene comprobante
    }
  }
}
