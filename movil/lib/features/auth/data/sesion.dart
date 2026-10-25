/// Contexto de sesión devuelto por `POST /api/auth/login` y `GET /api/auth/me` (CU-02).
class Sesion {
  Sesion(this.datos);

  final Map<String, dynamic> datos;

  Map<String, dynamic> get _usuario => datos['usuario'] as Map<String, dynamic>;
  Map<String, dynamic>? get _empresa => datos['empresa'] as Map<String, dynamic>?;
  Map<String, dynamic>? get _suscripcion => datos['suscripcion'] as Map<String, dynamic>?;

  int get usuarioId => _usuario['id'] as int;
  String get nombreCompleto => '${_usuario['nombre']} ${_usuario['apellidos']}'.trim();
  String get email => _usuario['email'] as String;
  String get rol => _usuario['rol'] as String;
  String? get sucursalNombre => _usuario['sucursal_nombre'] as String?;

  String? get empresaCodigo => _empresa?['codigo'] as String?;
  String? get empresaNombre => _empresa?['razon_social'] as String?;

  String? get planNombre => (_suscripcion?['plan'] as Map<String, dynamic>?)?['nombre'] as String?;
  String? get suscripcionEstado => _suscripcion?['estado'] as String?;
  String? get vencimiento => _suscripcion?['fecha_vencimiento'] as String?;
  int? get maxSucursales => (_suscripcion?['plan'] as Map<String, dynamic>?)?['max_sucursales'] as int?;

  /// Administrador con suscripción no vigente: solo puede consultar su plan (RN05).
  bool get restringido => datos['restringido'] as bool? ?? false;

  /// Panel según rol: plataforma, empresa, reservas_sucursal, punto_venta o catalogo.
  String get panel => datos['panel'] as String? ?? 'catalogo';
}
