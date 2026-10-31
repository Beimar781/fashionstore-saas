import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../../core/network/api_client.dart';
import '../data/auth_repository.dart';
import 'auth_controller.dart';
import 'registro_screen.dart';

/// CU-02 · Inicio de sesión con código de empresa, correo y contraseña.
class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _formulario = GlobalKey<FormState>();
  final _codigo = TextEditingController();
  final _email = TextEditingController();
  final _password = TextEditingController();
  bool _ocultar = true;

  static const _demo = <(String, String, String, String)>[
    ('SuperAdmin', '', 'superadmin@fashionstore.com', 'Super2026*'),
    ('Admin EMP-A', 'EMP-A', 'admin@modaurbana.com', 'Demo2026*'),
    ('Cajero EMP-A', 'EMP-A', 'cajero@tienda.com', 'Demo2026*'),
    ('Cajero EMP-B', 'EMP-B', 'cajero@tienda.com', 'Demo2026*'),
  ];

  @override
  void dispose() {
    _codigo.dispose();
    _email.dispose();
    _password.dispose();
    super.dispose();
  }

  Future<void> _entrar() async {
    if (!_formulario.currentState!.validate()) return;
    await context.read<AuthController>().iniciarSesion(
          codigoEmpresa: _codigo.text,
          email: _email.text,
          password: _password.text,
        );
  }

  /// CU-01: abre «Crear cuenta»; al volver con la cuenta creada deja el código y el correo escritos para iniciar sesión.
  Future<void> _crearCuenta() async {
    final mensajes = ScaffoldMessenger.of(context);
    final creada = await Navigator.push<(String, String)>(context, MaterialPageRoute(builder: (_) => const RegistroScreen()));
    if (creada == null || !mounted) return;
    setState(() {
      _codigo.text = creada.$1;
      _email.text = creada.$2;
      _password.clear();
    });
    mensajes.showSnackBar(const SnackBar(content: Text('Cuenta creada. Ingrese con su contraseña.')));
  }

  /// Pide al servidor el correo para restablecer la contraseña con el código de empresa y el correo escritos en el formulario.
  Future<void> _olvideMiPassword() async {
    final mensajes = ScaffoldMessenger.of(context);
    if (!_email.text.contains('@')) {
      mensajes.showSnackBar(const SnackBar(content: Text('Escriba su correo para enviarle el enlace de restablecimiento.')));
      return;
    }
    try {
      final detalle = await context.read<AuthRepository>().olvidePassword(codigoEmpresa: _codigo.text, email: _email.text);
      mensajes.showSnackBar(SnackBar(content: Text(detalle)));
    } on ApiException catch (e) {
      mensajes.showSnackBar(SnackBar(content: Text(e.mensaje)));
    }
  }

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthController>();
    final esquema = Theme.of(context).colorScheme;
    return Scaffold(
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 420),
              child: Form(
                key: _formulario,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Container(
                      width: 60,
                      height: 60,
                      alignment: Alignment.center,
                      decoration: BoxDecoration(color: esquema.primary, borderRadius: BorderRadius.circular(16)),
                      child: const Text('F',
                          style: TextStyle(color: Colors.white, fontSize: 32, fontWeight: FontWeight.w600, fontFamily: 'serif')),
                    ),
                    const SizedBox(height: 16),
                    Text('FashionStore', style: Theme.of(context).textTheme.headlineMedium?.copyWith(fontFamily: 'serif', fontWeight: FontWeight.w600)),
                    const SizedBox(height: 4),
                    const Text('Ingrese el código de su empresa. El SuperAdministrador lo deja vacío.'),
                    const SizedBox(height: 20),
                    TextFormField(
                      controller: _codigo,
                      decoration: const InputDecoration(labelText: 'Código de empresa', hintText: 'EMP-A'),
                      textCapitalization: TextCapitalization.characters,
                      autofillHints: const [AutofillHints.organizationName],
                    ),
                    const SizedBox(height: 12),
                    TextFormField(
                      controller: _email,
                      decoration: const InputDecoration(labelText: 'Correo'),
                      keyboardType: TextInputType.emailAddress,
                      autofillHints: const [AutofillHints.username],
                      validator: (v) => (v == null || !v.contains('@')) ? 'Ingrese un correo válido' : null,
                    ),
                    const SizedBox(height: 12),
                    TextFormField(
                      controller: _password,
                      obscureText: _ocultar,
                      decoration: InputDecoration(
                        labelText: 'Contraseña',
                        suffixIcon: IconButton(
                          icon: Icon(_ocultar ? Icons.visibility : Icons.visibility_off),
                          onPressed: () => setState(() => _ocultar = !_ocultar),
                        ),
                      ),
                      validator: (v) => (v == null || v.isEmpty) ? 'Ingrese su contraseña' : null,
                      onFieldSubmitted: (_) => _entrar(),
                    ),
                    if (auth.error != null) ...[
                      const SizedBox(height: 12),
                      Container(
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(color: esquema.errorContainer, borderRadius: BorderRadius.circular(10)),
                        child: Text(auth.error!, style: TextStyle(color: esquema.onErrorContainer)),
                      ),
                    ],
                    Align(
                      alignment: Alignment.centerRight,
                      child: TextButton(onPressed: _olvideMiPassword, child: const Text('¿Olvidó su contraseña?')),
                    ),
                    const SizedBox(height: 4),
                    FilledButton(
                      onPressed: auth.cargando ? null : _entrar,
                      child: auth.cargando
                          ? const SizedBox(width: 22, height: 22, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                          : const Text('Ingresar'),
                    ),
                    TextButton(onPressed: _crearCuenta, child: const Text('¿No tiene cuenta? Crear cuenta')),
                    if (kDebugMode) ...[
                      const SizedBox(height: 20),
                      const Text('Cuentas de demostración (solo en desarrollo)', style: TextStyle(fontSize: 12)),
                      const SizedBox(height: 6),
                      Wrap(
                        spacing: 8,
                        children: [
                          for (final c in _demo)
                            ActionChip(
                              label: Text(c.$1),
                              onPressed: () => setState(() {
                                _codigo.text = c.$2;
                                _email.text = c.$3;
                                _password.text = c.$4;
                              }),
                            ),
                        ],
                      ),
                    ],
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
