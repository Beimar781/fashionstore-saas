import 'package:flutter/foundation.dart';

import '../../../core/network/api_client.dart';
import '../data/auth_repository.dart';
import '../data/sesion.dart';

/// Estado de autenticación de la app (CU-02) para la capa de presentación.
class AuthController extends ChangeNotifier {
  AuthController(this._repo, {this.antesDeCerrarSesion});

  final AuthRepository _repo;

  /// Se ejecuta con el token todavía vigente (por ejemplo, para dar de baja el dispositivo de los avisos push).
  final Future<void> Function()? antesDeCerrarSesion;

  Sesion? sesion;
  bool iniciando = true;
  bool cargando = false;
  bool sinConexion = false;
  String? error;

  /// Al abrir la app se recupera la sesión guardada en SQLite (funciona sin conexión).
  Future<void> iniciar() async {
    sesion = await _repo.sesionLocal();
    iniciando = false;
    notifyListeners();
    if (sesion != null) await actualizarContexto();
  }

  Future<void> iniciarSesion({String? codigoEmpresa, required String email, required String password}) async {
    cargando = true;
    error = null;
    notifyListeners();
    try {
      sesion = await _repo.iniciarSesion(codigoEmpresa: codigoEmpresa, email: email, password: password);
      sinConexion = false;
    } on ApiException catch (e) {
      if (e.sinConexion) {
        // Sin conexión: solo se continúa con una sesión previa del mismo usuario en este dispositivo
        if (await _repo.coincideConSesionLocal(codigoEmpresa, email)) {
          sesion = await _repo.sesionLocal();
          sinConexion = true;
        } else {
          error = 'Se requiere conexión para el primer inicio de sesión.';
        }
      } else {
        error = e.mensaje;
      }
    }
    cargando = false;
    notifyListeners();
  }

  Future<void> actualizarContexto() async {
    try {
      sesion = await _repo.actualizarContexto();
      sinConexion = false;
    } on ApiException catch (e) {
      if (e.sinConexion) {
        sinConexion = true;
      } else if (e.statusCode == 401 || e.statusCode == 403) {
        // La sesión local venció o la empresa/usuario ya no está habilitado: se pide iniciar sesión de nuevo
        await cerrarSesion();
        return;
      }
    }
    notifyListeners();
  }

  Future<void> cerrarSesion() async {
    try {
      await antesDeCerrarSesion?.call().timeout(const Duration(seconds: 3));
    } catch (_) {}
    await _repo.cerrarSesion();
    sesion = null;
    error = null;
    notifyListeners();
  }
}
