import 'package:flutter_local_notifications/flutter_local_notifications.dart';

/// Notificación local del sistema (sin Internet ni Firebase). La usa el modo sin conexión para avisar, con la app en segundo plano,
/// que se perdió o volvió la red y cómo terminó la sincronización. Si el sistema no la permite, simplemente no se muestra.
class NotificacionLocal {
  static final FlutterLocalNotificationsPlugin _plugin = FlutterLocalNotificationsPlugin();
  static bool _lista = false;
  static int _siguienteId = 5000;

  static Future<void> mostrar(String texto) async {
    try {
      if (!_lista) {
        await _plugin.initialize(settings: const InitializationSettings(android: AndroidInitializationSettings('@mipmap/ic_launcher')));
        _lista = true;
      }
      await _plugin.show(
        id: _siguienteId++,
        title: 'FashionStore',
        body: texto,
        notificationDetails: const NotificationDetails(
          android: AndroidNotificationDetails('avisos', 'Avisos de FashionStore', channelDescription: 'Devoluciones, cambios y compras', importance: Importance.high, priority: Priority.high),
        ),
      );
    } catch (_) {
      // sin permiso o sin soporte: el aviso queda dentro de la app
    }
  }
}
