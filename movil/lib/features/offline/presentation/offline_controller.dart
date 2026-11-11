import 'dart:async';

import 'package:flutter/widgets.dart' show AppLifecycleState, WidgetsBinding, WidgetsBindingObserver;

import 'package:flutter/foundation.dart';

import '../../../core/network/api_client.dart';
import '../../auth/data/sesion.dart';
import '../data/modelos.dart';
import '../data/offline_repository.dart';

/// Estado del modo sin conexión para la capa de presentación (CU-37 a CU-39).
/// Cuando hay sesión, sincroniza al abrir la app, en el instante en que vuelve la red y, como respaldo, cada 30 segundos mientras queden operaciones pendientes (RNF06).
const msgSinRed = 'Sin conexión: sus acciones se guardarán en este dispositivo y se enviarán solas al volver la red.';

String textoReconexion(int pendientes) => pendientes > 0 ? 'Conexión restablecida. Sincronizando $pendientes operaciones…' : 'Conexión restablecida.';

String textoResumen(ResumenSync r) => 'Sincronización completa: ${r.confirmadas} confirmadas, ${r.enConflicto} en conflicto, ${r.rechazadas} rechazadas';

class OfflineController extends ChangeNotifier with WidgetsBindingObserver {
  /// `conectividad` emite true al recuperar la red y false al perderla (en la app es `conectividadDelDispositivo()`; en las pruebas, un doble).
  OfflineController(this._repo, {Stream<bool>? conectividad, this.descargaAutomatica = false})
      : _conectividad = conectividad;

  /// Si es true (así la crea la app), el catálogo se descarga solo en segundo plano cuando todavía no hay copia: al iniciar sesión, al volver la red y cada cierto tiempo.
  final bool descargaAutomatica;
  DateTime _ultimoIntentoCatalogo = DateTime.fromMillisecondsSinceEpoch(0);

  final OfflineRepository _repo;
  final Stream<bool>? _conectividad;
  StreamSubscription<bool>? _red;

  /// RNF06: tras cada fallo de red o respuesta 5xx la espera se duplica (30 s, 1 min, 2 min…, máximo 15 min); un 4xx de negocio no se reintenta (queda RECHAZADA).
  int _fallosSeguidos = 0;
  bool _repetir = false;
  DateTime _proximoIntento = DateTime.fromMillisecondsSinceEpoch(0);

  Sesion? _sesion;
  Timer? _reintento;
  List<OperacionLocal> operaciones = [];
  bool hayCatalogo = false;
  String? catalogoGeneradoEn;
  String? ultimaSync;
  bool sincronizando = false;
  bool descargando = false;
  bool enLinea = true;

  /// Sube tras cada sincronización y al volver la red: las pantallas abiertas (Mis compras, Mis reservas) vuelven a pedir sus datos sin que el usuario salga de ellas.
  int refresco = 0;

  /// «Simular sin conexión» (§B11): fuerza el modo sin conexión aunque haya Internet. Al apagarlo se sincroniza en el acto.
  bool simulado = false;
  String? error;

  OfflineRepository get repo => _repo;
  Sesion? get sesion => _sesion;
  List<OperacionLocal> get pendientes =>
      operaciones.where((o) => o.pendiente).toList();
  List<OperacionLocal> get enConflicto =>
      operaciones.where((o) => o.estado == Estado.enConflicto).toList();
  bool get esCliente => _sesion?.rol == 'Cliente';
  bool get habilitado =>
      _sesion != null &&
      _sesion!.offlineHabilitado &&
      ['Cliente', 'Cajero', 'Encargado'].contains(_sesion!.rol);

  /// Lo llama el proveedor cada vez que cambia la sesión (inicio y cierre de sesión).
  void usarSesion(Sesion? s) {
    final cambio = s?.usuarioId != _sesion?.usuarioId;
    _sesion = s;
    if (!cambio) return;
    _reintento?.cancel();
    _red?.cancel();
    operaciones = [];
    if (habilitado) {
      try {
        WidgetsBinding.instance.addObserver(this); // B10: al volver la app a primer plano se sincroniza
      } catch (_) {
        // sin enlace con Flutter (pruebas de lógica): no hay ciclo de vida que observar
      }
      _red = _conectividad?.listen(_alCambiarLaRed);
      _reintento = Timer.periodic(const Duration(seconds: 30), (_) {
        if (pendientes.isNotEmpty && !DateTime.now().isBefore(_proximoIntento)) sincronizar();
        actualizarSiVencido();
      });
      Future.microtask(() async {
        await recargar();
        await sincronizar();
        if (descargaAutomatica) await actualizarSiVencido(); // al iniciar sesión: baja la copia si falta o venció (solo en la app)
      });
    } else {
      notifyListeners();
    }
  }

  /// Nombres de las prendas del catálogo descargado (para el comprobante provisional). Si no se conoce, se muestra el código de la variante.
  final Map<int, String> _nombres = {};

  String nombreDeVariante(int id) => _nombres[id] ?? 'Prenda $id';

  Future<void> _cargarNombres() async {
    for (final p in await _repo.buscar('', limite: 100000)) {
      _nombres[p.variante.id] = '${p.producto.nombre} (${p.variante.talla}, ${p.variante.color})';
    }
  }

  void simularSinConexion(bool valor) {
    if (valor != simulado) _anunciarRed(!valor);
    simulado = valor;
    ApiClient.simularSinConexion = valor;
    enLinea = !valor;
    if (!valor) {
      _proximoIntento = DateTime.fromMillisecondsSinceEpoch(0);
      sincronizar();
      actualizarSiVencido();
    }
    notifyListeners();
  }

  void _registrarResultado(bool fallo) {
    if (!fallo) {
      _fallosSeguidos = 0;
      _proximoIntento = DateTime.fromMillisecondsSinceEpoch(0);
      return;
    }
    _fallosSeguidos++;
    final segundos = (30 * (1 << _fallosSeguidos)).clamp(30, 900);
    _proximoIntento = DateTime.now().add(Duration(seconds: segundos));
  }

  /// Segundos que faltan para el próximo reintento automático (0 si puede reintentar ya).
  int get esperaRestante => _proximoIntento.difference(DateTime.now()).inSeconds.clamp(0, 900);

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    _enSegundoPlano = state != AppLifecycleState.resumed;
    if (state != AppLifecycleState.resumed || !habilitado) return;
    _proximoIntento = DateTime.fromMillisecondsSinceEpoch(0);
    sincronizar();
    actualizarSiVencido();
  }

  /// Al perder la red se avisa en el acto; al recuperarla se sincroniza sin esperar al reintento.
  void _alCambiarLaRed(bool hayRed) {
    if (simulado) return; // con la simulación activa, la red real no cambia el modo
    if (hayRed != enLinea) _anunciarRed(hayRed);
    enLinea = hayRed;
    if (hayRed) {
      _proximoIntento = DateTime.fromMillisecondsSinceEpoch(0); // al volver la red se reintenta en el acto, sin esperar
      refresco++;
    }
    notifyListeners();
    if (hayRed && pendientes.isNotEmpty) sincronizar();
    if (hayRed) actualizarSiVencido();
  }

  Future<void> recargar() async {
    final s = _sesion;
    if (s == null || s.empresaId == null) return;
    operaciones = await _repo.operaciones(s.usuarioId, s.empresaId!);
    hayCatalogo = await _repo.hayCatalogo();
    if (hayCatalogo && _nombres.isEmpty) await _cargarNombres();
    catalogoGeneradoEn = await _repo.catalogoGeneradoEn();
    ultimaSync = await _repo.ultimaSincronizacion();
    notifyListeners();
  }

  /// Horas después de las cuales el catálogo descargado se actualiza solo con conexión (§5.3).
  static const horasVigencia = 6;

  bool get catalogoVencido {
    final fecha = DateTime.tryParse(catalogoGeneradoEn ?? '');
    return fecha != null && DateTime.now().difference(fecha).inHours >= horasVigencia;
  }

  /// Con conexión, si el catálogo tiene más de 6 horas se descarga de nuevo en segundo plano; «Actualizar ahora» hace lo mismo a mano.
  Future<void> actualizarSiVencido() async {
    if (!habilitado || !enLinea || descargando) return;
    if (hayCatalogo && catalogoVencido) return descargarCatalogo();
    if (!hayCatalogo && descargaAutomatica) await _descargarSiFalta();
  }

  /// Quien trabaja sin conexión necesita su copia: si no hay ninguna y hay red, se descarga sola (como mucho una vez por minuto), sin ir a otra pantalla.
  Future<void> _descargarSiFalta() async {
    if (DateTime.now().difference(_ultimoIntentoCatalogo).inSeconds < 60) return;
    _ultimoIntentoCatalogo = DateTime.now();
    await descargarCatalogo();
  }

  /// CU-37: descarga el catálogo con conexión.
  Future<void> descargarCatalogo() async {
    descargando = true;
    error = null;
    notifyListeners();
    try {
      await _repo.descargarCatalogo();
      enLinea = true;
    } catch (e) {
      error = e.toString();
      enLinea = false;
    }
    descargando = false;
    await recargar();
  }

  /// RF19: registra una operación en el dispositivo y, si hay conexión, la sincroniza enseguida.
  Future<OperacionLocal> registrar(
      {required String tipo,
      required Map<String, dynamic> payload,
      required int sucursalId,
      required String resumen,
      bool comprometer = true}) async {
    final s = _sesion!;
    final operacion = await _repo.registrar(
        tipo: tipo,
        payload: payload,
        sucursalId: sucursalId,
        resumen: resumen,
        usuarioId: s.usuarioId,
        empresaId: s.empresaId!);
    if (comprometer) {
      await _repo.comprometerStock(
          (payload['items'] as List).cast<Map<String, dynamic>>(), sucursalId);
    }
    await recargar();
    sincronizar();
    return operacion;
  }

  /// Registra una operación de la sucursal (devolución, recepción, ajuste o atención de reservas) y, si hay conexión, la sincroniza enseguida.
  Future<void> registrarTarea({required String tipo, required Map<String, dynamic> payload, required String resumen}) async {
    final s = _sesion!;
    await _repo.registrar(tipo: tipo, payload: payload, sucursalId: s.sucursalId, resumen: resumen, usuarioId: s.usuarioId, empresaId: s.empresaId!);
    await recargar();
    sincronizar();
  }

  /// CU-38: envía lo pendiente. No hace nada si ya hay una sincronización en curso.
  /// Quién muestra el mensaje emergente al cliente (lo conecta la app con su ScaffoldMessenger).
  void Function(String)? alAvisar;

  /// Quién muestra la notificación local del sistema cuando la app está en segundo plano (lo conecta la app).
  void Function(String)? alNotificar;
  bool _enSegundoPlano = false;
  bool _esperaResumen = false;

  /// Quién muestra el resumen de la sincronización con su botón «Ver detalle» (lo conecta la app); si nadie lo conecta, se usa el aviso común.
  void Function(String)? alResumir;

  /// Aviso global (SnackBar en cualquier pantalla) y, con la app en segundo plano, además notificación del sistema.
  void _avisar(String texto) {
    alAvisar?.call(texto);
    if (_enSegundoPlano) alNotificar?.call(texto);
  }

  void _avisarResumen(String texto) {
    (alResumir ?? alAvisar)?.call(texto);
    if (_enSegundoPlano) alNotificar?.call(texto);
  }

  /// Al perder la red y al recuperarla (real o con «Simular sin conexión»), sin reiniciar la app ni salir de la pantalla.
  void _anunciarRed(bool hayRed) {
    _esperaResumen = hayRed && pendientes.isNotEmpty;
    _avisar(hayRed ? textoReconexion(pendientes.length) : msgSinRed);
  }

  Future<ResumenSync?> sincronizar() async {
    final s = _sesion;
    if (s == null || s.empresaId == null) return null;
    if (sincronizando) {
      _repetir = true; // alguien pidió sincronizar mientras ya había un envío en curso: se repite al terminar, para no esperar al siguiente reintento
      return null;
    }
    sincronizando = true;
    notifyListeners();
    final resumen = await _repo.sincronizar(s.usuarioId, s.empresaId!);
    _registrarResultado(resumen.sinConexion || resumen.reintentar > 0);
    enLinea = !resumen.sinConexion;
    error = resumen.error;
    sincronizando = false;
    await recargar();
    refresco++;
    notifyListeners();
    for (final aviso in resumen.avisos) {
      _avisar(aviso);
    }
    final total = resumen.confirmadas + resumen.enConflicto + resumen.rechazadas;
    if (!resumen.sinConexion && (_esperaResumen || resumen.enConflicto > 0 || resumen.rechazadas > 0 || total >= 2)) {
      _esperaResumen = false;
      _avisarResumen(textoResumen(resumen)); // tras una reconexión, o cuando algo quedó en conflicto o se enviaron varias operaciones juntas
    }
    if (_repetir) {
      _repetir = false;
      sincronizar();
    }
    return resumen;
  }

  Future<void> limpiarTerminadas() async {
    final s = _sesion;
    if (s == null || s.empresaId == null) return;
    await _repo.limpiarTerminadas(s.usuarioId, s.empresaId!);
    await recargar();
  }

  @override
  void dispose() {
    _reintento?.cancel();
    _red?.cancel();
    try {
      WidgetsBinding.instance.removeObserver(this);
    } catch (_) {}
    super.dispose();
  }
}
