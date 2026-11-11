import 'dart:async';

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../../primer_parcial/ia/asistente/presentation/asistente_screen.dart';
import '../../../primer_parcial/catalogo/presentation/catalogo_screen.dart';
import '../../../primer_parcial/reservas/presentation/carrito_screen.dart';
import '../../../primer_parcial/reservas/presentation/reservas_screen.dart';
import '../../../primer_parcial/ventas/presentation/pedidos_screen.dart';
import '../../../primer_parcial/reservas/data/reservas_repository.dart';
import '../../../primer_parcial/reservas/presentation/tarjetas_screen.dart';
import '../../auth/data/auth_repository.dart';
import '../../auth/data/sesion.dart';
import '../../auth/presentation/auth_controller.dart';
import '../../notificaciones/presentation/push_controller.dart';
import '../../offline/presentation/caja_en_linea_screen.dart';
import '../../offline/presentation/caja_screen.dart';
import '../../offline/presentation/conflictos_screen.dart';
import '../../offline/presentation/estado_conexion_chip.dart';
import '../../offline/presentation/modo_offline_screen.dart';
import '../../offline/presentation/tareas_sucursal_screen.dart';
import '../../offline/presentation/offline_controller.dart';
import '../../offline/presentation/operaciones_con_problema.dart';

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
    final push = context.watch<PushController>();
    final esquema = Theme.of(context).colorScheme;
    if (s.rol == 'Cliente') {
      return _InicioCliente(sesion: s, restringido: s.restringido);
    }
    return Scaffold(
      appBar: AppBar(
        title: Text(s.empresaNombre ?? 'FashionStore'),
        actions: [
          const EstadoConexionChip(),
          IconButton(
              tooltip: 'Actualizar',
              icon: const Icon(Icons.sync),
              onPressed: auth.actualizarContexto),
          IconButton(
              tooltip: 'Cerrar sesión',
              icon: const Icon(Icons.logout),
              onPressed: () => cerrarSesionConAviso(context)),
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
                subtitle: Text(
                    'Se muestra el contexto guardado en el dispositivo; puede estar desactualizado.'),
              ),
            ),
          if (s.restringido)
            Card(
              color: esquema.errorContainer,
              child: ListTile(
                leading: Icon(Icons.lock, color: esquema.onErrorContainer),
                title:
                    const Text('La suscripción de su empresa no está vigente.'),
                subtitle: const Text('Solo puede consultar su plan.'),
              ),
            ),
          if ((s.rol == 'Cajero' || s.rol == 'Encargado') && !offline.habilitado && !s.restringido)
            // el plan de la empresa no incluye el modo sin conexión: la Caja sigue disponible, pero solo con Internet
            _acceso(context, Icons.point_of_sale, 'Caja', 'Venta de contado en efectivo (su plan no incluye el modo sin conexión: necesita Internet)', const CajaEnLineaScreen()),
          if ((s.rol == 'Cajero' || s.rol == 'Encargado') && offline.habilitado && !s.restringido) ...[
            _acceso(context, Icons.point_of_sale, 'Caja', 'Venta de contado con o sin conexión, ventas del turno y su resumen', const CajaScreen()),
            _acceso(context, Icons.assignment_return_outlined, 'Devoluciones', 'Devuelva prendas con o sin conexión (plazo y lo ya devuelto)', const DevolucionesScreen()),
          ],
          for (final aviso in push.avisos)
            Card(
              color: esquema.primaryContainer,
              child: ListTile(
                leading: const Icon(Icons.notifications_active),
                title: Text(aviso.titulo),
                subtitle: Text(aviso.mensaje),
                trailing: IconButton(
                    tooltip: 'Marcar como leído',
                    icon: const Icon(Icons.check),
                    onPressed: () => push.leer(aviso)),
              ),
            ),
          if (offline.habilitado && offline.pendientes.isNotEmpty)
            Card(
              color: const Color(0xFFFBEFD9),
              child: ListTile(
                leading: const Icon(Icons.sync_problem),
                title: Text(
                    '${offline.pendientes.length} operación(es) pendiente(s) de sincronizar'),
                subtitle:
                    const Text('Se enviarán solas al recuperar la conexión.'),
                onTap: () => _abrir(context, const ModoOfflineScreen()),
              ),
            ),
          if (offline.enConflicto.isNotEmpty)
            Card(
              color: esquema.errorContainer,
              child: ListTile(
                leading:
                    Icon(Icons.warning_amber, color: esquema.onErrorContainer),
                title: Text(
                    '${offline.enConflicto.length} operación(es) en conflicto'),
                subtitle: const Text(
                    'No alcanzaron las existencias; el Encargado de la sucursal las resuelve.'),
                onTap: () => _abrir(context, const ModoOfflineScreen()),
              ),
            ),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(s.nombreCompleto,
                      style: Theme.of(context).textTheme.titleLarge),
                  const SizedBox(height: 4),
                  Wrap(spacing: 8, children: [
                    Chip(label: Text(s.rol)),
                    if (s.empresaCodigo != null)
                      Chip(label: Text(s.empresaCodigo!)),
                    if (s.sucursalNombre != null)
                      Chip(label: Text(s.sucursalNombre!)),
                  ]),
                  const Divider(height: 24),
                  _fila('Panel', _paneles[s.panel] ?? s.panel),
                  if (s.planNombre != null) ...[
                    _fila('Plan', s.planNombre!),
                    _fila(
                        'Estado de la suscripción', s.suscripcionEstado ?? '—'),
                    _fila('Vence', s.vencimiento ?? '—'),
                    _fila('Sucursales activas permitidas',
                        '${s.maxSucursales ?? '—'}'),
                  ],
                ],
              ),
            ),
          ),
          const SizedBox(height: 12),
          if (s.rol == 'Cliente' && !s.restringido) ...[
            _acceso(
                context,
                Icons.storefront,
                'Catálogo',
                'Busque prendas; sin conexión usa el catálogo descargado',
                const CatalogoScreen()),
            _acceso(
                context,
                Icons.shopping_cart,
                'Mi carrito',
                'Prendas elegidas y pago con tarjeta de prueba',
                const CarritoScreen()),
            _acceso(context, Icons.receipt_long, 'Mis compras',
                'Historial y comprobantes', const PedidosScreen()),
            _acceso(
                context,
                Icons.event,
                'Mis reservas',
                'Reserve prendas, consúltelas y cancélelas',
                const ReservasScreen()),
            if (s.iaHabilitada)
              _acceso(
                  context,
                  Icons.auto_awesome,
                  'Asistente de compras',
                  'Pida prendas en lenguaje natural (plan Profesional)',
                  const AsistenteScreen()),
          ],
          if ((s.rol == 'Cajero' || s.rol == 'Encargado') && offline.habilitado && !s.restringido) ...[
            if (s.rol == 'Encargado') _acceso(context, Icons.assignment_outlined, 'Tareas de la sucursal', 'Recepción, ajuste de inventario y reservas, con o sin conexión', const TareasSucursalScreen()),
            if (s.rol == 'Encargado') _acceso(context, Icons.warning_amber_outlined, 'Conflictos de sincronización', 'Reintente o descarte lo que no alcanzó en el inventario (con conexión)', const ConflictosScreen()),
          ],
          if (!const ['Cliente', 'Cajero', 'Encargado'].contains(s.rol))
            // Proveedor, Administrador y SuperAdministrador trabajan en la web; en la app solo ven su contexto guardado (nunca un spinner infinito)
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text(offline.enLinea && !auth.sinConexion ? 'Las funciones de su rol se usan desde la web de FashionStore.' : 'Esta función necesita Internet.', style: Theme.of(context).textTheme.titleMedium),
                  const SizedBox(height: 4),
                  Text(offline.enLinea && !auth.sinConexion
                      ? 'Ingrese a la web con esta misma cuenta para gestionar su panel. Aquí puede consultar su plan y su estado de suscripción.'
                      : 'Sin conexión se muestra el contexto guardado en este dispositivo (plan, estado y vencimiento); puede estar desactualizado.'),
                  const SizedBox(height: 8),
                  FilledButton.icon(
                      onPressed: offline.enLinea && !auth.sinConexion ? auth.actualizarContexto : null,
                      icon: const Icon(Icons.sync),
                      label: const Text('Actualizar mi plan')),
                ]),
              ),
            ),
          if (s.rol == 'Cajero' || s.rol == 'Encargado') const OperacionesConProblema(tipos: ['VENTA_CONTADO'], titulo: 'Ventas con problema'),
          const InterruptorSimulacion(),
          if (offline.habilitado && !s.restringido)
            _acceso(
                context,
                Icons.cloud_off,
                s.rol == 'Cliente' ? 'Modo sin conexión' : 'Diagnóstico sin conexión',
                s.rol == 'Cliente'
                    ? 'Descargue el catálogo y reserve sin Internet'
                    : 'Diagnóstico: catálogo descargado, cola y registro de sincronización',
                const ModoOfflineScreen()),
        ],
      ),
    );
  }

  void _abrir(BuildContext context, Widget pantalla) => Navigator.of(context)
      .push(MaterialPageRoute<void>(builder: (_) => pantalla));

  Widget _acceso(BuildContext context, IconData icono, String titulo,
          String detalle, Widget pantalla) =>
      Card(
        child: ListTile(
            leading: Icon(icono),
            title: Text(titulo),
            subtitle: Text(detalle),
            trailing: const Icon(Icons.chevron_right),
            onTap: () => _abrir(context, pantalla)),
      );

  Widget _fila(String etiqueta, String valor) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 4),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Flexible(child: Text(etiqueta)),
            const SizedBox(width: 12),
            Flexible(
                child: Text(valor,
                    style: const TextStyle(fontWeight: FontWeight.w600),
                    textAlign: TextAlign.end))
          ],
        ),
      );
}

class _InicioCliente extends StatefulWidget {
  const _InicioCliente({required this.sesion, required this.restringido});
  final Sesion sesion;
  final bool restringido;
  @override
  State<_InicioCliente> createState() => _InicioClienteState();
}

class _InicioClienteState extends State<_InicioCliente> {
  int _pestana = 0;
  int _carrito = 0;
  Timer? _relojCarrito;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _actualizarCarrito());
    _relojCarrito = Timer.periodic(
        const Duration(seconds: 20), (_) => _actualizarCarrito());
  }

  @override
  void dispose() {
    _relojCarrito?.cancel();
    super.dispose();
  }

  Future<void> _actualizarCarrito() async {
    try {
      final carrito =
          await ReservasRepository(context.read<AuthRepository>().api)
              .carrito();
      if (mounted) {
        setState(() => _carrito = (((carrito['items'] as List?) ?? const [])
                .cast<Map<String, dynamic>>())
            .fold<int>(
                0,
                (suma, item) =>
                    suma + ((item['cantidad'] as num?)?.toInt() ?? 0)));
      }
    } catch (_) {}
  }

  @override
  Widget build(BuildContext context) {
    final s = widget.sesion;
    final push = context.watch<PushController>();
    final offline = context.watch<OfflineController>();
    final soloPerfil = widget.restringido;
    final pantallas = <Widget>[
      CatalogoScreen(integrado: true, nombreEmpresa: s.empresaNombre),
      CatalogoScreen(
          integrado: true,
          soloPromociones: true,
          nombreEmpresa: s.empresaNombre),
      const ReservasScreen(integrado: true),
      const PedidosScreen(integrado: true),
      _PerfilCliente(sesion: s),
    ];
    return Scaffold(
      appBar: AppBar(title: Text(s.empresaNombre ?? 'FashionStore'), actions: [
        const EstadoConexionChip(),
        if (!soloPerfil) ...[
          IconButton(
              tooltip: 'Avisos',
              onPressed: () => _abrir(context, const _AvisosScreen()),
              icon: Badge(
                  isLabelVisible: push.avisos.isNotEmpty,
                  label: Text('${push.avisos.length}'),
                  child: const Icon(Icons.notifications_outlined))),
          IconButton(
              tooltip: 'Carrito',
              onPressed: () async {
                await _abrir(context, const CarritoScreen());
                _actualizarCarrito();
              },
              icon: Badge(
                  isLabelVisible: _carrito > 0,
                  label: Text('$_carrito'),
                  child: const Icon(Icons.shopping_cart_outlined))),
        ],
      ]),
      body: Stack(children: [
        IndexedStack(index: soloPerfil ? 4 : _pestana, children: pantallas),
        if (!soloPerfil && _pestana == 0 && s.iaHabilitada)
          Positioned(
              right: 16,
              bottom: 16,
              child: FloatingActionButton.small(
                  tooltip: 'Asistente de compras',
                  onPressed: () => _abrir(context, const AsistenteScreen()),
                  child: const Icon(Icons.auto_awesome))),
        if (!soloPerfil &&
            offline.habilitado &&
            (!offline.enLinea ||
                offline.pendientes.isNotEmpty ||
                offline.enConflicto.isNotEmpty))
          Positioned(
              left: 12,
              right: 12,
              top: 8,
              child: _AvisosOffline(offline: offline)),
      ]),
      bottomNavigationBar: soloPerfil
          ? null
          : NavigationBar(
              selectedIndex: _pestana,
              onDestinationSelected: (i) => setState(() => _pestana = i),
              destinations: const [
                  NavigationDestination(
                      icon: Icon(Icons.home_outlined),
                      selectedIcon: Icon(Icons.home),
                      label: 'Inicio'),
                  NavigationDestination(
                      icon: Icon(Icons.local_offer_outlined),
                      label: 'Promociones'),
                  NavigationDestination(
                      icon: Icon(Icons.event_outlined), label: 'Reservas'),
                  NavigationDestination(
                      icon: Icon(Icons.receipt_long_outlined),
                      label: 'Compras'),
                  NavigationDestination(
                      icon: Icon(Icons.person_outline), label: 'Perfil'),
                ]),
    );
  }

  Future<void> _abrir(BuildContext context, Widget pantalla) =>
      Navigator.of(context)
          .push(MaterialPageRoute<void>(builder: (_) => pantalla));
}

class _PerfilCliente extends StatelessWidget {
  const _PerfilCliente({required this.sesion});
  final dynamic sesion;
  @override
  Widget build(BuildContext context) {
    final offline = context.watch<OfflineController>();
    final auth = context.read<AuthController>();
    return ListView(
        padding: EdgeInsets.fromLTRB(
            16, 16, 16, MediaQuery.viewPaddingOf(context).bottom + 20),
        children: [
          Card(
              child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(children: [
                          Expanded(
                              child: Text(sesion.nombreCompleto,
                                  style:
                                      Theme.of(context).textTheme.titleLarge)),
                          IconButton(
                              tooltip: 'Actualizar',
                              icon: const Icon(Icons.sync),
                              onPressed: auth.actualizarContexto),
                        ]),
                        Text(
                            '${sesion.rol} · ${sesion.empresaCodigo ?? ''} · ${sesion.sucursalNombre ?? 'Sin sucursal'}'),
                        const Divider(),
                        Text('Panel: ${sesion.panel}'),
                        Text('Plan: ${sesion.planNombre ?? '—'}'),
                        Text('Estado: ${sesion.suscripcionEstado ?? '—'}'),
                        Text('Vence: ${sesion.vencimiento ?? '—'}'),
                        Text(
                            'Sucursales permitidas: ${sesion.maxSucursales ?? '—'}'),
                        if (sesion.restringido)
                          const Padding(
                              padding: EdgeInsets.only(top: 8),
                              child: Text(
                                  'La suscripción de su empresa no está vigente. Solo puede consultar su plan.')),
                      ]))),
          if (!sesion.restringido && offline.habilitado)
            _acceso(context, Icons.cloud_off, 'Modo sin conexión',
                const ModoOfflineScreen()),
          if (!sesion.restringido && sesion.iaHabilitada)
            _acceso(context, Icons.auto_awesome, 'Asistente de compras',
                const AsistenteScreen()),
          if (!sesion.restringido)
            _acceso(context, Icons.credit_card, 'Tarjetas guardadas',
                const TarjetasScreen()),
          const InterruptorSimulacion(),
          Card(
              child: ListTile(
                  leading: const Icon(Icons.logout),
                  title: const Text('Cerrar sesión'),
                  onTap: () => cerrarSesionConAviso(context))),
        ]);
  }

  Widget _acceso(BuildContext context, IconData icono, String titulo,
          Widget pantalla) =>
      Card(
          child: ListTile(
              leading: Icon(icono),
              title: Text(titulo),
              trailing: const Icon(Icons.chevron_right),
              onTap: () => Navigator.of(context)
                  .push(MaterialPageRoute<void>(builder: (_) => pantalla))));
}

class _AvisosOffline extends StatelessWidget {
  const _AvisosOffline({required this.offline});
  final OfflineController offline;
  @override
  Widget build(BuildContext context) => Card(
      color: const Color(0xFFFBEFD9),
      child: ListTile(
          dense: true,
          leading:
              Icon(!offline.enLinea ? Icons.cloud_off : Icons.sync_problem),
          title: Text(!offline.enLinea
              ? (offline.simulado ? 'Modo sin conexión simulado' : 'Sin conexión')
              : offline.enConflicto.isNotEmpty
                  ? '${offline.enConflicto.length} operación(es) en conflicto'
                  : '${offline.pendientes.length} operación(es) pendiente(s)'),
          subtitle: Text(offline.pendientes.isNotEmpty ||
                  offline.enConflicto.isNotEmpty
              ? 'Consulte las operaciones en Perfil → Modo sin conexión.'
              : 'Datos al ${fechaCorta(offline.catalogoGeneradoEn)}; pueden estar desactualizados. Se muestra el catálogo guardado hasta recuperar la red.')));
}

class _AvisosScreen extends StatelessWidget {
  const _AvisosScreen();
  @override
  Widget build(BuildContext context) {
    final push = context.watch<PushController>();
    return Scaffold(
        appBar: AppBar(title: const Text('Avisos'), actions: [
          TextButton(
              onPressed: () async {
                for (final a in [...push.avisos]) {
                  await push.leer(a);
                }
              },
              child: const Text('Marcar todos'))
        ]),
        body: push.avisos.isEmpty
            ? const Center(child: Text('No hay avisos nuevos.'))
            : ListView(
                padding: EdgeInsets.fromLTRB(
                    12, 12, 12, MediaQuery.viewPaddingOf(context).bottom + 16),
                children: [
                    for (final a in push.avisos)
                      Card(
                          color: Theme.of(context).colorScheme.primaryContainer,
                          child: ListTile(
                              leading: const Icon(Icons.notifications_active),
                              title: Text(a.titulo),
                              subtitle: Text(a.mensaje),
                              trailing: IconButton(
                                  tooltip: 'Marcar como leído',
                                  icon: const Icon(Icons.check),
                                  onPressed: () => push.leer(a))))
                  ]));
  }
}

/// §5.4: cerrar sesión nunca borra operaciones. Si hay pendientes, se avisa que se conservan en este dispositivo (ligadas a este usuario y empresa).
Future<void> cerrarSesionConAviso(BuildContext context) async {
  final auth = context.read<AuthController>();
  final pendientes = context.read<OfflineController>().pendientes.length;
  if (pendientes > 0) {
    final seguir = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('¿Cerrar sesión?'),
        content: Text('Tiene $pendientes operaciones sin sincronizar. Se conservarán en este dispositivo.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancelar')),
          FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Sí, cerrar sesión')),
        ],
      ),
    );
    if (seguir != true) return;
  }
  await auth.cerrarSesion();
}

/// §B11 · «Simular sin conexión»: fuerza el modo sin conexión aunque haya Internet, para demostrar el offline sin apagar el WiFi. Visible para todos los roles.
class InterruptorSimulacion extends StatelessWidget {
  const InterruptorSimulacion({super.key});

  @override
  Widget build(BuildContext context) {
    final offline = context.watch<OfflineController>();
    return Card(
      child: SwitchListTile(
        secondary: const Icon(Icons.airplanemode_active),
        title: const Text('Simular sin conexión'),
        subtitle: Text(offline.simulado ? 'Modo sin conexión simulado: apáguelo para sincronizar.' : 'Fuerza el modo sin conexión aunque haya Internet.'),
        value: offline.simulado,
        onChanged: offline.simularSinConexion,
      ),
    );
  }
}
