import 'dart:io';

import 'package:open_filex/open_filex.dart';
import 'package:path_provider/path_provider.dart';

import '../../../core/network/api_client.dart';

/// Acceso a la API del historial de compras del cliente (CU-12).
class VentasRepository {
  VentasRepository(this._api, {Future<Directory> Function()? carpetaTemporal}) : _carpetaTemporal = carpetaTemporal ?? getTemporaryDirectory;

  final ApiClient _api;
  final Future<Directory> Function() _carpetaTemporal;

  Future<List<Map<String, dynamic>>> compras() async {
    final r = await _api.get('/compras');
    return (r['compras'] as List).cast<Map<String, dynamic>>();
  }

  Future<Map<String, dynamic>> detalle(int pedidoId) => _api.get('/compras/$pedidoId');

  /// Descarga el comprobante PDF a la carpeta temporal y devuelve la ruta del archivo.
  Future<String> descargarComprobante(int pedidoId, String numero) async {
    final archivo = await _api.descargar('/compras/$pedidoId/comprobante');
    final nombre = (archivo.nombre ?? 'comprobante-$numero.pdf').replaceAll(RegExp(r'[\/:*?"<>|]'), '_');
    final ruta = '${(await _carpetaTemporal()).path}${Platform.pathSeparator}$nombre';
    await File(ruta).writeAsBytes(archivo.bytes);
    return ruta;
  }
}

/// Abre un archivo con la aplicación del teléfono. Devuelve false si no hay ninguna que lo pueda abrir (por ejemplo, un visor de PDF).
Future<bool> abrirConVisor(String ruta) async => (await OpenFilex.open(ruta)).type == ResultType.done;
