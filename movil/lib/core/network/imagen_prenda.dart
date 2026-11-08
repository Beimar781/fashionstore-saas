import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:flutter_cache_manager/flutter_cache_manager.dart';

import 'url_imagen.dart';

/// Imagen con caché en disco; si la ruta falta o la descarga falla, muestra un marcador.
class ImagenPrenda extends StatelessWidget {
  const ImagenPrenda({super.key, required this.ruta, this.fit = BoxFit.cover});

  final String? ruta;
  final BoxFit fit;

  @override
  Widget build(BuildContext context) {
    final url = urlImagen(ruta);
    if (url == null) return const _MarcadorPrenda();
    return CachedNetworkImage(
      imageUrl: url,
      fit: fit,
      placeholder: (_, __) => const _MarcadorPrenda(cargando: true),
      errorWidget: (_, __, ___) => const _MarcadorPrenda(),
    );
  }
}

/// Descarga también las fotos que el Cliente todavía no abrió, para que estén disponibles offline.
Future<void> precalentarImagenes(Iterable<String?> rutas) async {
  final cache = DefaultCacheManager();
  for (final ruta in rutas.whereType<String>().where((r) => r.isNotEmpty)) {
    final url = urlImagen(ruta);
    if (url == null) continue;
    try {
      await cache.downloadFile(url);
    } catch (_) {
      // Una imagen que falla no cancela la descarga del resto del catálogo.
    }
  }
}

class _MarcadorPrenda extends StatelessWidget {
  const _MarcadorPrenda({this.cargando = false});
  final bool cargando;

  @override
  Widget build(BuildContext context) => Container(
        color: Theme.of(context).colorScheme.surfaceContainerHighest,
        alignment: Alignment.center,
        child: Icon(Icons.checkroom,
            size: cargando ? 30 : 34,
            color: Theme.of(context).colorScheme.outline),
      );
}
