import 'dart:io';

import 'package:fashionstore_movil/core/network/api_client.dart';
import 'package:fashionstore_movil/primer_parcial/ventas/data/comprobante_movil.dart';
import 'package:fashionstore_movil/primer_parcial/ventas/data/ventas_repository.dart';
import 'package:flutter_test/flutter_test.dart';

/// Doble en memoria del servidor: devuelve el archivo preparado o lanza el error preparado.
class ApiFalsa extends ApiClient {
  ApiFalsa() : super(obtenerToken: () async => null, renovarToken: () async => false);

  ArchivoDescargado? archivo;
  ApiException? fallo;
  String? rutaPedida;

  @override
  Future<ArchivoDescargado> descargar(String ruta, {bool reintento = false}) async {
    rutaPedida = ruta;
    if (fallo != null) throw fallo!;
    return archivo!;
  }
}

void main() {
  late Directory carpeta;
  late ApiFalsa api;
  late List<String> abiertos;

  setUp(() async {
    carpeta = await Directory.systemTemp.createTemp('comprobantes');
    api = ApiFalsa();
    abiertos = [];
  });

  tearDown(() => carpeta.delete(recursive: true));

  ComprobanteMovil flujo({bool hayVisor = true}) => ComprobanteMovil(
        VentasRepository(api, carpetaTemporal: () async => carpeta),
        abrir: (ruta) async {
          abiertos.add(ruta);
          return hayVisor;
        },
      );

  test('Descarga correcta: guarda el PDF con el nombre que da el servidor y lo abre', () async {
    api.archivo = ArchivoDescargado([37, 80, 68, 70], 'CMP-001-000007.pdf');
    expect(await flujo().ver(7, 'CMP-001-000007'), isNull);
    expect(api.rutaPedida, '/compras/7/comprobante');
    expect(abiertos, hasLength(1));
    expect(abiertos.single.endsWith('CMP-001-000007.pdf'), isTrue);
    expect(await File(abiertos.single).readAsBytes(), [37, 80, 68, 70]);
  });

  test('Sin nombre del servidor se usa comprobante-<numero>.pdf', () async {
    api.archivo = ArchivoDescargado([1, 2, 3], null);
    await flujo().ver(7, 'CMP-001-000007');
    expect(abiertos.single.endsWith('comprobante-CMP-001-000007.pdf'), isTrue);
  });

  test('Un nombre con rutas o caracteres raros no puede salir de la carpeta temporal', () async {
    api.archivo = ArchivoDescargado([1], '../../malo.pdf');
    await flujo().ver(7, 'X');
    expect(File(abiertos.single).parent.path, carpeta.path);
  });

  test('Sin conexión: mensaje en español y no se abre nada', () async {
    api.fallo = ApiException('Sin conexión con el servidor.', sinConexion: true);
    expect(await flujo().ver(7, 'X'), 'Sin conexión: no se puede descargar el comprobante. Inténtelo de nuevo cuando tenga red.');
    expect(abiertos, isEmpty);
  });

  test('404 o 403: «No se encontró el comprobante de esta compra.» y no se abre nada', () async {
    for (final codigo in [404, 403]) {
      api.fallo = ApiException('No se pudo descargar el archivo.', statusCode: codigo);
      expect(await flujo().ver(7, 'X'), 'No se encontró el comprobante de esta compra.');
    }
    expect(abiertos, isEmpty);
  });

  test('Sin visor de PDF en el teléfono: mensaje claro', () async {
    api.archivo = ArchivoDescargado([1], 'a.pdf');
    expect(await flujo(hayVisor: false).ver(7, 'X'), 'No hay una aplicación para abrir PDF en este teléfono.');
  });
}
