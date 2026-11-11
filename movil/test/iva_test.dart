import 'package:fashionstore_movil/core/util/iva.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  // misma tabla que backend/tests/test_f_iva_y_catalogo.py y frontend/src/app/core/iva.spec.ts (la calcula el servidor)
  const tabla = {'0.00': '0.00', '0.50': '0.06', '1.00': '0.12', '9.99': '1.15', '100.00': '11.50', '235.00': '27.04', '300.00': '34.51', '1250.50': '143.86', '8.69': '1.00', '4.35': '0.50'};

  test('IVA incluido sin conexión: coincide con el servidor al céntimo', () {
    tabla.forEach((total, esperado) => expect(ivaIncluido(total), esperado, reason: total));
    expect(ivaIncluido(300.0), '34.51');
  });

  test('usa la tasa descargada y 13 % si no hay', () {
    expect(ivaIncluido('113.00'), '13.00');
    expect(ivaIncluido('120.00', 20), '20.00');
  });
}
