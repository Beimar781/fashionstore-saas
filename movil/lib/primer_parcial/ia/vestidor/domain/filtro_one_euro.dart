import 'dart:math' as math;

import 'cuerpo.dart';

/// Filtro One Euro: suaviza mucho cuando el punto casi no se mueve (sin temblor) y casi nada cuando se mueve rápido (sin retraso).
/// Es la única capa de suavizado: con un detector rápido no hace falta una segunda mezcla.
class FiltroOneEuro {
  FiltroOneEuro({this.frecuenciaMinima = 1.35, this.beta = 0.02, this.frecuenciaDerivada = 1.0});

  final double frecuenciaMinima;
  final double beta;
  final double frecuenciaDerivada;

  double? _previo;
  double _derivadaPrevia = 0;
  double? _instantePrevio;

  static double _alfa(double frecuenciaCorte, double dt) {
    final tau = 1 / (2 * math.pi * frecuenciaCorte);
    return 1 / (1 + tau / dt);
  }

  /// `instante` en segundos. Devuelve el valor suavizado.
  double filtrar(double valor, double instante) {
    final previo = _previo;
    final instantePrevio = _instantePrevio;
    if (previo == null || instantePrevio == null || instante <= instantePrevio) {
      _previo = valor;
      _instantePrevio = instante;
      return valor;
    }
    final dt = instante - instantePrevio;
    final derivada = (valor - previo) / dt;
    final derivadaSuave = _derivadaPrevia + _alfa(frecuenciaDerivada, dt) * (derivada - _derivadaPrevia);
    final corte = frecuenciaMinima + beta * derivadaSuave.abs();
    final suave = previo + _alfa(corte, dt) * (valor - previo);
    _previo = suave;
    _derivadaPrevia = derivadaSuave;
    _instantePrevio = instante;
    return suave;
  }

  void reiniciar() {
    _previo = null;
    _instantePrevio = null;
    _derivadaPrevia = 0;
  }
}

/// Suaviza los cuatro puntos del cuerpo (x e y de cada uno).
class FiltroPose {
  final List<FiltroOneEuro> _x = List.generate(4, (_) => FiltroOneEuro());
  final List<FiltroOneEuro> _y = List.generate(4, (_) => FiltroOneEuro());

  PoseCuerpo filtrar(PoseCuerpo pose, double instante) =>
      pose.transformar((i, p) => PuntoCuerpo(_x[i].filtrar(p.x, instante), _y[i].filtrar(p.y, instante), p.confianza));

  void reiniciar() {
    for (final f in [..._x, ..._y]) {
      f.reiniciar();
    }
  }
}
