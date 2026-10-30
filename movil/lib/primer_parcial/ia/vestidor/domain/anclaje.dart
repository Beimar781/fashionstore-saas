import 'dart:math' as math;
import 'dart:ui';

import 'cuerpo.dart';

/// Dónde está la prenda dentro de su PNG (proporciones de 0 a 1), tal como lo guarda el servidor.
class Anclaje {
  const Anclaje({this.yHombros = 0.10, this.anchoHombros = 0.85, this.yCadera = 0.92, this.ajuste = 1.0});

  factory Anclaje.desdeJson(Map<String, dynamic> j) => Anclaje(
        yHombros: (j['y_hombros'] as num).toDouble(),
        anchoHombros: (j['ancho_hombros'] as num).toDouble(),
        yCadera: (j['y_cadera'] as num).toDouble(),
        ajuste: (j['ajuste'] as num).toDouble(),
      );

  final double yHombros;
  final double anchoHombros;
  final double yCadera;
  final double ajuste;
}

/// Dónde y cómo dibujar el PNG: su centro en píxeles, su tamaño y cuánto se gira (radianes).
class Colocacion {
  const Colocacion({required this.centro, required this.ancho, required this.alto, required this.angulo});

  final Offset centro;
  final double ancho;
  final double alto;
  final double angulo;
}

/// Qué parte del tamaño sale del torso (distancia hombros-caderas); el resto sale del ancho de hombros, que es lo más estable.
const pesoDelTorso = 0.35;

/// Lógica pura: coloca la prenda sobre el cuerpo. La línea de hombros del PNG coincide con los hombros detectados y el ancho se ajusta a su separación;
/// si las caderas se ven bien, el largo del torso afina la escala. `escalaTalla` viene del servidor por código de talla (1.0 si no figura).
Colocacion colocarPrenda({
  required PoseCuerpo pose,
  required Anclaje anclaje,
  required double escalaTalla,
  required Size area,
  required double proporcionPng, // ancho / alto del PNG
  double umbralCadera = 0.30,
}) {
  final izq = pose.hombroIzq.x <= pose.hombroDer.x ? pose.hombroIzq : pose.hombroDer;
  final der = identical(izq, pose.hombroIzq) ? pose.hombroDer : pose.hombroIzq;
  final a = Offset(izq.x * area.width, izq.y * area.height);
  final b = Offset(der.x * area.width, der.y * area.height);
  final medio = Offset((a.dx + b.dx) / 2, (a.dy + b.dy) / 2);
  final anchoHombros = (b - a).distance;
  final angulo = math.atan2(b.dy - a.dy, b.dx - a.dx);

  var ancho = anchoHombros / anclaje.anchoHombros;
  final caderasVisibles = pose.caderaIzq.confianza >= umbralCadera && pose.caderaDer.confianza >= umbralCadera;
  if (caderasVisibles) {
    final cadera = Offset(
      (pose.caderaIzq.x + pose.caderaDer.x) / 2 * area.width,
      (pose.caderaIzq.y + pose.caderaDer.y) / 2 * area.height,
    );
    final torso = (cadera - medio).distance;
    final tramo = anclaje.yCadera - anclaje.yHombros;
    if (torso > 0 && tramo > 0) {
      final anchoPorTorso = torso / tramo * proporcionPng;
      ancho = ancho * (1 - pesoDelTorso) + anchoPorTorso * pesoDelTorso;
    }
  }
  ancho *= anclaje.ajuste * escalaTalla;
  final alto = ancho / proporcionPng;

  // el centro del PNG está (0.5 - yHombros) · alto por debajo del punto de anclaje, en la dirección del cuerpo
  final bajada = (0.5 - anclaje.yHombros) * alto;
  final centro = Offset(medio.dx - math.sin(angulo) * bajada, medio.dy + math.cos(angulo) * bajada);
  return Colocacion(centro: centro, ancho: ancho, alto: alto, angulo: angulo);
}
