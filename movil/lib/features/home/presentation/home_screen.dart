import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../../primer_parcial/catalogo/presentation/catalogo_screen.dart';
import '../../../primer_parcial/reservas/presentation/carrito_screen.dart';
import '../../../primer_parcial/reservas/presentation/reservas_screen.dart';
import '../../../primer_parcial/ventas/presentation/pedidos_screen.dart';
import '../../auth/presentation/auth_controller.dart';
import '../../offline/presentation/modo_offline_screen.dart';
import '../../offline/presentation/offline_controller.dart';

/// Pantalla inicial tras el inicio de sesión. Muestra el contexto de la sesión (empresa, rol, sucursal y plan) y los accesos del rol:
/// el cliente ve catálogo, carrito, compras y reservas; el personal de tienda opera sin conexión (ventas de contado); todos sincronizan.
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
    final offline = context.watch<OfflineController>();
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
          if (offline.habilitado && offline.pendientes.isNotEmpty)
            Card(
              color: const Color(0xFFFBEFD9),
              child: ListTile(
                leading: const Icon(Icons.sync_problem),
                title: Text('${offline.pendientes.length} operación(es) pendiente(s) de sincronizar'),
                subtitle: const Text('Se enviarán solas al recuperar la conexión.'),
                onTap: () => _abrir(context, const ModoOfflineScreen()),
              ),
            ),
          if (offline.enConflicto.isNotEmpty)
            Card(
              color: esquema.errorContainer,
              child: ListTile(
                leading: Icon(Icons.warning_amber, color: esquema.onErrorContainer),
                title: Text('${offline.enConflicto.length} operación(es) en conflicto'),
                subtitle: const Text('No alcanzaron las existencias; el Encargado de la sucursal las resuelve.'),
                onTap: () => _abrir(context, const ModoOfflineScreen()),
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
          const SizedBox(height: 12),
          if (s.rol == 'Cliente' && !s.restringido) ...[
            _acceso(context, Icons.storefront, 'Catálogo', 'Busque prendas; sin conexión usa el catálogo descargado', const CatalogoScreen()),
            _acceso(context, Icons.shopping_cart, 'Mi carrito', 'Prendas elegidas y pago con tarjeta de prueba', const CarritoScreen()),
            _acceso(context, Icons.receipt_long, 'Mis compras', 'Historial y comprobantes', const PedidosScreen()),
            _acceso(context, Icons.event, 'Mis reservas', 'Consulte y cancele sus reservas', const ReservasScreen()),
          ],
          if (offline.habilitado && !s.restringido)
            _acceso(context, Icons.cloud_off, 'Modo sin conexión', s.rol == 'Cliente' ? 'Descargue el catálogo y reserve sin Internet' : 'Descargue el catálogo y registre ventas de contado sin Internet', const ModoOfflineScreen()),
        ],
      ),
    );
  }

  void _abrir(BuildContext context, Widget pantalla) => Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => pantalla));

  Widget _acceso(BuildContext context, IconData icono, String titulo, String detalle, Widget pantalla) => Card(
        child: ListTile(leading: Icon(icono), title: Text(titulo), subtitle: Text(detalle), trailing: const Icon(Icons.chevron_right), onTap: () => _abrir(context, pantalla)),
      );

  Widget _fila(String etiqueta, String valor) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 4),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [Text(etiqueta), Flexible(child: Text(valor, style: const TextStyle(fontWeight: FontWeight.w600), textAlign: TextAlign.end))],
        ),
      );
}
