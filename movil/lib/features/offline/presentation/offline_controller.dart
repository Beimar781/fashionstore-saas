import 'dart:async';

import 'package:flutter/foundation.dart';

import '../../auth/data/sesion.dart';
import '../data/modelos.dart';
import '../data/offline_repository.dart';

/// Estado del modo sin conexión para la capa de presentación (CU-37 a CU-39).
/// Cuando hay sesión, sincroniza al abrir la app, en el instante en que vuelve la red y, como respaldo, cada 30 segundos mientras queden operaciones pendientes (RNF06).
class OfflineController extends ChangeNotifier {
  /// `conectividad` emite true al recuperar la red y false al perderla (en la app es `conectividadDelDispositivo()`; en las pruebas, un doble).
  OfflineController(this._repo, {Stream<bool>? conectividad})
      : _conectividad = conectividad;

  final OfflineRepository _repo;
  final Stream<bool>? _conectividad;
  StreamSubscription<bool>? _red;

  Sesion? _sesion;
  Timer? _reintento;
  List<OperacionLocal> operaciones = [];
  bool hayCatalogo = false;
  String? catalogoGeneradoEn;
  String? ultimaSync;
  bool sincronizando = false;
  bool descargando = false;
  bool enLinea = true;
  String? error;

  OfflineRepository get repo => _repo;
  Sesion? get sesion => _sesion;
  List<OperacionLocal> get pendientes =>
      operaciones.where((o) => o.pendiente).toList();
  List<OperacionLocal> get enConflicto =>
      operaciones.where((o) => o.estado == Estado.enConflicto).toList();
  bool get esCliente => _sesion?.rol == 'Cliente';
  bool get habilitado =>
      _sesion != null &&
      _sesion!.offlineHabilitado &&
      ['Cliente', 'Cajero', 'Encargado'].contains(_sesion!.rol);

  /// Lo llama el proveedor cada vez que cambia la sesión (inicio y cierre de sesión).
  void usarSesion(Sesion? s) {
    final cambio = s?.usuarioId != _sesion?.usuarioId;
    _sesion = s;
    if (!cambio) return;
    _reintento?.cancel();
    _red?.cancel();
    operaciones = [];
    if (habilitado) {
      _red = _conectividad?.listen(_alCambiarLaRed);
      _reintento = Timer.periodic(const Duration(seconds: 30), (_) {
        if (pendientes.isNotEmpty) sincronizar();
        actualizarSiVencido();
      });
      Future.microtask(() async {
        await recargar();
        await sincronizar();
      });
    } else {
      notifyListeners();
    }
  }

  /// Al perder la red se avisa en el acto; al recuperarla se sincroniza sin esperar al reintento.
  void _alCambiarLaRed(bool hayRed) {
    enLinea = hayRed;
    notifyListeners();
    if (hayRed && pendientes.isNotEmpty) sincronizar();
    if (hayRed) actualizarSiVencido();
  }

  Future<void> recargar() async {
    final s = _sesion;
    if (s == null || s.empresaId == null) return;
    operaciones = await _repo.operaciones(s.usuarioId, s.empresaId!);
    hayCatalogo = await _repo.hayCatalogo();
    catalogoGeneradoEn = await _repo.catalogoGeneradoEn();
    ultimaSync = await _repo.ultimaSincronizacion();
    notifyListeners();
  }

  /// Horas después de las cuales el catálogo descargado se actualiza solo con conexión (§5.3).
  static const horasVigencia = 6;

  bool get catalogoVencido {
    final fecha = DateTime.tryParse(catalogoGeneradoEn ?? '');
    return fecha != null && DateTime.now().difference(fecha).inHours >= horasVigencia;
  }

  /// Con conexión, si el catálogo tiene más de 6 horas se descarga de nuevo en segundo plano; «Actualizar ahora» hace lo mismo a mano.
  Future<void> actualizarSiVencido() async {
    if (!habilitado || !enLinea || descargando || !hayCatalogo || !catalogoVencido) return;
    await descargarCatalogo();
  }

  /// CU-37: descarga el catálogo con conexión.
  Future<void> descargarCatalogo() async {
    descargando = true;
    error = null;
    notifyListeners();
    try {
      await _repo.descargarCatalogo();
      enLinea = true;
    } catch (e) {
      error = e.toString();
      enLinea = false;
    }
    descargando = false;
    await recargar();
  }

  /// RF19: registra una operación en el dispositivo y, si hay conexión, la sincroniza enseguida.
  Future<void> registrar(
      {required String tipo,
      required Map<String, dynamic> payload,
      required int sucursalId,
      required String resumen}) async {
    final s = _sesion!;
    await _repo.registrar(
        tipo: tipo,
        payload: payload,
        sucursalId: sucursalId,
        resumen: resumen,
        usuarioId: s.usuarioId,
        empresaId: s.empresaId!);
    await _repo.comprometerStock(
        (payload['items'] as List).cast<Map<String, dynamic>>(), sucursalId);
    await recargar();
    sincronizar();
  }

  /// CU-38: envía lo pendiente. No hace nada si ya hay una sincronización en curso.
  /// Quién muestra el mensaje emergente al cliente (lo conecta la app con su ScaffoldMessenger).
  void Function(String)? alAvisar;

  Future<ResumenSync?> sincronizar() async {
    final s = _sesion;
    if (s == null || s.empresaId == null || sincronizando) return null;
    sincronizando = true;
    notifyListeners();
    final resumen = await _repo.sincronizar(s.usuarioId, s.empresaId!);
    enLinea = !resumen.sinConexion;
    error = resumen.error;
    sincronizando = false;
    await recargar();
    for (final aviso in resumen.avisos) {
      alAvisar?.call(aviso);
    }
    return resumen;
  }

  Future<void> limpiarTerminadas() async {
    final s = _sesion;
    if (s == null || s.empresaId == null) return;
    await _repo.limpiarTerminadas(s.usuarioId, s.empresaId!);
    await recargar();
  }

  @override
  void dispose() {
    _reintento?.cancel();
    _red?.cancel();
    super.dispose();
  }
}
