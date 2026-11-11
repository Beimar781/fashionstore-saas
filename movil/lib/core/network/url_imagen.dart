import '../config/api_config.dart';

/// La API devuelve rutas bajo `/media`; las imágenes se sirven desde el origen sin `/api`.
String? urlImagen(String? ruta) {
  if (ruta == null || ruta.trim().isEmpty) return null;
  if (ruta.startsWith('http://') || ruta.startsWith('https://')) return ruta;
  final origen = ApiConfig.baseUrl.replaceFirst(RegExp(r'/api/?$'), '');
  // el catálogo descargado trae la ruta guardada en la base («1/productos/…»); la API normal ya trae «/media/…»
  final conMedia = ruta.startsWith('/media/') ? ruta : '/media/${ruta.startsWith('/') ? ruta.substring(1) : ruta}';
  return '$origen$conMedia';
}
