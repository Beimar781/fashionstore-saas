import 'dart:convert';

import 'package:sqflite/sqflite.dart';

import '../../../core/db/local_database.dart';
import '../../../core/network/api_client.dart';
import 'sesion.dart';

/// Acceso a datos del paquete Usuarios y acceso: API REST + sesión local en SQLite.
class AuthRepository {
  AuthRepository() {
    _api = ApiClient(obtenerToken: _accessToken, renovarToken: _renovar);
  }

  late final ApiClient _api;

  /// Cliente HTTP con el token de la sesión: lo usan también los demás paquetes (catálogo, reservas, offline).
  ApiClient get api => _api;

  Future<Database> get _db => LocalDatabase.instance.database;

  /// CU-02: inicia sesión en el servidor y guarda el contexto localmente.
  Future<Sesion> iniciarSesion({String? codigoEmpresa, required String email, required String password}) async {
    final codigo = (codigoEmpresa ?? '').trim();
    final respuesta = await _api.post(
      '/auth/login',
      {'codigo_empresa': codigo.isEmpty ? null : codigo, 'email': email.trim(), 'password': password},
      autenticado: false,
    );
    return _guardar(respuesta);
  }

  /// Sesión guardada en el dispositivo (permite continuar sin conexión).
  Future<Sesion?> sesionLocal() async {
    final filas = await (await _db).query('sesion', where: 'id = 1');
    if (filas.isEmpty) return null;
    return Sesion(jsonDecode(filas.first['contexto_json'] as String) as Map<String, dynamic>);
  }

  /// ¿La sesión local corresponde al usuario que intenta ingresar sin conexión?
  Future<bool> coincideConSesionLocal(String? codigoEmpresa, String email) async {
    final local = await sesionLocal();
    if (local == null) return false;
    return local.email.toLowerCase() == email.trim().toLowerCase() &&
        (local.empresaCodigo ?? '').toLowerCase() == (codigoEmpresa ?? '').trim().toLowerCase();
  }

  /// Actualiza el contexto desde el servidor (por ejemplo, si cambió el plan de la empresa).
  Future<Sesion> actualizarContexto() async {
    final contexto = await _api.get('/auth/me');
    final db = await _db;
    await db.update(
      'sesion',
      {'contexto_json': jsonEncode(contexto), 'actualizado_en': DateTime.now().toIso8601String()},
      where: 'id = 1',
    );
    return Sesion(contexto);
  }

  Future<void> cerrarSesion() async {
    await (await _db).delete('sesion');
  }

  // ---- internos ----
  Future<Sesion> _guardar(Map<String, dynamic> respuesta) async {
    final contexto = Map<String, dynamic>.from(respuesta)
      ..remove('access_token')
      ..remove('refresh_token')
      ..remove('token_type');
    await (await _db).insert(
      'sesion',
      {
        'id': 1,
        'access_token': respuesta['access_token'],
        'refresh_token': respuesta['refresh_token'],
        'contexto_json': jsonEncode(contexto),
        'actualizado_en': DateTime.now().toIso8601String(),
      },
      conflictAlgorithm: ConflictAlgorithm.replace,
    );
    return Sesion(contexto);
  }

  Future<String?> _accessToken() async {
    final filas = await (await _db).query('sesion', columns: ['access_token'], where: 'id = 1');
    return filas.isEmpty ? null : filas.first['access_token'] as String;
  }

  Future<bool> _renovar() async {
    final filas = await (await _db).query('sesion', columns: ['refresh_token'], where: 'id = 1');
    if (filas.isEmpty) return false;
    try {
      final respuesta = await _api.post(
        '/auth/refresh',
        {'refresh_token': filas.first['refresh_token']},
        autenticado: false,
      );
      await _guardar(respuesta);
      return true;
    } on ApiException {
      return false;
    }
  }
}
