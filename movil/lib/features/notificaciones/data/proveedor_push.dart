import 'dart:async';

import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';

/// De dónde sale el identificador del dispositivo para los avisos push. Con Firebase es el token de FCM; sin Firebase (modo simulado) no hay proveedor
/// y `PushRepository` usa un identificador local. Así la lógica de registro se prueba sin Firebase.
abstract class ProveedorPush {
  /// Inicia el servicio y pide el permiso de notificaciones. Devuelve el token, o null si no hay Firebase o el usuario negó el permiso.
  /// `alRecibir` se llama cuando llega un aviso con la app abierta (para actualizar la campana).
  Future<String?> iniciar({required void Function() alRecibir});

  /// Firebase renueva el token de vez en cuando: hay que volver a registrarlo en el servidor.
  Stream<String> get tokenRenovado;
}

/// Firebase Cloud Messaging. Con la app cerrada o en segundo plano, Android muestra la notificación solo; con la app abierta se muestra con
/// `flutter_local_notifications`. El canal «avisos» (importancia alta) es el mismo que nombra el backend en cada mensaje.
class ProveedorFirebase implements ProveedorPush {
  static const canal = AndroidNotificationChannel('avisos', 'Avisos de FashionStore', description: 'Devoluciones, cambios y compras', importance: Importance.high);

  final FlutterLocalNotificationsPlugin _local = FlutterLocalNotificationsPlugin();
  int _siguienteId = 0;

  final StreamController<String> _renovado = StreamController<String>.broadcast();
  bool _preparado = false;

  @override
  Stream<String> get tokenRenovado => _renovado.stream;

  // getToken y onTokenRefresh figuran como obsoletos, pero siguen entregando el token de registro clásico que acepta la API HTTP v1 del backend (`message.token`);
  // el reemplazo (register y onRegistered) entrega un Firebase Installation ID, otro tipo de destino.
  @override
  Future<String?> iniciar({required void Function() alRecibir}) async {
    try {
      if (!_preparado) {
        await Firebase.initializeApp(); // lee google-services.json (el plugin de Gradle solo existe si el archivo estaba al compilar)
        await _local.initialize(settings: const InitializationSettings(android: AndroidInitializationSettings('@mipmap/ic_launcher')));
        await _local.resolvePlatformSpecificImplementation<AndroidFlutterLocalNotificationsPlugin>()?.createNotificationChannel(canal);
        FirebaseMessaging.onMessage.listen((m) {
          final n = m.notification;
          if (n != null) _mostrar(n.title ?? 'FashionStore', n.body ?? '');
          alRecibir();
        });
        // ignore: deprecated_member_use
        FirebaseMessaging.instance.onTokenRefresh.listen(_renovado.add);
        _preparado = true;
      }
      final permiso = await FirebaseMessaging.instance.requestPermission(); // Android 13: pide POST_NOTIFICATIONS
      if (permiso.authorizationStatus == AuthorizationStatus.denied) return null;
      // ignore: deprecated_member_use
      return await FirebaseMessaging.instance.getToken();
    } catch (_) {
      return null; // sin Firebase la app sigue en modo simulado: los avisos aparecen dentro de la app
    }
  }

  Future<void> _mostrar(String titulo, String cuerpo) => _local.show(
        id: _siguienteId++,
        title: titulo,
        body: cuerpo,
        notificationDetails: NotificationDetails(
          android: AndroidNotificationDetails(canal.id, canal.name, channelDescription: canal.description, importance: Importance.high, priority: Priority.high),
        ),
      );
}
