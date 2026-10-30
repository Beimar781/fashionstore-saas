import 'package:sqflite/sqflite.dart';

import '../../../core/db/local_database.dart';
import '../../../core/network/api_client.dart';
import '../../../core/util/uuid.dart';
import 'proveedor_push.dart';

/// Aviso importante que el servidor dejó para el usuario (devolución o cambio, compra sin conexión que no se pudo atender...).
class AvisoPush {
  AvisoPush({required this.id, required this.titulo, required this.mensaje, required this.leido});

  factory AvisoPush.desdeJson(Map<String, dynamic> j) =>
      AvisoPush(id: j['id'] as int, titulo: j['titulo'] as String, mensaje: j['mensaje'] as String, leido: j['leida'] as bool);

  final int id;
  final String titulo;
  final String mensaje;
  final bool leido;
}

/// RF11 · Avisos push en el móvil (regla 17). Con Firebase, el dispositivo se registra con su token de FCM y los avisos llegan como notificación nativa.
/// Sin Firebase (modo simulado) se registra con un identificador local, el servidor deja el aviso pendiente en la campana y la app lo muestra al abrirse o al sincronizar.
class PushRepository {
  PushRepository(this._api, {ProveedorPush? proveedor}) : _proveedor = proveedor;

  final ApiClient _api;
  final ProveedorPush? _proveedor;

  /// Lo llama el controlador: se ejecuta cuando llega un aviso con la app abierta.
  void Function() alRecibirAviso = () {};

  Stream<String> get tokenRenovado => _proveedor?.tokenRenovado ?? const Stream.empty();

  /// Identificador de este dispositivo: se genera una vez y se guarda en SQLite.
  Future<String> identificadorLocal() async {
    final db = await LocalDatabase.instance.database;
    final f = await db.query('meta', where: 'clave = ?', whereArgs: ['push_dispositivo']);
    if (f.isNotEmpty) return f.first['valor'] as String;
    final nuevo = 'simulado-${generarUuid()}';
    await db.insert('meta', {'clave': 'push_dispositivo', 'valor': nuevo});
    return nuevo;
  }

  /// Token que se registró en el servidor: se guarda para darlo de baja al cerrar sesión aunque Firebase ya no esté disponible.
  Future<String?> _registrado() async {
    final db = await LocalDatabase.instance.database;
    final f = await db.query('meta', where: 'clave = ?', whereArgs: ['push_registrado']);
    return f.isEmpty ? null : f.first['valor'] as String;
  }

  Future<void> registrarDispositivo({String? tokenNuevo}) async {
    final token = tokenNuevo ?? await _proveedor?.iniciar(alRecibir: () => alRecibirAviso()) ?? await identificadorLocal();
    await _api.post('/notificaciones/dispositivos', {'canal': 'MOVIL', 'token': token});
    final db = await LocalDatabase.instance.database;
    await db.insert('meta', {'clave': 'push_registrado', 'valor': token}, conflictAlgorithm: ConflictAlgorithm.replace);
  }

  Future<void> quitarDispositivo() async =>
      _api.post('/notificaciones/dispositivos/baja', {'canal': 'MOVIL', 'token': await _registrado() ?? await identificadorLocal()});

  Future<List<AvisoPush>> pendientes() async =>
      (await _api.getLista('/notificaciones?solo_no_leidas=true&limite=20')).map((j) => AvisoPush.desdeJson(j as Map<String, dynamic>)).toList();

  Future<void> marcarLeido(int id) async => _api.post('/notificaciones/$id/leer', {});
}
