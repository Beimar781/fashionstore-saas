import 'dart:async';

import 'package:camera/camera.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../data/detector_mlkit.dart';
import '../data/vestidor_repository.dart';
import '../domain/cuerpo.dart';
import '../domain/guia.dart';
import '../domain/metricas.dart';
import 'vestidor_controller.dart';

/// CU-06 · Vestidor virtual: la cámara muestra al cliente y la prenda se dibuja sobre sus hombros y torso. Solo prendas superiores.
/// La detección de pose ocurre en el teléfono; ningún cuadro de la cámara sale de él. El botón del insecto muestra FPS y latencia.
class VestidorScreen extends StatefulWidget {
  const VestidorScreen({super.key, required this.repo, required this.productoId, required this.nombre, this.tallaInicial});

  final VestidorRepository repo;
  final int productoId;
  final String nombre;
  final String? tallaInicial;

  @override
  State<VestidorScreen> createState() => _VestidorScreenState();
}

class _VestidorScreenState extends State<VestidorScreen> with WidgetsBindingObserver {
  late final VestidorController _c = VestidorController(widget.repo, widget.productoId);
  final Stopwatch _reloj = Stopwatch()..start();
  List<CameraDescription> _camaras = [];
  int _indice = 0;
  CameraController? _camara;
  DetectorPose? _detector;
  bool _ocupado = false;
  bool _permisoDenegado = false;
  String? _errorCamara;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    SystemChrome.setPreferredOrientations([DeviceOrientation.portraitUp]); // el anclaje y la rotación del cuadro se calculan en vertical
    _arrancar();
  }

  Future<void> _arrancar() async {
    await _c.cargar(tallaInicial: widget.tallaInicial);
    if (!mounted || _c.producto?.admite != true || _c.coloresListos.isEmpty) return;
    try {
      _camaras = await availableCameras();
      if (_camaras.isEmpty) {
        setState(() => _errorCamara = 'Este dispositivo no tiene cámara.');
        return;
      }
      _indice = _camaras.indexWhere((c) => c.lensDirection == CameraLensDirection.front);
      if (_indice < 0) _indice = 0;
      await _abrirCamara();
    } on CameraException catch (e) {
      _manejarErrorDeCamara(e);
    }
  }

  void _manejarErrorDeCamara(CameraException e) {
    if (!mounted) return;
    setState(() {
      if (e.code.startsWith('CameraAccessDenied') || e.code == 'CameraAccessRestricted') {
        _permisoDenegado = true;
      } else {
        _errorCamara = 'No se pudo abrir la cámara.';
      }
    });
  }

  Future<void> _abrirCamara() async {
    await _cerrarCamara();
    final descripcion = _camaras[_indice];
    final controlador = CameraController(
      descripcion,
      ResolutionPreset.medium, // 640×480 aprox.: suficiente para hombros y caderas y mucho más rápido que alta resolución
      enableAudio: false,
      imageFormatGroup: ImageFormatGroup.nv21,
    );
    try {
      await controlador.initialize();
    } on CameraException catch (e) {
      await controlador.dispose();
      _manejarErrorDeCamara(e);
      return;
    }
    if (!mounted) {
      await controlador.dispose();
      return;
    }
    _detector = DetectorMlKit(espejo: descripcion.lensDirection == CameraLensDirection.front);
    _c.usarProporcionCuadro(1 / controlador.value.aspectRatio);
    _c.reiniciarSeguimiento();
    _reloj
      ..reset()
      ..start();
    setState(() => _camara = controlador);
    await controlador.startImageStream((imagen) => _alCuadro(imagen, descripcion.sensorOrientation));
  }

  /// Un cuadro a la vez: si la detección anterior no terminó, el cuadro se descarta (así la imagen nunca se atrasa).
  Future<void> _alCuadro(CameraImage imagen, int rotacion) async {
    final detector = _detector;
    if (_ocupado || detector == null) return;
    _ocupado = true;
    final inicio = Stopwatch()..start();
    try {
      final pose = await detector.detectar(imagen, rotacion);
      if (mounted) _c.registrarDeteccion(pose, inicio.elapsed, _reloj.elapsedMicroseconds / 1e6);
    } catch (_) {
      // un cuadro que falla se descarta; el siguiente se procesa normalmente
    } finally {
      _ocupado = false;
    }
  }

  Future<void> _cerrarCamara() async {
    final camara = _camara;
    _camara = null;
    if (camara != null) {
      try {
        if (camara.value.isStreamingImages) await camara.stopImageStream();
      } catch (_) {}
      await camara.dispose();
    }
    await _detector?.cerrar();
    _detector = null;
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState estado) {
    if (estado == AppLifecycleState.inactive || estado == AppLifecycleState.paused) {
      _cerrarCamara();
      if (mounted) setState(() {});
    } else if (estado == AppLifecycleState.resumed && _camaras.isNotEmpty && _camara == null && !_permisoDenegado) {
      _abrirCamara();
    }
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _cerrarCamara();
    SystemChrome.setPreferredOrientations(DeviceOrientation.values);
    _c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: _c,
      builder: (context, _) => Scaffold(
        backgroundColor: Colors.black,
        appBar: AppBar(
          title: Text(widget.nombre),
          actions: [
            if (_camaras.length > 1)
              IconButton(
                tooltip: 'Cambiar de cámara',
                icon: const Icon(Icons.cameraswitch),
                onPressed: () {
                  _indice = (_indice + 1) % _camaras.length;
                  _abrirCamara();
                },
              ),
            IconButton(tooltip: 'FPS y latencia', icon: Icon(_c.depuracion ? Icons.bug_report : Icons.bug_report_outlined), onPressed: _c.alternarDepuracion),
          ],
        ),
        body: _cuerpo(context),
      ),
    );
  }

  Widget _mensaje(String texto) => Center(child: Padding(padding: const EdgeInsets.all(24), child: Text(texto, textAlign: TextAlign.center, style: const TextStyle(color: Colors.white, fontSize: 16))));

  Widget _cuerpo(BuildContext context) {
    if (_c.cargando) return const Center(child: CircularProgressIndicator());
    if (_c.error != null) return _mensaje(_c.error!);
    final producto = _c.producto!;
    if (!producto.admite) return _mensaje(producto.mensaje ?? 'Esta prenda no admite vestidor.');
    if (_c.coloresListos.isEmpty) return _mensaje('Esta prenda todavía no tiene imagen para el vestidor.');
    if (_permisoDenegado) {
      return _mensaje('Necesitamos la cámara para el vestidor. Permita el acceso en Ajustes → Aplicaciones → FashionStore → Permisos y vuelva a abrir el vestidor.');
    }
    if (_errorCamara != null) return _mensaje(_errorCamara!);
    final camara = _camara;
    if (camara == null || !camara.value.isInitialized) return const Center(child: CircularProgressIndicator());
    return Column(children: [
      Expanded(
        child: Center(
          child: AspectRatio(
            aspectRatio: 1 / camara.value.aspectRatio,
            child: LayoutBuilder(builder: (context, caja) {
              final area = Size(caja.maxWidth, caja.maxHeight);
              final colocacion = _c.colocacion(area);
              return Stack(fit: StackFit.expand, children: [
                CameraPreview(camara),
                if (colocacion != null && _c.png != null)
                  Positioned(
                    left: colocacion.centro.dx - colocacion.ancho / 2,
                    top: colocacion.centro.dy - colocacion.alto / 2,
                    width: colocacion.ancho,
                    height: colocacion.alto,
                    child: IgnorePointer(
                      child: Transform.rotate(angle: colocacion.angulo, child: Image.memory(_c.png!, fit: BoxFit.fill, gaplessPlayback: true, filterQuality: FilterQuality.low)),
                    ),
                  ),
                if (!_c.prendaVisible) Positioned(left: 12, right: 12, bottom: 12, child: _guia()),
                if (_c.depuracion) Positioned(left: 8, top: 8, child: _depuracion()),
              ]);
            }),
          ),
        ),
      ),
      _controles(),
    ]);
  }

  Widget _guia() => Center(
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
          decoration: BoxDecoration(color: Colors.black54, borderRadius: BorderRadius.circular(20)),
          child: Text(mensajesGuia[_c.guia]!, style: const TextStyle(color: Colors.white, fontSize: 15)),
        ),
      );

  Widget _depuracion() {
    final m = _c.metricas;
    String marca(bool ok) => ok ? '✓' : '✗';
    final prenda = m.prendaVisibleMs == null ? 'aún no' : '${(m.prendaVisibleMs! / 1000).toStringAsFixed(2)} s ${marca(m.cumplePrenda)}';
    return Container(
      padding: const EdgeInsets.all(8),
      decoration: BoxDecoration(color: Colors.black87, borderRadius: BorderRadius.circular(8)),
      child: DefaultTextStyle(
        style: const TextStyle(color: Colors.greenAccent, fontSize: 12, fontFeatures: [FontFeature.tabularFigures()]),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
          Text('FPS: ${m.fps.toStringAsFixed(0)} ${marca(m.cumpleFps)}  (meta ${MedidorRendimiento.metaFps.toStringAsFixed(0)})'),
          Text('Latencia: ${m.latenciaMs.toStringAsFixed(0)} ms'),
          Text('Prenda visible: $prenda  (meta < 1 s)'),
          Text('Guía: ${_c.guia.name}'),
        ]),
      ),
    );
  }

  Widget _controles() => Container(
        color: Colors.black,
        padding: const EdgeInsets.fromLTRB(12, 8, 12, 16),
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          Wrap(spacing: 8, children: [
            for (final c in _c.coloresListos)
              ChoiceChip(label: Text(c.nombre), selected: _c.color?.id == c.id, onSelected: (_) => _c.elegirColor(c)),
          ]),
          if (_c.tallas.isNotEmpty)
            Wrap(spacing: 8, children: [
              for (final t in _c.tallas) ChoiceChip(label: Text(t), selected: _c.talla == t, onSelected: (_) => _c.elegirTalla(t)),
            ]),
        ]),
      );
}
