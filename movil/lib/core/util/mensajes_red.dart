import '../network/api_client.dart';

const msgSinRedGuardado = 'No hay conexión, se guardó en este teléfono.';
const msgSinRedNecesita = 'Esta función necesita Internet.';
const msgServidorNoRespondio = 'El servidor no respondió, reintentamos solos.';
const msgErrorGeneral = 'No se pudo completar la acción. Intente de nuevo.';

/// Texto para mostrar al usuario ante cualquier error: nunca códigos HTTP ni nombres de excepciones.
/// `guardado` indica que lo pedido ya quedó en el teléfono para enviarse al volver la red.
String mensajeAmigable(Object error, {bool guardado = false}) {
  if (error is ApiException) {
    if (error.sinConexion) return guardado ? msgSinRedGuardado : msgSinRedNecesita;
    final codigo = error.statusCode ?? 0;
    if (codigo >= 500) return msgServidorNoRespondio;
    return _limpio(error.mensaje) ?? msgErrorGeneral;
  }
  return _limpio('$error') ?? msgErrorGeneral;
}

/// Un texto del servidor ya viene en español para el usuario; lo técnico (Exception, StatusCode, trazas) se descarta.
String? _limpio(String texto) {
  final t = texto.replaceFirst('Exception: ', '').trim();
  final tecnico = RegExp(r'(Exception|Error:|StatusCode|Traceback|SocketException|HttpException|\bnull\b|^\d{3}\b)', caseSensitive: false);
  return t.isEmpty || tecnico.hasMatch(t) ? null : t;
}
