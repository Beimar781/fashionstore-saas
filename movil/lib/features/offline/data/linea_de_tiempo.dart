import 'dart:io';

import 'modelos.dart';

/// Un paso de la historia de una operación: qué pasó, cuándo (si se sabe) y de qué tipo (info, ok, warn, danger).
class PasoTiempo {
  const PasoTiempo(this.fecha, this.texto, this.tipo);
  final String? fecha;
  final String texto;
  final String tipo;
}

/// Nombre corto del dispositivo para la línea de tiempo («este teléfono Android»).
String etiquetaDispositivo([String? sistema]) {
  final so = sistema ?? Platform.operatingSystem;
  return switch (so) { 'android' => 'este teléfono Android', 'ios' => 'este iPhone', 'windows' => 'este equipo Windows', 'macos' => 'este equipo Mac', _ => 'este dispositivo' };
}

/// Historia de una operación sin conexión: registrada en este dispositivo → enviada (cada intento, con su resultado) → confirmada, en conflicto o rechazada → resuelta.
/// Sale de lo guardado en el teléfono (la operación y el registro de sincronización), así que se puede ver sin conexión.
List<PasoTiempo> lineaDeTiempo(OperacionLocal o, List<Map<String, Object?>> registro, {String? dispositivo}) {
  final pasos = <PasoTiempo>[PasoTiempo(o.creadoEn, 'Registrada en ${dispositivo ?? etiquetaDispositivo()}', 'info')];
  final intentos = registro.where((r) => r['operacion_id'] == o.id).toList()..sort((a, b) => '${a['fecha']}'.compareTo('${b['fecha']}'));
  for (final i in intentos) {
    final envio = 'Envío ${i['intento']}';
    final motivo = '${i['motivo'] ?? ''}'.isEmpty ? '' : ' — ${i['motivo']}';
    final fecha = '${i['fecha']}';
    switch ('${i['resultado']}') {
      case 'CONFIRMADA':
        pasos.add(PasoTiempo(fecha, '$envio: confirmada por el servidor', 'ok'));
      case 'EN_CONFLICTO':
        pasos.add(PasoTiempo(fecha, '$envio: en conflicto$motivo', 'warn'));
      case 'RECHAZADA':
        pasos.add(PasoTiempo(fecha, '$envio: rechazada$motivo', 'danger'));
      default:
        pasos.add(PasoTiempo(fecha, '$envio: el servidor no respondió (${i['codigo']}); se reintentará', 'warn'));
    }
  }
  final huboConflicto = intentos.any((i) => i['resultado'] == 'EN_CONFLICTO');
  if (huboConflicto && o.estado == Estado.confirmada) {
    pasos.add(const PasoTiempo(null, 'Resuelta por el Encargado: reintentada y confirmada', 'ok'));
  } else if (huboConflicto && o.estado == Estado.rechazada) {
    pasos.add(const PasoTiempo(null, 'Resuelta por el Encargado: descartada', 'danger'));
  } else if (o.pendiente) {
    pasos.add(PasoTiempo(null, o.estado == Estado.enviada ? 'Esperando la respuesta del servidor…' : 'Pendiente: se enviará sola al volver la conexión', 'info'));
  }
  return pasos;
}
