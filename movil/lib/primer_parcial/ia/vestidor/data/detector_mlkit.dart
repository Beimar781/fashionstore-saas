import 'dart:ui';

import 'package:camera/camera.dart';
import 'package:google_mlkit_pose_detection/google_mlkit_pose_detection.dart';

import '../domain/cuerpo.dart';

/// Plan A: detección de pose con ML Kit en modo stream. ML Kit se encarga de la conversión YUV, del giro y de un modelo optimizado para el celular.
/// Solo se piden los cuatro puntos que usa el vestidor. Los cuadros se procesan en el teléfono y nunca se envían a ningún servidor.
class DetectorMlKit implements DetectorPose {
  DetectorMlKit({required this.espejo})
      : _detector = PoseDetector(options: PoseDetectorOptions(model: PoseDetectionModel.base, mode: PoseDetectionMode.stream));

  /// Con la cámara frontal la vista previa sale en espejo: los puntos también se voltean para coincidir con lo que se ve.
  final bool espejo;
  final PoseDetector _detector;

  @override
  Future<PoseCuerpo?> detectar(CameraImage imagen, int rotacionGrados) async {
    if (imagen.format.group != ImageFormatGroup.nv21 || imagen.planes.length != 1) return null;
    final grados = rotacionGrados % 360;
    final rotacion = switch (grados) {
      90 => InputImageRotation.rotation90deg,
      180 => InputImageRotation.rotation180deg,
      270 => InputImageRotation.rotation270deg,
      _ => InputImageRotation.rotation0deg,
    };
    final plano = imagen.planes.first;
    final entrada = InputImage.fromBytes(
      bytes: plano.bytes,
      metadata: InputImageMetadata(
        size: Size(imagen.width.toDouble(), imagen.height.toDouble()),
        rotation: rotacion,
        format: InputImageFormat.nv21,
        bytesPerRow: plano.bytesPerRow,
      ),
    );
    final poses = await _detector.processImage(entrada);
    if (poses.isEmpty) return null;
    final puntos = poses.first.landmarks;
    final girado = grados == 90 || grados == 270; // con el cuadro girado, ancho y alto se intercambian
    final ancho = (girado ? imagen.height : imagen.width).toDouble();
    final alto = (girado ? imagen.width : imagen.height).toDouble();

    PuntoCuerpo punto(PoseLandmarkType tipo) {
      final p = puntos[tipo];
      if (p == null) return const PuntoCuerpo(0, 0, 0);
      final x = p.x / ancho;
      return PuntoCuerpo(espejo ? 1 - x : x, p.y / alto, p.likelihood);
    }

    return PoseCuerpo(
      hombroIzq: punto(PoseLandmarkType.leftShoulder),
      hombroDer: punto(PoseLandmarkType.rightShoulder),
      caderaIzq: punto(PoseLandmarkType.leftHip),
      caderaDer: punto(PoseLandmarkType.rightHip),
    );
  }

  @override
  Future<void> cerrar() => _detector.close();
}
