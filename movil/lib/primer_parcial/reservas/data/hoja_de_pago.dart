import 'package:flutter_stripe/flutter_stripe.dart';

enum EstadoHoja { completada, cancelada, fallida, error }

class ResultadoHoja {
  const ResultadoHoja(this.estado, [this.motivo = '']);

  final EstadoHoja estado;
  final String motivo;
}

/// Donde el cliente paga con tarjeta. Es una interfaz para poder probar el flujo del pago con un doble en memoria, sin Stripe real.
abstract class HojaDePago {
  /// Tarjeta nueva: muestra la hoja de pago de Stripe, donde el cliente escribe los datos.
  Future<ResultadoHoja> mostrar({required String clavePublica, required String claveSecreta});

  /// Tarjeta guardada: el servidor ya dejó el método de pago en el intento, así que Stripe solo lo confirma (y pide 3D Secure si hace falta).
  Future<ResultadoHoja> confirmarGuardada({required String clavePublica, required String claveSecreta});
}

/// Stripe en modo prueba. El número de la tarjeta lo captura Stripe: nuestro código y nuestro servidor nunca lo ven, igual que en la web.
/// Stripe se encarga también de la autenticación 3D Secure.
class HojaDePagoStripe implements HojaDePago {
  @override
  Future<ResultadoHoja> mostrar({required String clavePublica, required String claveSecreta}) => _con(clavePublica, () async {
        await Stripe.instance.initPaymentSheet(
          paymentSheetParameters: SetupPaymentSheetParameters(paymentIntentClientSecret: claveSecreta, merchantDisplayName: 'FashionStore'),
        );
        await Stripe.instance.presentPaymentSheet();
      });

  @override
  Future<ResultadoHoja> confirmarGuardada({required String clavePublica, required String claveSecreta}) =>
      _con(clavePublica, () => Stripe.instance.confirmPayment(paymentIntentClientSecret: claveSecreta));

  Future<ResultadoHoja> _con(String clavePublica, Future<void> Function() accion) async {
    try {
      Stripe.publishableKey = clavePublica; // la clave pública la entrega el backend; no está escrita en el código
      await Stripe.instance.applySettings();
      await accion();
      return const ResultadoHoja(EstadoHoja.completada);
    } on StripeException catch (e) {
      if (e.error.code == FailureCode.Canceled) return const ResultadoHoja(EstadoHoja.cancelada);
      return ResultadoHoja(EstadoHoja.fallida, e.error.localizedMessage ?? e.error.message ?? '');
    } catch (_) {
      return const ResultadoHoja(EstadoHoja.error, 'No se pudo abrir la hoja de pago. Intente nuevamente.');
    }
  }
}
