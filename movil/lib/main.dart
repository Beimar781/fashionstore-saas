import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'core/ui/tema.dart';
import 'features/auth/data/auth_repository.dart';
import 'features/auth/presentation/auth_controller.dart';
import 'features/auth/presentation/login_screen.dart';
import 'features/home/presentation/home_screen.dart';
import 'features/offline/data/offline_repository.dart';
import 'features/offline/presentation/offline_controller.dart';

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
        ChangeNotifierProvider(create: (_) => AuthController(authRepo)..iniciar()),
        // el modo sin conexión sigue a la sesión: al iniciar sesión sincroniza lo pendiente y reintenta mientras haya operaciones sin enviar
        ChangeNotifierProxyProvider<AuthController, OfflineController>(
          create: (_) => OfflineController(OfflineRepository(authRepo.api)),
          update: (_, auth, offline) => offline!..usarSesion(auth.sesion),
        ),
      ],
      child: MaterialApp(
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
