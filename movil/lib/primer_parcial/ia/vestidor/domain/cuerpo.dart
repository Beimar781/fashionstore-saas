import 'package:camera/camera.dart';

/// Un punto del cuerpo con coordenadas de 0 a 1 sobre el cuadro tal como se ve en pantalla (ya girado y, con la cámara frontal, ya en espejo).
class PuntoCuerpo {
  const PuntoCuerpo(this.x, this.y, this.confianza);

  final double x;
  final double y;
  final double confianza;

  PuntoCuerpo con({double? x, double? y}) => PuntoCuerpo(x ?? this.x, y ?? this.y, confianza);
}

/// Los cuatro puntos que usa el vestidor (hombros y caderas). Es la interfaz común de los dos planes de detección:
/// el plan A (ML Kit) y el plan B (MoveNet con tflite) solo tienen que llenar esto, y el anclaje no cambia.
class PoseCuerpo {
  const PoseCuerpo({required this.hombroIzq, required this.hombroDer, required this.caderaIzq, required this.caderaDer});

  final PuntoCuerpo hombroIzq;
  final PuntoCuerpo hombroDer;
  final PuntoCuerpo caderaIzq;
  final PuntoCuerpo caderaDer;

  List<PuntoCuerpo> get puntos => [hombroIzq, hombroDer, caderaIzq, caderaDer];

  PoseCuerpo transformar(PuntoCuerpo Function(int indice, PuntoCuerpo punto) f) {
    final p = puntos;
    return PoseCuerpo(hombroIzq: f(0, p[0]), hombroDer: f(1, p[1]), caderaIzq: f(2, p[2]), caderaDer: f(3, p[3]));
  }
}

/// Quien detecta el cuerpo en un cuadro de la cámara. Plan A: `DetectorMlKit`. Plan B (si hiciera falta): MoveNet Lightning con tflite_flutter en un Isolate.
abstract class DetectorPose {
  Future<PoseCuerpo?> detectar(CameraImage imagen, int rotacionGrados);

  Future<void> cerrar();
}
