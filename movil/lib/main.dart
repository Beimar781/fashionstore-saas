import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'core/ui/tema.dart';
import 'features/auth/data/auth_repository.dart';
import 'features/auth/presentation/auth_controller.dart';
import 'features/auth/presentation/login_screen.dart';
import 'features/home/presentation/home_screen.dart';
import 'features/offline/data/offline_repository.dart';
import 'features/notificaciones/data/push_repository.dart';
import 'features/notificaciones/presentation/push_controller.dart';
import 'features/offline/presentation/offline_controller.dart';

final _mensajero = GlobalKey<ScaffoldMessengerState>();

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(FashionStoreApp(authRepo: AuthRepository()));
}

class FashionStoreApp extends StatelessWidget {
  const FashionStoreApp({super.key, required this.authRepo});

  final AuthRepository authRepo;

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        Provider<AuthRepository>.value(value: authRepo),
        ChangeNotifierProvider(create: (_) => AuthController(authRepo, antesDeCerrarSesion: PushRepository(authRepo.api).quitarDispositivo)..iniciar()),
        // el modo sin conexión sigue a la sesión: al iniciar sesión sincroniza lo pendiente y reintenta mientras haya operaciones sin enviar
        ChangeNotifierProxyProvider<AuthController, OfflineController>(
          create: (_) => OfflineController(OfflineRepository(authRepo.api))..alAvisar = (texto) => _mensajero.currentState?.showSnackBar(SnackBar(content: Text(texto), duration: const Duration(seconds: 8))),
          update: (_, auth, offline) => offline!..usarSesion(auth.sesion),
        ),
        // avisos push (modo simulado): el dispositivo se registra al iniciar sesión y los avisos pendientes se muestran en el inicio
        ChangeNotifierProxyProvider<AuthController, PushController>(
          create: (_) => PushController(PushRepository(authRepo.api)),
          update: (_, auth, push) => push!..usarSesion(auth.sesion),
        ),
      ],
      child: MaterialApp(
        scaffoldMessengerKey: _mensajero,
        title: 'FashionStore',
        debugShowCheckedModeBanner: false,
        theme: Tema.claro(),
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
