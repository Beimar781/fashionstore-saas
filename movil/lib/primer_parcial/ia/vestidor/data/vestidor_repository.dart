import 'dart:typed_data';

import 'package:http/http.dart' as http;

import '../../../../core/config/api_config.dart';
import '../../../../core/network/api_client.dart';
import '../domain/anclaje.dart';

/// Un color de la prenda con su imagen para el vestidor.
class ColorVestidor {
  ColorVestidor({required this.id, required this.nombre, required this.codigoHex, required this.imagenUrl, required this.anclaje, this.ancho, this.alto});

  factory ColorVestidor.desdeJson(Map<String, dynamic> j) => ColorVestidor(
        id: j['color_id'] as int,
        nombre: j['color'] as String,
        codigoHex: j['codigo_hex'] as String,
        imagenUrl: j['imagen_url'] as String?,
        ancho: j['ancho'] as int?,
        alto: j['alto'] as int?,
        anclaje: j['anclaje'] == null ? null : Anclaje.desdeJson(j['anclaje'] as Map<String, dynamic>),
      );

  final int id;
  final String nombre;
  final String codigoHex;
  final String? imagenUrl;
  final Anclaje? anclaje;
  final int? ancho;
  final int? alto;

  bool get listo => imagenUrl != null && anclaje != null && ancho != null && alto != null && alto! > 0;

  /// ancho / alto del PNG
  double get proporcion => listo ? ancho! / alto! : 1.0;
}

/// Lo que el móvil necesita para probarse una prenda (CU-06).
class VestidorProducto {
  VestidorProducto({required this.admite, required this.mensaje, required this.colores, required this.escalaTallas});

  factory VestidorProducto.desdeJson(Map<String, dynamic> j) => VestidorProducto(
        admite: j['admite'] as bool,
        mensaje: j['mensaje'] as String?,
        colores: [for (final c in (j['colores'] as List).cast<Map<String, dynamic>>()) ColorVestidor.desdeJson(c)],
        escalaTallas: {for (final e in (j['escala_tallas'] as Map<String, dynamic>).entries) e.key: (e.value as num).toDouble()},
      );

  final bool admite;
  final String? mensaje;
  final List<ColorVestidor> colores;
  final Map<String, double> escalaTallas;

  /// Escala de una talla por su código; las que no figuran (numéricas u otras) usan 1.0.
  double escalaDe(String talla) => escalaTallas[talla.trim().toUpperCase()] ?? escalaTallas[talla] ?? 1.0;
}

/// Acceso al vestidor: la información de la prenda y su PNG, con caché para que la prenda esté lista al abrir la cámara.
class VestidorRepository {
  VestidorRepository(this._api, {Future<Uint8List> Function(Uri)? descargar}) : _descargar = descargar ?? _descargarPorHttp;

  final ApiClient _api;
  final Future<Uint8List> Function(Uri) _descargar;
  final Map<int, VestidorProducto> _productos = {};
  final Map<String, Uint8List> _imagenes = {};

  static Future<Uint8List> _descargarPorHttp(Uri uri) async {
    final r = await http.get(uri).timeout(const Duration(seconds: 15));
    if (r.statusCode != 200) throw ApiException('No se pudo descargar la imagen de la prenda.', statusCode: r.statusCode);
    return r.bodyBytes;
  }

  /// Las imágenes están en la raíz del servidor (`/media/...`), no bajo `/api`.
  static Uri urlDeImagen(String ruta) => Uri.parse(ApiConfig.baseUrl.replaceFirst(RegExp(r'/api/?$'), '') + ruta);

  Future<VestidorProducto> producto(int productoId, {bool forzar = false}) async {
    if (!forzar && _productos.containsKey(productoId)) return _productos[productoId]!;
    final p = VestidorProducto.desdeJson(await _api.get('/vestidor/productos/$productoId'));
    return _productos[productoId] = p;
  }

  Future<Uint8List> imagen(String ruta) async => _imagenes[ruta] ??= await _descargar(urlDeImagen(ruta));

  /// Se llama al abrir la ficha del producto: deja en memoria la información y los PNG para que el vestidor muestre la prenda de inmediato. Nunca falla.
  Future<void> precargar(int productoId) async {
    try {
      final p = await producto(productoId);
      for (final c in p.colores.where((c) => c.listo)) {
        await imagen(c.imagenUrl!);
      }
    } catch (_) {}
  }
}
