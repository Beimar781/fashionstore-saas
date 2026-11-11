import 'modelos.dart';

/// Frase clara para una operación que todavía no se confirmó (en vez de «REGISTRADA_LOCAL» o «Compra local c20069dd»).
String estadoLegible(OperacionLocal o) {
  if (o.estado == Estado.enviada) return 'Enviando al servidor…';
  final tarjeta = RegExp(r'se cobrará a (.+?) terminada en (\d{4})').firstMatch(o.resumen);
  if (o.tipo == 'COMPRA') {
    return tarjeta != null ? 'Pendiente de enviar · se cobrará a la ${tarjeta.group(1)} ${tarjeta.group(2)} al reconectar' : 'Pendiente de enviar · quedará por pagar al reconectar';
  }
  return 'Pendiente de enviar · se enviará al reconectar';
}
