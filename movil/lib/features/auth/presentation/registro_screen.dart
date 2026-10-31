import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../../core/network/api_client.dart';
import '../data/auth_repository.dart';
import '../data/registro_cliente.dart';

/// CU-01 · Crear cuenta de cliente. Al terminar vuelve al login con el código y el correo ya escritos.
class RegistroScreen extends StatefulWidget {
  const RegistroScreen({super.key});

  @override
  State<RegistroScreen> createState() => _RegistroScreenState();
}

class _RegistroScreenState extends State<RegistroScreen> {
  final _formulario = GlobalKey<FormState>();
  final _codigo = TextEditingController();
  final _nombre = TextEditingController();
  final _apellidos = TextEditingController();
  final _email = TextEditingController();
  final _password = TextEditingController();
  bool _ocultar = true;
  bool _creando = false;
  String? _error;

  @override
  void dispose() {
    for (final c in [_codigo, _nombre, _apellidos, _email, _password]) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> _crear() async {
    if (!_formulario.currentState!.validate()) return;
    setState(() { _creando = true; _error = null; });
    try {
      await context.read<AuthRepository>().registrarCliente(RegistroCliente(
            codigoEmpresa: _codigo.text,
            nombre: _nombre.text,
            apellidos: _apellidos.text,
            email: _email.text,
            password: _password.text,
          ));
      if (mounted) Navigator.pop(context, (_codigo.text.trim(), _email.text.trim()));
      return;
    } on ApiException catch (e) {
      if (mounted) setState(() => _error = e.sinConexion ? 'Sin conexión: crear la cuenta necesita Internet.' : e.mensaje);
    }
    if (mounted) setState(() => _creando = false);
  }

  @override
  Widget build(BuildContext context) {
    final esquema = Theme.of(context).colorScheme;
    return Scaffold(
      appBar: AppBar(title: const Text('Crear cuenta de cliente')),
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 420),
              child: Form(
                key: _formulario,
                child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                  const Text('Pida el código de la tienda en la que desea comprar. Su cuenta solo existirá en esa tienda.'),
                  const SizedBox(height: 16),
                  TextFormField(
                    controller: _codigo,
                    textCapitalization: TextCapitalization.characters,
                    decoration: const InputDecoration(labelText: 'Código de la tienda', hintText: 'EMP-A'),
                    validator: RegistroCliente.validarCodigo,
                  ),
                  const SizedBox(height: 12),
                  TextFormField(controller: _nombre, decoration: const InputDecoration(labelText: 'Nombre'), validator: RegistroCliente.validarNombre),
                  const SizedBox(height: 12),
                  TextFormField(controller: _apellidos, decoration: const InputDecoration(labelText: 'Apellidos')),
                  const SizedBox(height: 12),
                  TextFormField(
                    controller: _email,
                    keyboardType: TextInputType.emailAddress,
                    decoration: const InputDecoration(labelText: 'Correo'),
                    validator: RegistroCliente.validarEmail,
                  ),
                  const SizedBox(height: 12),
                  TextFormField(
                    controller: _password,
                    obscureText: _ocultar,
                    decoration: InputDecoration(
                      labelText: 'Contraseña (mínimo 8 caracteres)',
                      suffixIcon: IconButton(icon: Icon(_ocultar ? Icons.visibility : Icons.visibility_off), onPressed: () => setState(() => _ocultar = !_ocultar)),
                    ),
                    validator: RegistroCliente.validarPassword,
                    onFieldSubmitted: (_) => _crear(),
                  ),
                  if (_error != null) ...[
                    const SizedBox(height: 12),
                    Container(
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(color: esquema.errorContainer, borderRadius: BorderRadius.circular(10)),
                      child: Text(_error!, style: TextStyle(color: esquema.onErrorContainer)),
                    ),
                  ],
                  const SizedBox(height: 16),
                  FilledButton(
                    onPressed: _creando ? null : _crear,
                    child: _creando ? const SizedBox(width: 22, height: 22, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white)) : const Text('Crear cuenta'),
                  ),
                ]),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
