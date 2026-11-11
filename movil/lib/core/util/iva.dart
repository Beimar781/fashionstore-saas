/// IVA que ya viene incluido en el precio. Misma fórmula que el servidor (`iva_incluido` de backend/app/core/tipos.py):
/// total × porcentaje ÷ (100 + porcentaje), con redondeo medio hacia arriba al céntimo. Se trabaja en enteros para no perder céntimos.
const ivaPorcentajePorDefecto = 13;

String ivaIncluido(Object? total, [int porcentaje = ivaPorcentajePorDefecto]) {
  final centimos = ((double.tryParse('$total') ?? 0) * 100).round();
  final divisor = 100 + porcentaje;
  final iva = (centimos * porcentaje * 2 + divisor) ~/ (divisor * 2);
  return (iva / 100).toStringAsFixed(2);
}
