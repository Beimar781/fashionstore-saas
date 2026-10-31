import '../../../core/network/api_client.dart';
import 'hoja_de_pago.dart';
import 'reservas_repository.dart';

enum TipoPago { aprobado, rechazado, pendiente, cancelado, error }

class ResultadoPagoMovil {
  const ResultadoPagoMovil(this.tipo, this.mensaje, {this.pagoId});

  final TipoPago tipo;
  final String mensaje;

  /// Para volver a preguntar el estado de un pago que quedó pendiente de confirmación.
  final int? pagoId;
}

/// Pago de la compra digital en el móvil (CU-11, CU-32): checkout → iniciar el pago → tarjeta → confirmar. Sigue los mismos pasos y textos que la web.
/// Con Stripe la tarjeta se escribe en la hoja de pago de Stripe; con la pasarela simulada (sin claves en el backend) se usa la tarjeta de prueba.
class PagoMovil {
  PagoMovil(this._repo, this._hoja);

  final ReservasRepository _repo;
  final HojaDePago _hoja;

  /// `pedirTarjeta` solo se usa con la pasarela simulada: muestra el formulario de la tarjeta de prueba (null si el cliente cancela).
  Future<ResultadoPagoMovil> pagar({required Future<Map<String, dynamic>?> Function(String monto) pedirTarjeta}) async {
    try {
      final pedido = await _repo.checkout();
      final pago = await _repo.iniciarPago(pedido['id'] as int);
      final pendiente = ResultadoPagoMovil(TipoPago.cancelado, 'El pedido ${pedido['codigo']} quedó pendiente de pago.');
      if (pago['modo'] == 'stripe') {
        final hoja = await _hoja.mostrar(clavePublica: pago['publishable_key'] as String, claveSecreta: pago['client_secret'] as String);
        if (hoja.estado == EstadoHoja.cancelada) return pendiente;
        if (hoja.estado == EstadoHoja.error) return ResultadoPagoMovil(TipoPago.error, hoja.motivo);
        return await _confirmar(pago['pago_id'] as int, null, motivoStripe: hoja.motivo);
      }
      final tarjeta = await pedirTarjeta(pago['monto'] as String);
      if (tarjeta == null) return pendiente;
      return await _confirmar(pago['pago_id'] as int, tarjeta);
    } on ApiException catch (e) {
      return ResultadoPagoMovil(TipoPago.error, e.mensaje);
    }
  }

  /// Pago pendiente de confirmación (la pasarela no respondió): se vuelve a preguntar su estado.
  Future<ResultadoPagoMovil> verificar(int pagoId) async {
    try {
      return _desdeRespuesta(await _repo.reconciliarPago(pagoId));
    } on ApiException catch (e) {
      return _desdeError(e, '');
    }
  }

  Future<ResultadoPagoMovil> _confirmar(int pagoId, Map<String, dynamic>? tarjeta, {String motivoStripe = ''}) async {
    try {
      return _desdeRespuesta(await _repo.confirmarPago(pagoId, tarjeta));
    } on ApiException catch (e) {
      return _desdeError(e, motivoStripe);
    }
  }

  ResultadoPagoMovil _desdeRespuesta(Map<String, dynamic> r) {
    if (r['aprobado'] == true) {
      final pago = r['pago'] as Map<String, dynamic>;
      final comprobante = (r['pedido'] as Map<String, dynamic>)['comprobante_numero'];
      return ResultadoPagoMovil(TipoPago.aprobado, '✔ Pago aprobado\n${pago['tarjeta_marca']} terminada en ${pago['tarjeta_ultimos4']} · Comprobante N.° $comprobante');
    }
    return ResultadoPagoMovil(TipoPago.pendiente, '⏳ Pendiente de confirmación\n${r['mensaje']}', pagoId: (r['pago'] as Map<String, dynamic>)['id'] as int);
  }

  /// 402 = la pasarela rechazó la tarjeta; el resto de los errores (sin stock 409, sin conexión...) llegan con su mensaje.
  ResultadoPagoMovil _desdeError(ApiException e, String motivoStripe) {
    if (e.statusCode != 402) return ResultadoPagoMovil(TipoPago.error, e.mensaje);
    final motivo = motivoStripe.isNotEmpty ? motivoStripe : e.motivo;
    return ResultadoPagoMovil(
      TipoPago.rechazado,
      '✖ Pago rechazado\n${e.mensaje}${motivo.isEmpty ? '' : '\nMotivo: $motivo'}\nNo se cobró nada. Pruebe con otra tarjeta.',
    );
  }
}
