import '../../../core/db/local_database.dart';
import '../../../core/network/api_client.dart';
import '../../../core/util/uuid.dart';

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

/// RF11 · Avisos push en el móvil (regla 17). Hoy en modo simulado: sin cuenta de servicio de Firebase el dispositivo se registra con un identificador local
/// y el servidor deja el aviso pendiente en la campana; la app lo muestra al abrirse o al sincronizar. Con Firebase, el token de FCM ocupa el lugar de ese identificador.
class PushRepository {
  PushRepository(this._api);

  final ApiClient _api;

  /// Identificador de este dispositivo: se genera una vez y se guarda en SQLite.
  Future<String> identificadorLocal() async {
    final db = await LocalDatabase.instance.database;
    final f = await db.query('meta', where: 'clave = ?', whereArgs: ['push_dispositivo']);
    if (f.isNotEmpty) return f.first['valor'] as String;
    final nuevo = 'simulado-${generarUuid()}';
    await db.insert('meta', {'clave': 'push_dispositivo', 'valor': nuevo});
    return nuevo;
  }

  Future<void> registrarDispositivo() async =>
      _api.post('/notificaciones/dispositivos', {'canal': 'MOVIL', 'token': await identificadorLocal()});

  Future<void> quitarDispositivo() async =>
      _api.post('/notificaciones/dispositivos/baja', {'canal': 'MOVIL', 'token': await identificadorLocal()});

  Future<List<AvisoPush>> pendientes() async =>
      (await _api.getLista('/notificaciones?solo_no_leidas=true&limite=20')).map((j) => AvisoPush.desdeJson(j as Map<String, dynamic>)).toList();

  Future<void> marcarLeido(int id) async => _api.post('/notificaciones/$id/leer', {});
}
