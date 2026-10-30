import 'package:fashionstore_movil/primer_parcial/ia/vestidor/presentation/contador_fps.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('Contador de FPS: 60 cuadros por segundo dan FPS actual y promedio cercanos a 60', () {
    final m = MedidorFps();
    for (var i = 0; i < 180; i++) {
      m.registrar(i * 16667);
    }
    expect(m.actual, closeTo(60, 1));
    expect(m.promedio, closeTo(60, 1));
  });

  test('Contador de FPS: el actual mira solo el último segundo y el promedio todo el recorrido', () {
    final m = MedidorFps();
    for (var i = 0; i < 60; i++) {
      m.registrar(i * 16667); // 1 s a 60 FPS
    }
    const inicio = 60 * 16667;
    for (var i = 0; i < 31; i++) {
      m.registrar(inicio + i * 33333); // luego 1 s a 30 FPS
    }
    expect(m.actual, closeTo(30, 1));
    expect(m.promedio, closeTo(45, 2));
  });

  test('Contador de FPS: sin cuadros suficientes marca 0 en lugar de fallar', () {
    final m = MedidorFps();
    expect(m.actual, 0);
    expect(m.promedio, 0);
    m.registrar(1000);
    expect(m.actual, 0);
    expect(m.promedio, 0);
  });
}
