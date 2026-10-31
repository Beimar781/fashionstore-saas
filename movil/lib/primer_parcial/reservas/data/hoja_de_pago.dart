import 'package:flutter_stripe/flutter_stripe.dart';

enum EstadoHoja { completada, cancelada, fallida, error }

class ResultadoHoja {
  const ResultadoHoja(this.estado, [this.motivo = '']);

  final EstadoHoja estado;
  final String motivo;
}

/// La hoja de pago donde el cliente escribe su tarjeta. Es una interfaz para poder probar el flujo del pago con un doble en memoria, sin Stripe real.
abstract class HojaDePago {
  Future<ResultadoHoja> mostrar({required String clavePublica, required String claveSecreta});
}

/// Payment Sheet de Stripe (modo prueba). El número de la tarjeta lo captura Stripe: nuestro código y nuestro servidor nunca lo ven, igual que en la web.
/// Stripe se encarga también de la autenticación 3D Secure.
class HojaDePagoStripe implements HojaDePago {
  @override
  Future<ResultadoHoja> mostrar({required String clavePublica, required String claveSecreta}) async {
    try {
      Stripe.publishableKey = clavePublica; // la clave pública la entrega el backend; no está escrita en el código
      await Stripe.instance.applySettings();
      await Stripe.instance.initPaymentSheet(
        paymentSheetParameters: SetupPaymentSheetParameters(paymentIntentClientSecret: claveSecreta, merchantDisplayName: 'FashionStore'),
      );
      await Stripe.instance.presentPaymentSheet();
      return const ResultadoHoja(EstadoHoja.completada);
    } on StripeException catch (e) {
      if (e.error.code == FailureCode.Canceled) return const ResultadoHoja(EstadoHoja.cancelada);
      return ResultadoHoja(EstadoHoja.fallida, e.error.localizedMessage ?? e.error.message ?? '');
    } catch (_) {
      return const ResultadoHoja(EstadoHoja.error, 'No se pudo abrir la hoja de pago. Intente nuevamente.');
    }
  }
}
