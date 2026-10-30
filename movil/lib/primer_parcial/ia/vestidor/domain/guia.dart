import 'cuerpo.dart';

/// Umbral de confianza para dar un punto por visto (el móvil viejo pedía 0.42 y nunca «enganchaba»).
const umbralConfianza = 0.30;

enum Guia { sinPersona, subeLaCamara, acercate, alejate, ponteDeFrente, bien }

const mensajesGuia = {
  Guia.sinPersona: 'Ponte frente a la cámara',
  Guia.subeLaCamara: 'Sube la cámara hasta que se vean tus hombros',
  Guia.acercate: 'Acércate un poco',
  Guia.alejate: 'Aléjate un poco',
  Guia.ponteDeFrente: 'Ponte de frente a la cámara',
  Guia.bien: 'Listo',
};

/// Mira la pose y dice qué le falta al usuario para que la prenda enganche.
/// `proporcionCuadro` es ancho / alto del cuadro (vertical, 3:4 = 0.75): los puntos van de 0 a 1 en cada eje, así que hay que devolverlos a la misma escala.
Guia evaluarPose(PoseCuerpo? pose, {double proporcionCuadro = 0.75}) {
  if (pose == null) return Guia.sinPersona;
  if (pose.hombroIzq.confianza < umbralConfianza || pose.hombroDer.confianza < umbralConfianza) return Guia.subeLaCamara;
  final ancho = (pose.hombroDer.x - pose.hombroIzq.x).abs();
  if (ancho < 0.14) return Guia.acercate;
  if (ancho > 0.85) return Guia.alejate;
  final caderasVisibles = pose.caderaIzq.confianza >= umbralConfianza && pose.caderaDer.confianza >= umbralConfianza;
  if (caderasVisibles) {
    final mediaCaderaY = (pose.caderaIzq.y + pose.caderaDer.y) / 2;
    final mediaHombroY = (pose.hombroIzq.y + pose.hombroDer.y) / 2;
    final torso = mediaCaderaY - mediaHombroY;
    // de frente, el ancho de hombros es cerca de 0.8 veces el largo del torso; de lado se juntan (menos de 0.3)
    if (torso > 0 && ancho * proporcionCuadro / torso < 0.30) return Guia.ponteDeFrente;
  }
  return Guia.bien;
}

/// Bloqueo con pocos cuadros buenos (1 o 2) para que la prenda aparezca rápido, y con paciencia para soltarla: un cuadro malo suelto no la apaga.
class BloqueoPose {
  BloqueoPose({this.cuadrosParaBloquear = 2, this.cuadrosParaSoltar = 8, this.proporcionCuadro = 0.75});

  final double proporcionCuadro;
  final int cuadrosParaBloquear;
  final int cuadrosParaSoltar;

  int _buenos = 0;
  int _malos = 0;
  bool bloqueado = false;
  Guia ultimaGuia = Guia.sinPersona;

  /// Devuelve true si este cuadro es el que acaba de bloquear la pose (la primera vez que se ve la prenda).
  bool registrar(PoseCuerpo? pose) {
    ultimaGuia = evaluarPose(pose, proporcionCuadro: proporcionCuadro);
    if (ultimaGuia == Guia.bien) {
      _malos = 0;
      _buenos++;
      if (!bloqueado && _buenos >= cuadrosParaBloquear) {
        bloqueado = true;
        return true;
      }
    } else {
      _buenos = 0;
      _malos++;
      if (bloqueado && _malos >= cuadrosParaSoltar) bloqueado = false;
    }
    return false;
  }

  void reiniciar() {
    _buenos = 0;
    _malos = 0;
    bloqueado = false;
    ultimaGuia = Guia.sinPersona;
  }
}
