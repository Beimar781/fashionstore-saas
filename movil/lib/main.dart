import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'core/ui/tema.dart';
import 'features/auth/data/auth_repository.dart';
import 'features/auth/presentation/auth_controller.dart';
import 'features/auth/presentation/login_screen.dart';
import 'features/home/presentation/home_screen.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const FashionStoreApp());
}

class FashionStoreApp extends StatelessWidget {
  const FashionStoreApp({super.key});

  @override
  Widget build(BuildContext context) {
    return ChangeNotifierProvider(
      create: (_) => AuthController(AuthRepository())..iniciar(),
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
