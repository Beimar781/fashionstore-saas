import 'package:fashionstore_movil/core/network/api_client.dart';
import 'package:fashionstore_movil/primer_parcial/reservas/data/datos_entrega.dart';
import 'package:fashionstore_movil/primer_parcial/reservas/data/reservas_repository.dart';
import 'package:flutter_test/flutter_test.dart';

class ApiFalsa extends ApiClient {
  ApiFalsa() : super(obtenerToken: () async => null, renovarToken: () async => false);

  Map<String, dynamic>? cuerpo;

  @override
  Future<Map<String, dynamic>> post(String ruta, Map<String, dynamic> cuerpo, {bool autenticado = true}) async {
    this.cuerpo = cuerpo;
    return {'id': 1};
  }
}

void main() {
  test('Retiro con NIT: es válido y se envía sin dirección', () {
    const d = DatosEntrega(nitCi: ' 1234567 ', razonSocial: 'Mi Empresa');
    expect(d.validar(), isNull);
    expect(d.aCuerpo(), {'tipo_entrega': 'RETIRO', 'direccion_entrega': '', 'nit_ci': '1234567', 'razon_social': 'Mi Empresa'});
  });

  test('Domicilio sin dirección: «Ingrese la dirección de entrega.»', () {
    const d = DatosEntrega(domicilio: true, direccion: '   ', nitCi: '1234567');
    expect(d.validar(), 'Ingrese la dirección de entrega.');
  });

  test('Domicilio con dirección: se envía como DELIVERY con la dirección', () {
    const d = DatosEntrega(domicilio: true, direccion: 'Av. Banzer #123', nitCi: '1234567');
    expect(d.validar(), isNull);
    expect(d.aCuerpo()['tipo_entrega'], 'DELIVERY');
    expect(d.aCuerpo()['direccion_entrega'], 'Av. Banzer #123');
  });

  test('NIT vacío o de menos de 3 caracteres: «Ingrese su NIT o CI para la facturación.»', () {
    expect(const DatosEntrega().validar(), 'Ingrese su NIT o CI para la facturación.');
    expect(const DatosEntrega(nitCi: '12').validar(), 'Ingrese su NIT o CI para la facturación.');
  });

  test('El checkout envía al servidor los datos del formulario y no los de siempre', () async {
    final api = ApiFalsa();
    await ReservasRepository(api).checkout(const DatosEntrega(domicilio: true, direccion: 'Calle 1', nitCi: '999', razonSocial: 'ACME'));
    expect(api.cuerpo, {'tipo_entrega': 'DELIVERY', 'direccion_entrega': 'Calle 1', 'nit_ci': '999', 'razon_social': 'ACME'});
  });
}
