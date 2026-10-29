import 'dart:async';

import 'package:flutter/foundation.dart';

import '../../auth/data/sesion.dart';
import '../data/modelos.dart';
import '../data/offline_repository.dart';

/// Estado del modo sin conexión para la capa de presentación (CU-37 a CU-39).
/// Cuando hay sesión, sincroniza al abrir la app y reintenta cada 30 segundos mientras queden operaciones pendientes (RNF06).
class OfflineController extends ChangeNotifier {
  OfflineController(this._repo);

  final OfflineRepository _repo;

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
  List<OperacionLocal> get pendientes => operaciones.where((o) => o.pendiente).toList();
  List<OperacionLocal> get enConflicto => operaciones.where((o) => o.estado == Estado.enConflicto).toList();
  bool get esCliente => _sesion?.rol == 'Cliente';
  bool get habilitado => _sesion != null && _sesion!.offlineHabilitado && ['Cliente', 'Cajero', 'Encargado'].contains(_sesion!.rol);

  /// Lo llama el proveedor cada vez que cambia la sesión (inicio y cierre de sesión).
  void usarSesion(Sesion? s) {
    final cambio = s?.usuarioId != _sesion?.usuarioId;
    _sesion = s;
    if (!cambio) return;
    _reintento?.cancel();
    operaciones = [];
    if (habilitado) {
      _reintento = Timer.periodic(const Duration(seconds: 30), (_) {
        if (pendientes.isNotEmpty) sincronizar();
      });
      Future.microtask(() async {
        await recargar();
        await sincronizar();
      });
    } else {
      notifyListeners();
    }
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
  Future<void> registrar({required String tipo, required Map<String, dynamic> payload, required int sucursalId, required String resumen}) async {
    final s = _sesion!;
    await _repo.registrar(tipo: tipo, payload: payload, sucursalId: sucursalId, resumen: resumen, usuarioId: s.usuarioId, empresaId: s.empresaId!);
    await _repo.comprometerStock((payload['items'] as List).cast<Map<String, dynamic>>(), sucursalId);
    await recargar();
    sincronizar();
  }

  /// CU-38: envía lo pendiente. No hace nada si ya hay una sincronización en curso.
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
    super.dispose();
  }
}
