import 'package:fashionstore_movil/core/config/api_config.dart';
import 'package:fashionstore_movil/core/network/imagen_prenda.dart';
import 'package:fashionstore_movil/core/network/url_imagen.dart';
import 'package:fashionstore_movil/core/ui/area_segura.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('Imágenes del catálogo', () {
    test('resuelve rutas /media desde el origen sin /api', () {
      final origen = ApiConfig.baseUrl.replaceFirst(RegExp(r'/api/?$'), '');
      expect(urlImagen('/media/prendas/1.png'), '$origen/media/prendas/1.png');
    });

    test('el catálogo descargado trae la ruta de la base y se completa con /media', () {
      final origen = ApiConfig.baseUrl.replaceFirst(RegExp(r'/api/?$'), '');
      expect(urlImagen('2/productos/5/abc.jpg'), '$origen/media/2/productos/5/abc.jpg');
      expect(urlImagen('https://cdn.ejemplo.com/a.jpg'), 'https://cdn.ejemplo.com/a.jpg');
    });

    test('devuelve nulo cuando la prenda no tiene imagen', () {
      expect(urlImagen(null), isNull);
      expect(urlImagen('  '), isNull);
    });

    testWidgets('usa el marcador cuando no hay ruta de imagen', (tester) async {
      await tester.pumpWidget(const MaterialApp(
        home: Scaffold(
            body: SizedBox(
                width: 100, height: 120, child: ImagenPrenda(ruta: null))),
      ));

      expect(find.byIcon(Icons.checkroom), findsOneWidget);
    });

    testWidgets('reserva el margen inferior de la barra de tres botones',
        (tester) async {
      const control = Key('control-inferior');
      await tester.pumpWidget(MaterialApp(
        builder: (_, child) => MediaQuery(
          data: const MediaQueryData(
              size: Size(360, 800),
              padding: EdgeInsets.only(bottom: 48),
              viewPadding: EdgeInsets.only(bottom: 48)),
          child: AreaSeguraAplicacion(child: child!),
        ),
        home: const Scaffold(
            body: Align(
                alignment: Alignment.bottomCenter,
                child: SizedBox(key: control, height: 40, width: 120))),
      ));

      expect(
          tester.getBottomLeft(find.byKey(control)).dy, lessThanOrEqualTo(752));
    });
  });
}
