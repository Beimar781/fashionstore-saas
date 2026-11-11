import 'dart:async';

import 'package:camera/camera.dart';
import 'package:flutter/material.dart';
import 'package:google_mlkit_barcode_scanning/google_mlkit_barcode_scanning.dart';

/// B7 · Abre la cámara y devuelve el primer código de barras o QR que lea (o null si el usuario vuelve atrás). La lectura ocurre en el teléfono, sin enviar imágenes.
Future<String?> escanearCodigo(BuildContext context) => Navigator.of(context).push<String>(MaterialPageRoute(builder: (_) => const EscanerScreen()));

class EscanerScreen extends StatefulWidget {
  const EscanerScreen({super.key});

  @override
  State<EscanerScreen> createState() => _EscanerScreenState();
}

class _EscanerScreenState extends State<EscanerScreen> {
  final BarcodeScanner _escaner = BarcodeScanner();
  CameraController? _camara;
  bool _ocupado = false;
  bool _terminado = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _abrir();
  }

  Future<void> _abrir() async {
    try {
      final camaras = await availableCameras();
      if (camaras.isEmpty) return setState(() => _error = 'Este dispositivo no tiene cámara.');
      final trasera = camaras.firstWhere((c) => c.lensDirection == CameraLensDirection.back, orElse: () => camaras.first);
      final controlador = CameraController(trasera, ResolutionPreset.medium, enableAudio: false, imageFormatGroup: ImageFormatGroup.nv21);
      await controlador.initialize();
      if (!mounted) {
        await controlador.dispose();
        return;
      }
      setState(() => _camara = controlador);
      await controlador.startImageStream((imagen) => _alCuadro(imagen, trasera.sensorOrientation));
    } on CameraException catch (e) {
      if (mounted) setState(() => _error = e.code.startsWith('CameraAccess') ? 'Permita el acceso a la cámara para escanear códigos.' : 'No se pudo abrir la cámara.');
    } catch (_) {
      if (mounted) setState(() => _error = 'No se pudo abrir la cámara.');
    }
  }

  Future<void> _alCuadro(CameraImage imagen, int rotacion) async {
    if (_ocupado || _terminado || imagen.planes.length != 1) return;
    _ocupado = true;
    try {
      final plano = imagen.planes.first;
      final entrada = InputImage.fromBytes(
        bytes: plano.bytes,
        metadata: InputImageMetadata(
          size: Size(imagen.width.toDouble(), imagen.height.toDouble()),
          rotation: switch (rotacion % 360) {
            90 => InputImageRotation.rotation90deg,
            180 => InputImageRotation.rotation180deg,
            270 => InputImageRotation.rotation270deg,
            _ => InputImageRotation.rotation0deg,
          },
          format: InputImageFormat.nv21,
          bytesPerRow: plano.bytesPerRow,
        ),
      );
      final codigos = await _escaner.processImage(entrada);
      final valor = codigos.map((c) => c.rawValue).whereType<String>().firstOrNull;
      if (valor != null && mounted && !_terminado) {
        _terminado = true;
        Navigator.of(context).pop(valor);
      }
    } catch (_) {
      // un cuadro que falla se descarta; el siguiente se procesa normalmente
    } finally {
      _ocupado = false;
    }
  }

  @override
  void dispose() {
    unawaited(_camara?.dispose());
    unawaited(_escaner.close());
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        backgroundColor: Colors.black,
        appBar: AppBar(title: const Text('Escanear código')),
        body: _error != null
            ? Center(child: Padding(padding: const EdgeInsets.all(24), child: Text(_error!, textAlign: TextAlign.center, style: const TextStyle(color: Colors.white, fontSize: 16))))
            : _camara == null || !_camara!.value.isInitialized
                ? const Center(child: CircularProgressIndicator())
                : Stack(fit: StackFit.expand, children: [
                    CameraPreview(_camara!),
                    Align(alignment: Alignment.bottomCenter, child: Padding(padding: EdgeInsets.only(bottom: MediaQuery.viewPaddingOf(context).bottom + 24), child: const Text('Apunte al código de barras o QR de la prenda', style: TextStyle(color: Colors.white, fontSize: 15)))),
                  ]),
      );
}
