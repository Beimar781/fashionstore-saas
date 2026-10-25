import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../auth/presentation/auth_controller.dart';

/// Pantalla inicial tras el inicio de sesión. Muestra el contexto de la sesión (empresa, rol, sucursal
/// y plan). Los paneles de catálogo, reservas y ventas se agregan en el Lote 2 sobre este contexto.
class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key});

  static const _paneles = {
    'plataforma': 'Panel de plataforma',
    'empresa': 'Panel de la empresa',
    'reservas_sucursal': 'Reservas de la sucursal',
    'punto_venta': 'Punto de venta',
    'catalogo': 'Catálogo',
  };

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthController>();
    final s = auth.sesion!;
    final esquema = Theme.of(context).colorScheme;
    return Scaffold(
      appBar: AppBar(
        title: Text(s.empresaNombre ?? 'FashionStore'),
        actions: [
          IconButton(tooltip: 'Actualizar', icon: const Icon(Icons.sync), onPressed: auth.actualizarContexto),
          IconButton(tooltip: 'Cerrar sesión', icon: const Icon(Icons.logout), onPressed: auth.cerrarSesion),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          if (auth.sinConexion)
            Card(
              color: const Color(0xFFFBEFD9),
              child: const ListTile(
                leading: Icon(Icons.cloud_off),
                title: Text('Sin conexión'),
                subtitle: Text('Se muestra el contexto guardado en el dispositivo; puede estar desactualizado.'),
              ),
            ),
          if (s.restringido)
            Card(
              color: esquema.errorContainer,
              child: ListTile(
                leading: Icon(Icons.lock, color: esquema.onErrorContainer),
                title: const Text('La suscripción de su empresa no está vigente.'),
                subtitle: const Text('Solo puede consultar su plan.'),
              ),
            ),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(s.nombreCompleto, style: Theme.of(context).textTheme.titleLarge),
                  const SizedBox(height: 4),
                  Wrap(spacing: 8, children: [
                    Chip(label: Text(s.rol)),
                    if (s.empresaCodigo != null) Chip(label: Text(s.empresaCodigo!)),
                    if (s.sucursalNombre != null) Chip(label: Text(s.sucursalNombre!)),
                  ]),
                  const Divider(height: 24),
                  _fila('Panel', _paneles[s.panel] ?? s.panel),
                  if (s.planNombre != null) ...[
                    _fila('Plan', s.planNombre!),
                    _fila('Estado de la suscripción', s.suscripcionEstado ?? '—'),
                    _fila('Vence', s.vencimiento ?? '—'),
                    _fila('Sucursales activas permitidas', '${s.maxSucursales ?? '—'}'),
                  ],
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _fila(String etiqueta, String valor) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 4),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [Text(etiqueta), Flexible(child: Text(valor, style: const TextStyle(fontWeight: FontWeight.w600), textAlign: TextAlign.end))],
        ),
      );
}
