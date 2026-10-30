import 'dart:collection';
import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:flutter/scheduler.dart';

/// Calcula los FPS reales de la pantalla a partir del instante en que termina de pintarse cada cuadro (en microsegundos).
class MedidorFps {
  final Queue<int> _ultimoSegundo = Queue<int>();
  int? _primero;
  int _ultimo = 0;
  int _total = 0;

  /// Cuadros pintados durante el último segundo.
  double get actual => _ultimoSegundo.length < 2 ? 0 : (_ultimoSegundo.length - 1) * 1e6 / (_ultimoSegundo.last - _ultimoSegundo.first);

  /// Cuadros por segundo desde que se empezó a medir.
  double get promedio => _total < 2 || _ultimo == _primero ? 0 : (_total - 1) * 1e6 / (_ultimo - _primero!);

  void registrar(int terminoEnMicros) {
    _primero ??= terminoEnMicros;
    _ultimo = terminoEnMicros;
    _total++;
    _ultimoSegundo.addLast(terminoEnMicros);
    while (_ultimoSegundo.length > 2 && terminoEnMicros - _ultimoSegundo.first > 1000000) {
      _ultimoSegundo.removeFirst();
    }
  }
}

/// Contador de FPS (actual y promedio) para medir el rendimiento en un celular real. Solo escucha los cuadros mientras está en pantalla:
/// al ocultarlo se quita de la jerarquía y se deja de escuchar, así que no cuesta nada cuando no se usa.
class ContadorFps extends StatefulWidget {
  const ContadorFps({super.key});

  @override
  State<ContadorFps> createState() => _ContadorFpsState();
}

class _ContadorFpsState extends State<ContadorFps> {
  final MedidorFps _medidor = MedidorFps();
  final ValueNotifier<String> _texto = ValueNotifier('FPS: midiendo…');
  int _ultimaActualizacion = 0;

  @override
  void initState() {
    super.initState();
    SchedulerBinding.instance.addTimingsCallback(_alPintar);
  }

  void _alPintar(List<FrameTiming> tiempos) {
    for (final t in tiempos) {
      _medidor.registrar(t.timestampInMicroseconds(FramePhase.rasterFinish));
    }
    final ahora = tiempos.last.timestampInMicroseconds(FramePhase.rasterFinish);
    if (ahora - _ultimaActualizacion < 500000) return; // el texto se refresca dos veces por segundo
    _ultimaActualizacion = ahora;
    _texto.value = 'FPS: ${_medidor.actual.toStringAsFixed(0)}  ·  promedio: ${_medidor.promedio.toStringAsFixed(1)}';
  }

  @override
  void dispose() {
    SchedulerBinding.instance.removeTimingsCallback(_alPintar);
    _texto.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => IgnorePointer(
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
          decoration: BoxDecoration(color: Colors.black87, borderRadius: BorderRadius.circular(8)),
          child: ValueListenableBuilder<String>(
            valueListenable: _texto,
            builder: (_, texto, __) => Text(texto, style: const TextStyle(color: Colors.greenAccent, fontSize: 12, fontFeatures: [FontFeature.tabularFigures()])),
          ),
        ),
      );
}
