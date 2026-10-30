/// Mide lo que importa del vestidor en el teléfono: cuántos cuadros por segundo se procesan, cuánto tarda cada detección y en cuánto tiempo aparece la prenda.
/// Metas: prenda visible en menos de 1 segundo y 15 FPS o más. El reloj se inyecta para poder probarlo.
class MedidorRendimiento {
  MedidorRendimiento({DateTime Function()? reloj}) : _reloj = reloj ?? DateTime.now;

  static const metaFps = 15.0;
  static const metaPrendaMs = 1000;

  final DateTime Function() _reloj;
  final List<DateTime> _cuadros = [];
  final List<int> _latencias = [];
  DateTime? _primerCuadro;
  int? prendaVisibleMs;

  /// Se anota cada detección terminada y lo que tardó (de recibir el cuadro a tener la pose).
  void registrarCuadro(Duration latencia) {
    final ahora = _reloj();
    _primerCuadro ??= ahora.subtract(latencia);
    _cuadros.add(ahora);
    _cuadros.removeWhere((t) => ahora.difference(t) > const Duration(seconds: 1));
    _latencias.add(latencia.inMilliseconds);
    if (_latencias.length > 30) _latencias.removeAt(0);
  }

  /// Se llama cuando la prenda aparece por primera vez: mide desde el primer cuadro recibido.
  void prendaVisible() {
    final inicio = _primerCuadro;
    if (inicio != null) prendaVisibleMs ??= _reloj().difference(inicio).inMilliseconds;
  }

  double get fps => _cuadros.length.toDouble();

  double get latenciaMs => _latencias.isEmpty ? 0 : _latencias.reduce((a, b) => a + b) / _latencias.length;

  bool get cumpleFps => fps >= metaFps;

  bool get cumplePrenda => prendaVisibleMs != null && prendaVisibleMs! < metaPrendaMs;

  void reiniciar() {
    _cuadros.clear();
    _latencias.clear();
    _primerCuadro = null;
    prendaVisibleMs = null;
  }
}
