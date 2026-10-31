/// Tarjeta que el cliente guardó en una compra anterior (`GET /pagos/tarjetas`).
class TarjetaGuardada {
  const TarjetaGuardada({required this.id, required this.marca, required this.ultimos4, required this.expMes, required this.expAnio});

  factory TarjetaGuardada.desdeJson(Map<String, dynamic> j) =>
      TarjetaGuardada(id: j['id'] as int, marca: j['marca'] as String, ultimos4: j['ultimos4'] as String, expMes: j['exp_mes'] as int, expAnio: j['exp_anio'] as int);

  final int id;
  final String marca;
  final String ultimos4;
  final int expMes;
  final int expAnio;

  String get descripcion => '$marca terminada en $ultimos4 · vence $expMes/$expAnio';
}

/// Cómo paga el cliente: con una tarjeta guardada, o con una tarjeta nueva (que puede guardar para próximas compras).
class MedioDePago {
  const MedioDePago({this.tarjetaGuardadaId, this.guardar = false});

  final int? tarjetaGuardadaId;
  final bool guardar;

  /// Cuerpo de `POST /pagos/pedidos/{id}/iniciar`, igual que la web. Solo se guarda una tarjeta nueva.
  Map<String, dynamic> aCuerpo() => {'tarjeta_guardada_id': tarjetaGuardadaId, 'guardar_tarjeta': tarjetaGuardadaId == null && guardar};
}
