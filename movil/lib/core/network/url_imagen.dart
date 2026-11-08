import '../config/api_config.dart';

/// La API devuelve rutas bajo `/media`; las imágenes se sirven desde el origen sin `/api`.
String? urlImagen(String? ruta) {
  if (ruta == null || ruta.trim().isEmpty) return null;
  if (ruta.startsWith('http://') || ruta.startsWith('https://')) return ruta;
  final origen = ApiConfig.baseUrl.replaceFirst(RegExp(r'/api/?$'), '');
  return '$origen${ruta.startsWith('/') ? ruta : '/$ruta'}';
}
