import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';

import 'core/network/conectividad.dart';
import 'core/ui/tema.dart';
import 'core/ui/area_segura.dart';
import 'features/auth/data/auth_repository.dart';
import 'features/auth/presentation/auth_controller.dart';
import 'features/auth/presentation/login_screen.dart';
import 'features/home/presentation/home_screen.dart';
import 'features/offline/data/offline_repository.dart';
import 'features/notificaciones/data/proveedor_push.dart';
import 'features/notificaciones/data/push_repository.dart';
import 'core/notificacion_local.dart';
import 'features/notificaciones/presentation/push_controller.dart';
import 'features/offline/presentation/conflictos_screen.dart';
import 'features/offline/presentation/modo_offline_screen.dart';
import 'features/offline/presentation/offline_controller.dart';
import 'primer_parcial/reservas/data/reserva_borrador.dart';

final _mensajero = GlobalKey<ScaffoldMessengerState>();
final _navegador = GlobalKey<NavigatorState>();

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  SystemChrome.setEnabledSystemUIMode(SystemUiMode.edgeToEdge);
  SystemChrome.setSystemUIOverlayStyle(const SystemUiOverlayStyle(
    systemNavigationBarColor: Tema.tinta,
    systemNavigationBarIconBrightness: Brightness.light,
    systemNavigationBarContrastEnforced: true,
    statusBarColor: Tema.tinta,
    statusBarIconBrightness: Brightness.light,
  ));
  final authRepo = AuthRepository();
  runApp(FashionStoreApp(
      authRepo: authRepo,
      pushRepo: PushRepository(authRepo.api, proveedor: ProveedorFirebase())));
}

class FashionStoreApp extends StatelessWidget {
  const FashionStoreApp(
      {super.key, required this.authRepo, required this.pushRepo});

  final AuthRepository authRepo;
  final PushRepository pushRepo;

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        Provider<AuthRepository>.value(value: authRepo),
        ChangeNotifierProvider(
            create: (_) => AuthController(authRepo,
                antesDeCerrarSesion: pushRepo.quitarDispositivo)
              ..iniciar()),
        // el modo sin conexión sigue a la sesión: al iniciar sesión sincroniza lo pendiente y reintenta mientras haya operaciones sin enviar
        ChangeNotifierProxyProvider<AuthController, OfflineController>(
          create: (_) => OfflineController(OfflineRepository(authRepo.api),
              conectividad: conectividadDelDispositivo(), descargaAutomatica: true)
            ..alNotificar = NotificacionLocal.mostrar
            ..alResumir = (texto, {bool conflicto = false}) {
              _mensajero.currentState
                ?..hideCurrentSnackBar()
                ..showSnackBar(SnackBar(
                  content: Text(texto),
                  duration: const Duration(seconds: 5),
                  action: SnackBarAction(
                      label: 'Ver detalle',
                      onPressed: () => _navegador.currentState?.push(MaterialPageRoute<void>(builder: (_) => conflicto ? const ConflictosScreen() : const ModoOfflineScreen(pestana: 2))))));
            }
            ..alAvisar = (texto) {
              _mensajero.currentState?.hideCurrentSnackBar();
              _mensajero.currentState?.showSnackBar(SnackBar(content: Text(texto), duration: const Duration(seconds: 5)));
            },
          update: (_, auth, offline) {
            if (auth.sesion == null) _mensajero.currentState?.clearSnackBars(); // al cerrar sesión no queda ningún aviso (ni en el Login)
            return offline!..usarSesion(auth.sesion);
          },
        ),
        // las prendas elegidas para reservar se guardan por usuario
        ChangeNotifierProxyProvider<AuthController, ReservaBorrador>(
          create: (_) => ReservaBorrador(),
          update: (_, auth, borrador) =>
              borrador!..usarUsuario(auth.sesion?.usuarioId),
        ),
        // avisos push: con Firebase el token de FCM se registra al iniciar sesión y la notificación es nativa; sin Firebase (modo simulado) los avisos se muestran en el inicio
        ChangeNotifierProxyProvider<AuthController, PushController>(
          create: (_) => PushController(pushRepo),
          update: (_, auth, push) => push!..usarSesion(auth.sesion),
        ),
      ],
      child: MaterialApp(
        scaffoldMessengerKey: _mensajero,
        navigatorKey: _navegador,
        title: 'FashionStore',
        debugShowCheckedModeBanner: false,
        theme: Tema.claro(),
        builder: (context, child) =>
            AreaSeguraAplicacion(child: child ?? const SizedBox.shrink()),
        home: const _Raiz(),
      ),
    );
  }
}

/// Decide la pantalla según la sesión (guardada en SQLite): login o inicio.
class _Raiz extends StatelessWidget {
  const _Raiz();

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthController>();
    if (auth.iniciando) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }
    return auth.sesion == null ? const LoginScreen() : const HomeScreen();
  }
}
