import 'dart:ui';

import 'package:flutter/foundation.dart';

import '../../../../core/network/api_client.dart';
import '../data/vestidor_repository.dart';
import '../domain/anclaje.dart';
import '../domain/cuerpo.dart';
import '../domain/filtro_one_euro.dart';
import '../domain/guia.dart';
import '../domain/metricas.dart';

/// Estado del vestidor: la prenda elegida (color y talla), la pose suavizada, el bloqueo y las métricas. No sabe nada de la cámara:
/// la pantalla le entrega cada pose detectada, y así toda esta lógica se prueba sin teléfono.
class VestidorController extends ChangeNotifier {
  VestidorController(this._repo, this.productoId, {MedidorRendimiento? metricas, BloqueoPose? bloqueo})
      : metricas = metricas ?? MedidorRendimiento(),
        _bloqueo = bloqueo ?? BloqueoPose();

  final VestidorRepository _repo;
  final int productoId;
  final MedidorRendimiento metricas;
  BloqueoPose _bloqueo;
  final FiltroPose _filtro = FiltroPose();

  VestidorProducto? producto;
  bool cargando = true;
  String? error;
  ColorVestidor? color;
  String? talla;
  Uint8List? png;
  PoseCuerpo? _pose;
  bool depuracion = false;

  Guia get guia => _bloqueo.ultimaGuia;
  bool get prendaVisible => _bloqueo.bloqueado && _pose != null && png != null;
  List<ColorVestidor> get coloresListos => [for (final c in producto?.colores ?? const <ColorVestidor>[]) if (c.listo) c];
  List<String> get tallas => (producto?.escalaTallas.keys.toList() ?? <String>[])..sort();

  Future<void> cargar({String? tallaInicial}) async {
    cargando = true;
    error = null;
    notifyListeners();
    try {
      producto = await _repo.producto(productoId);
      final listos = coloresListos;
      talla = (tallaInicial != null && tallas.contains(tallaInicial)) ? tallaInicial : (tallas.isNotEmpty ? tallas.first : null);
      if (producto!.admite && listos.isNotEmpty) await elegirColor(listos.first);
    } on ApiException catch (e) {
      error = e.mensaje;
    }
    cargando = false;
    notifyListeners();
  }

  Future<void> elegirColor(ColorVestidor c) async {
    color = c;
    png = await _repo.imagen(c.imagenUrl!);  // casi siempre ya está en memoria: se precarga al abrir la ficha del producto
    notifyListeners();
  }

  void elegirTalla(String t) {
    talla = t;
    notifyListeners();
  }

  void alternarDepuracion() {
    depuracion = !depuracion;
    notifyListeners();
  }

  /// La proporción del cuadro (ancho / alto) se conoce cuando la cámara está lista.
  void usarProporcionCuadro(double proporcion) => _bloqueo = BloqueoPose(proporcionCuadro: proporcion);

  /// Cada detección terminada: se anota para las métricas, se suaviza y se decide si la prenda ya se puede mostrar. `instante` en segundos.
  void registrarDeteccion(PoseCuerpo? pose, Duration latencia, double instante) {
    metricas.registrarCuadro(latencia);
    final suave = pose == null ? null : _filtro.filtrar(pose, instante);
    if (_bloqueo.registrar(suave)) metricas.prendaVisible();
    if (suave != null) _pose = suave;
    if (!_bloqueo.bloqueado && suave == null) _filtro.reiniciar();
    notifyListeners();
  }

  /// Dónde dibujar la prenda en un área del tamaño dado, o null si todavía no hay que mostrarla.
  Colocacion? colocacion(Size area) {
    final c = color;
    final p = _pose;
    if (!prendaVisible || c == null || p == null) return null;
    return colocarPrenda(
      pose: p,
      anclaje: c.anclaje!,
      escalaTalla: talla == null ? 1.0 : producto!.escalaDe(talla!),
      area: area,
      proporcionPng: c.proporcion,
    );
  }

  void reiniciarSeguimiento() {
    _bloqueo.reiniciar();
    _filtro.reiniciar();
    metricas.reiniciar();
    _pose = null;
    notifyListeners();
  }
}
