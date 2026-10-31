import 'package:fashionstore_movil/core/network/api_client.dart';
import 'package:fashionstore_movil/primer_parcial/reservas/data/datos_entrega.dart';
import 'package:fashionstore_movil/primer_parcial/reservas/data/hoja_de_pago.dart';
import 'package:fashionstore_movil/primer_parcial/reservas/data/medio_de_pago.dart';
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
  final cuerpos = <String, Map<String, dynamic>>{};
  List<Map<String, dynamic>> tarjetas = [];

  @override
  Future<Map<String, dynamic>> post(String ruta, Map<String, dynamic> cuerpo, {bool autenticado = true}) async {
    llamadas.add(ruta);
    cuerpos[ruta] = cuerpo;
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

  @override
  Future<List<dynamic>> getLista(String ruta) async {
    llamadas.add(ruta);
    return tarjetas;
  }

  @override
  Future<Map<String, dynamic>> delete(String ruta) async {
    llamadas.add('DELETE $ruta');
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
  final usos = <String>[];

  @override
  Future<ResultadoHoja> mostrar({required String clavePublica, required String claveSecreta}) async {
    this.clavePublica = clavePublica;
    this.claveSecreta = claveSecreta;
    usos.add('hoja');
    return resultado;
  }

  @override
  Future<ResultadoHoja> confirmarGuardada({required String clavePublica, required String claveSecreta}) async {
    this.clavePublica = clavePublica;
    this.claveSecreta = claveSecreta;
    usos.add('guardada');
    return resultado;
  }
}

const _datos = DatosEntrega(nitCi: '1234567');

Future<Map<String, dynamic>?> _sinTarjeta(String monto) async => null;
Future<Map<String, dynamic>?> _tarjetaDePrueba(String monto) async => {'numero': '4242 4242 4242 4242', 'mes': 12, 'anio': 2030, 'cvc': '123', 'titular': 'Cliente'};

PagoMovil _flujo(ApiFalsa api, HojaFalsa hoja) => PagoMovil(ReservasRepository(api), hoja);

void main() {
  test('Stripe aprobado: la hoja se abre con la clave del backend, se confirma y se muestra el comprobante', () async {
    final api = ApiFalsa();
    final hoja = HojaFalsa(const ResultadoHoja(EstadoHoja.completada));
    final r = await _flujo(api, hoja).pagar(datos: _datos, pedirTarjeta: _sinTarjeta);
    expect(r.tipo, TipoPago.aprobado);
    expect(r.mensaje, contains('Pago aprobado'));
    expect(r.mensaje, contains('Visa terminada en 4242'));
    expect(r.mensaje, contains('CMP-1-7'));
    expect((hoja.clavePublica, hoja.claveSecreta), ('pk_test_falsa', 'pi_falso_secret'));
    expect(api.llamadas, ['/compras/checkout', '/pagos/pedidos/5/iniciar', '/pagos/9/confirmar']);
  });

  test('Stripe rechazado (402): muestra el motivo del banco y que no se cobró nada', () async {
    final api = ApiFalsa()..falloAlConfirmar = ApiException('Pago rechazado.', statusCode: 402, motivo: 'Transacción denegada por su banco');
    final r = await _flujo(api, HojaFalsa(const ResultadoHoja(EstadoHoja.completada))).pagar(datos: _datos, pedirTarjeta: _sinTarjeta);
    expect(r.tipo, TipoPago.rechazado);
    expect(r.mensaje, contains('Pago rechazado'));
    expect(r.mensaje, contains('Motivo: Transacción denegada por su banco'));
    expect(r.mensaje, contains('No se cobró nada'));
  });

  test('Stripe falló en la hoja: se confirma igual y el motivo de Stripe tiene prioridad', () async {
    final api = ApiFalsa()..falloAlConfirmar = ApiException('Pago rechazado.', statusCode: 402, motivo: 'Transacción denegada por su banco');
    final r = await _flujo(api, HojaFalsa(const ResultadoHoja(EstadoHoja.fallida, 'Su tarjeta fue rechazada.'))).pagar(datos: _datos, pedirTarjeta: _sinTarjeta);
    expect(r.tipo, TipoPago.rechazado);
    expect(r.mensaje, contains('Motivo: Su tarjeta fue rechazada.'));
  });

  test('Stripe cancelado: el pedido queda pendiente de pago, sin confirmar y sin error', () async {
    final api = ApiFalsa();
    final r = await _flujo(api, HojaFalsa(const ResultadoHoja(EstadoHoja.cancelada))).pagar(datos: _datos, pedirTarjeta: _sinTarjeta);
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
    final r = await flujo.pagar(datos: _datos, pedirTarjeta: _sinTarjeta);
    expect(r.tipo, TipoPago.pendiente);
    expect(r.pagoId, 9);
    expect(r.mensaje, contains('Pendiente de confirmación'));
    api.respuestaConfirmar = null;
    expect((await flujo.verificar(r.pagoId!)).tipo, TipoPago.aprobado);
    expect(api.llamadas.last, '/pagos/9/reconciliar');
  });

  test('Si la hoja de pago no se puede abrir se avisa y no se confirma nada', () async {
    final api = ApiFalsa();
    final r = await _flujo(api, HojaFalsa(const ResultadoHoja(EstadoHoja.error, 'No se pudo abrir la hoja de pago. Intente nuevamente.'))).pagar(datos: _datos, pedirTarjeta: _sinTarjeta);
    expect(r.tipo, TipoPago.error);
    expect(api.llamadas.any((l) => l.endsWith('/confirmar')), isFalse);
  });

  test('Sin stock al pagar (409): el mensaje del servidor llega tal cual', () async {
    final api = ApiFalsa()..falloAlConfirmar = ApiException('La prenda se agotó.', statusCode: 409);
    final r = await _flujo(api, HojaFalsa(const ResultadoHoja(EstadoHoja.completada))).pagar(datos: _datos, pedirTarjeta: _sinTarjeta);
    expect((r.tipo, r.mensaje), (TipoPago.error, 'La prenda se agotó.'));
  });

  test('Modo simulado: sigue pidiendo la tarjeta de prueba y no abre la hoja de Stripe', () async {
    final api = ApiFalsa()..modo = 'simulado';
    final hoja = HojaFalsa(const ResultadoHoja(EstadoHoja.completada));
    final r = await _flujo(api, hoja).pagar(datos: _datos, pedirTarjeta: _tarjetaDePrueba);
    expect(r.tipo, TipoPago.aprobado);
    expect(hoja.clavePublica, isNull);
  });

  test('Modo simulado: si el cliente cierra el formulario, el pedido queda pendiente de pago', () async {
    final api = ApiFalsa()..modo = 'simulado';
    final r = await _flujo(api, HojaFalsa(const ResultadoHoja(EstadoHoja.completada))).pagar(datos: _datos, pedirTarjeta: _sinTarjeta);
    expect(r.tipo, TipoPago.cancelado);
  });

  test('Tarjeta nueva con «Guardar»: el servidor recibe guardar_tarjeta y se abre la hoja de Stripe', () async {
    final api = ApiFalsa();
    final hoja = HojaFalsa(const ResultadoHoja(EstadoHoja.completada));
    final r = await _flujo(api, hoja).pagar(datos: _datos, medio: const MedioDePago(guardar: true), pedirTarjeta: _sinTarjeta);
    expect(r.tipo, TipoPago.aprobado);
    expect(api.cuerpos['/pagos/pedidos/5/iniciar'], {'tarjeta_guardada_id': null, 'guardar_tarjeta': true});
    expect(hoja.usos, ['hoja']);
  });

  test('Sin marcar «Guardar» no se guarda nada', () async {
    final api = ApiFalsa();
    await _flujo(api, HojaFalsa(const ResultadoHoja(EstadoHoja.completada))).pagar(datos: _datos, pedirTarjeta: _sinTarjeta);
    expect(api.cuerpos['/pagos/pedidos/5/iniciar'], {'tarjeta_guardada_id': null, 'guardar_tarjeta': false});
  });

  test('Tarjeta guardada con Stripe: se envía su id y solo se confirma, sin abrir la hoja de pago', () async {
    final api = ApiFalsa();
    final hoja = HojaFalsa(const ResultadoHoja(EstadoHoja.completada));
    final r = await _flujo(api, hoja).pagar(datos: _datos, medio: const MedioDePago(tarjetaGuardadaId: 4, guardar: true), pedirTarjeta: _sinTarjeta);
    expect(r.tipo, TipoPago.aprobado);
    expect(api.cuerpos['/pagos/pedidos/5/iniciar'], {'tarjeta_guardada_id': 4, 'guardar_tarjeta': false}); // una tarjeta ya guardada no se vuelve a guardar
    expect(hoja.usos, ['guardada']);
    expect(api.llamadas.last, '/pagos/9/confirmar');
  });

  test('Tarjeta guardada rechazada por el banco: se muestra el rechazo', () async {
    final api = ApiFalsa()..falloAlConfirmar = ApiException('Pago rechazado.', statusCode: 402, motivo: 'Transacción denegada por su banco');
    final r = await _flujo(api, HojaFalsa(const ResultadoHoja(EstadoHoja.fallida, ''))).pagar(datos: _datos, medio: const MedioDePago(tarjetaGuardadaId: 4), pedirTarjeta: _sinTarjeta);
    expect(r.tipo, TipoPago.rechazado);
    expect(r.mensaje, contains('Motivo: Transacción denegada por su banco'));
  });

  test('Modo simulado con tarjeta guardada: no pide la tarjeta y confirma con la guardada', () async {
    final api = ApiFalsa()..modo = 'simulado';
    var pidioTarjeta = false;
    final r = await _flujo(api, HojaFalsa(const ResultadoHoja(EstadoHoja.completada))).pagar(
      datos: _datos,
      medio: const MedioDePago(tarjetaGuardadaId: 4),
      pedirTarjeta: (_) async {
        pidioTarjeta = true;
        return null;
      },
    );
    expect(r.tipo, TipoPago.aprobado);
    expect(pidioTarjeta, isFalse);
    expect(api.cuerpos['/pagos/9/confirmar'], {'tarjeta': null});
  });

  test('Las tarjetas guardadas se listan y se eliminan con los mismos endpoints de la web', () async {
    final api = ApiFalsa()
      ..tarjetas = [
        {'id': 4, 'marca': 'Visa', 'ultimos4': '4242', 'exp_mes': 12, 'exp_anio': 2030}
      ];
    final repo = ReservasRepository(api);
    final lista = await repo.tarjetasGuardadas();
    expect(lista.single.descripcion, 'Visa terminada en 4242 · vence 12/2030');
    await repo.eliminarTarjeta(4);
    expect(api.llamadas, ['/pagos/tarjetas', 'DELETE /pagos/tarjetas/4']);
  });
}
