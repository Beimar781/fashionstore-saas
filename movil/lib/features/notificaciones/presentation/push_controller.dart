import 'dart:async';

import 'package:flutter/foundation.dart';

import '../../auth/data/sesion.dart';
import '../data/push_repository.dart';

/// Registra el dispositivo del usuario al iniciar sesión y mantiene al día sus avisos pendientes. Un fallo (sin conexión, servidor caído) nunca interrumpe la app.
class PushController extends ChangeNotifier {
  PushController(this._repo) {
    _repo.alRecibirAviso = refrescar;
  }

  final PushRepository _repo;

  List<AvisoPush> avisos = [];
  int? _usuarioId;
  Timer? _reloj;
  StreamSubscription<String>? _renovacion;

  /// Lo llama el proveedor cada vez que cambia la sesión (inicio y cierre de sesión).
  void usarSesion(Sesion? s) {
    if (s?.usuarioId == _usuarioId) return;
    _usuarioId = s?.usuarioId;
    _reloj?.cancel();
    _renovacion?.cancel();
    avisos = [];
    if (s == null || s.restringido) {
      notifyListeners();
      return;
    }
    _reloj = Timer.periodic(const Duration(seconds: 60), (_) => refrescar());
    _renovacion = _repo.tokenRenovado.listen((t) async {
      try {
        await _repo.registrarDispositivo(tokenNuevo: t);
      } catch (_) {}
    });
    Future.microtask(() async {
      try {
        await _repo.registrarDispositivo();
      } catch (_) {}
      await refrescar();
    });
  }

  Future<void> refrescar() async {
    try {
      avisos = await _repo.pendientes();
      notifyListeners();
    } catch (_) {}
  }

  Future<void> leer(AvisoPush aviso) async {
    try {
      await _repo.marcarLeido(aviso.id);
    } catch (_) {
      return;
    }
    avisos = avisos.where((a) => a.id != aviso.id).toList();
    notifyListeners();
  }

  @override
  void dispose() {
    _reloj?.cancel();
    _renovacion?.cancel();
    super.dispose();
  }
}
