import 'package:fashionstore_movil/core/network/api_client.dart';
import 'package:fashionstore_movil/primer_parcial/reservas/data/hoja_de_pago.dart';
import 'package:fashionstore_movil/primer_parcial/reservas/data/pago_movil.dart';
import 'package:fashionstore_movil/primer_parcial/reservas/data/reservas_repository.dart';
import 'package:flutter_test/flutter_test.dart';

/// Doble en memoria del backend: guarda las rutas llamadas y responde lo que cada prueba prepare.
class ApiFalsa extends ApiClient {
  ApiFalsa() : super(obtenerToken: () async => null, renovarToken: () async => false);

  String modo = 'stripe';
  ApiException? falloAlConfirmar;
  Map<String, dynamic>? respuestaConfirmar;
  final llamadas = <String>[];

  @override
  Future<Map<String, dynamic>> post(String ruta, Map<String, dynamic> cuerpo, {bool autenticado = true}) async {
    llamadas.add(ruta);
    if (ruta == '/compras/checkout') return {'id': 5, 'codigo': 'PED-5'};
    if (ruta.endsWith('/iniciar')) {
      return {'pago_id': 9, 'modo': modo, 'publishable_key': 'pk_test_falsa', 'client_secret': 'pi_falso_secret', 'monto': '120.00'};
    }
    if (ruta.endsWith('/confirmar') || ruta.endsWith('/reconciliar')) {
      if (falloAlConfirmar != null) throw falloAlConfirmar!;
      return respuestaConfirmar ?? _aprobado;
    }
    return {};
  }

  static final Map<String, dynamic> _aprobado = {
    'aprobado': true,
    'pendiente': false,
    'mensaje': 'Pago aprobado.',
    'pago': {'id': 9, 'tarjeta_marca': 'Visa', 'tarjeta_ultimos4': '4242'},
    'pedido': {'comprobante_numero': 'CMP-1-7'},
  };
}

/// Doble de la hoja de pago de Stripe: devuelve lo que se le indique y guarda con qué claves se abrió.
class HojaFalsa implements HojaDePago {
  HojaFalsa(this.resultado);

  final ResultadoHoja resultado;
  String? clavePublica;
  String? claveSecreta;

  @override
  Future<ResultadoHoja> mostrar({required String clavePublica, required String claveSecreta}) async {
    this.clavePublica = clavePublica;
    this.claveSecreta = claveSecreta;
    return resultado;
  }
}

Future<Map<String, dynamic>?> _sinTarjeta(String monto) async => null;
Future<Map<String, dynamic>?> _tarjetaDePrueba(String monto) async => {'numero': '4242 4242 4242 4242', 'mes': 12, 'anio': 2030, 'cvc': '123', 'titular': 'Cliente'};

PagoMovil _flujo(ApiFalsa api, HojaFalsa hoja) => PagoMovil(ReservasRepository(api), hoja);

void main() {
  test('Stripe aprobado: la hoja se abre con la clave del backend, se confirma y se muestra el comprobante', () async {
    final api = ApiFalsa();
    final hoja = HojaFalsa(const ResultadoHoja(EstadoHoja.completada));
    final r = await _flujo(api, hoja).pagar(pedirTarjeta: _sinTarjeta);
    expect(r.tipo, TipoPago.aprobado);
    expect(r.mensaje, contains('Pago aprobado'));
    expect(r.mensaje, contains('Visa terminada en 4242'));
    expect(r.mensaje, contains('CMP-1-7'));
    expect((hoja.clavePublica, hoja.claveSecreta), ('pk_test_falsa', 'pi_falso_secret'));
    expect(api.llamadas, ['/compras/checkout', '/pagos/pedidos/5/iniciar', '/pagos/9/confirmar']);
  });

  test('Stripe rechazado (402): muestra el motivo del banco y que no se cobró nada', () async {
    final api = ApiFalsa()..falloAlConfirmar = ApiException('Pago rechazado.', statusCode: 402, motivo: 'Transacción denegada por su banco');
    final r = await _flujo(api, HojaFalsa(const ResultadoHoja(EstadoHoja.completada))).pagar(pedirTarjeta: _sinTarjeta);
    expect(r.tipo, TipoPago.rechazado);
    expect(r.mensaje, contains('Pago rechazado'));
    expect(r.mensaje, contains('Motivo: Transacción denegada por su banco'));
    expect(r.mensaje, contains('No se cobró nada'));
  });

  test('Stripe falló en la hoja: se confirma igual y el motivo de Stripe tiene prioridad', () async {
    final api = ApiFalsa()..falloAlConfirmar = ApiException('Pago rechazado.', statusCode: 402, motivo: 'Transacción denegada por su banco');
    final r = await _flujo(api, HojaFalsa(const ResultadoHoja(EstadoHoja.fallida, 'Su tarjeta fue rechazada.'))).pagar(pedirTarjeta: _sinTarjeta);
    expect(r.tipo, TipoPago.rechazado);
    expect(r.mensaje, contains('Motivo: Su tarjeta fue rechazada.'));
  });

  test('Stripe cancelado: el pedido queda pendiente de pago, sin confirmar y sin error', () async {
    final api = ApiFalsa();
    final r = await _flujo(api, HojaFalsa(const ResultadoHoja(EstadoHoja.cancelada))).pagar(pedirTarjeta: _sinTarjeta);
    expect(r.tipo, TipoPago.cancelado);
    expect(r.mensaje, 'El pedido PED-5 quedó pendiente de pago.');
    expect(api.llamadas.any((l) => l.endsWith('/confirmar')), isFalse);
  });

  test('Stripe pendiente de confirmación: ofrece verificar y la verificación posterior aprueba el pago', () async {
    final api = ApiFalsa()
      ..respuestaConfirmar = {
        'aprobado': false,
        'pendiente': true,
        'mensaje': 'Pendiente de confirmación: la pasarela no respondió.',
        'pago': {'id': 9},
        'pedido': {},
      };
    final flujo = _flujo(api, HojaFalsa(const ResultadoHoja(EstadoHoja.completada)));
    final r = await flujo.pagar(pedirTarjeta: _sinTarjeta);
    expect(r.tipo, TipoPago.pendiente);
    expect(r.pagoId, 9);
    expect(r.mensaje, contains('Pendiente de confirmación'));
    api.respuestaConfirmar = null;
    expect((await flujo.verificar(r.pagoId!)).tipo, TipoPago.aprobado);
    expect(api.llamadas.last, '/pagos/9/reconciliar');
  });

  test('Si la hoja de pago no se puede abrir se avisa y no se confirma nada', () async {
    final api = ApiFalsa();
    final r = await _flujo(api, HojaFalsa(const ResultadoHoja(EstadoHoja.error, 'No se pudo abrir la hoja de pago. Intente nuevamente.'))).pagar(pedirTarjeta: _sinTarjeta);
    expect(r.tipo, TipoPago.error);
    expect(api.llamadas.any((l) => l.endsWith('/confirmar')), isFalse);
  });

  test('Sin stock al pagar (409): el mensaje del servidor llega tal cual', () async {
    final api = ApiFalsa()..falloAlConfirmar = ApiException('La prenda se agotó.', statusCode: 409);
    final r = await _flujo(api, HojaFalsa(const ResultadoHoja(EstadoHoja.completada))).pagar(pedirTarjeta: _sinTarjeta);
    expect((r.tipo, r.mensaje), (TipoPago.error, 'La prenda se agotó.'));
  });

  test('Modo simulado: sigue pidiendo la tarjeta de prueba y no abre la hoja de Stripe', () async {
    final api = ApiFalsa()..modo = 'simulado';
    final hoja = HojaFalsa(const ResultadoHoja(EstadoHoja.completada));
    final r = await _flujo(api, hoja).pagar(pedirTarjeta: _tarjetaDePrueba);
    expect(r.tipo, TipoPago.aprobado);
    expect(hoja.clavePublica, isNull);
  });

  test('Modo simulado: si el cliente cierra el formulario, el pedido queda pendiente de pago', () async {
    final api = ApiFalsa()..modo = 'simulado';
    final r = await _flujo(api, HojaFalsa(const ResultadoHoja(EstadoHoja.completada))).pagar(pedirTarjeta: _sinTarjeta);
    expect(r.tipo, TipoPago.cancelado);
  });
}
