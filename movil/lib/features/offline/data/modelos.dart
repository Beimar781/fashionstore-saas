import 'dart:convert';

/// Estados de una operación en el dispositivo (RN11). REGISTRADA_LOCAL y ENVIADA existen solo aquí; los otros tres los fija el servidor.
class Estado {
  static const registradaLocal = 'REGISTRADA_LOCAL';
  static const enviada = 'ENVIADA';
  static const confirmada = 'CONFIRMADA';
  static const rechazada = 'RECHAZADA';
  static const enConflicto = 'EN_CONFLICTO';

  static const textos = {
    registradaLocal: 'Registrada en el dispositivo',
    enviada: 'Enviada, esperando respuesta',
    confirmada: 'Confirmada por el servidor',
    rechazada: 'Rechazada',
    enConflicto: 'En conflicto',
  };
}

class VarianteLocal {
  VarianteLocal({
    required this.id,
    required this.sku,
    required this.codigoBarras,
    required this.talla,
    required this.color,
    required this.precio,
    required this.precioFinal,
    required this.promocion,
    required this.stock,
  });

  final int id;
  final String sku;
  final String? codigoBarras;
  final String talla;
  final String color;
  final String precio;
  final String precioFinal;
  final String? promocion;

  /// sucursal → unidades disponibles
  final Map<int, int> stock;

  factory VarianteLocal.fromJson(Map<String, dynamic> j) => VarianteLocal(
        id: j['id'] as int,
        sku: j['sku'] as String,
        codigoBarras: j['codigo_barras'] as String?,
        talla: j['talla'] as String,
        color: j['color'] as String,
        precio: '${j['precio']}',
        precioFinal: '${j['precio_final']}',
        promocion: j['promocion'] as String?,
        stock: {for (final e in (j['stock'] as Map<String, dynamic>).entries) int.parse(e.key): e.value as int},
      );

  Map<String, dynamic> toJson() => {
        'id': id,
        'sku': sku,
        'codigo_barras': codigoBarras,
        'talla': talla,
        'color': color,
        'precio': precio,
        'precio_final': precioFinal,
        'promocion': promocion,
        'stock': {for (final e in stock.entries) '${e.key}': e.value},
      };

  /// Unidades en una sucursal; sin sucursal, la suma de todas.
  int stockEn(int? sucursalId) => sucursalId == null ? stock.values.fold(0, (a, b) => a + b) : (stock[sucursalId] ?? 0);
}

class ProductoLocal {
  ProductoLocal({required this.id, required this.nombre, required this.categoria, required this.genero, required this.imagen, required this.variantes});

  final int id;
  final String nombre;
  final String categoria;
  final String? genero;
  final String? imagen;
  final List<VarianteLocal> variantes;
}

/// Una prenda concreta (variante) con su producto, tal como se busca y se vende.
class PrendaLocal {
  PrendaLocal(this.producto, this.variante);
  final ProductoLocal producto;
  final VarianteLocal variante;

  String get texto => '${producto.nombre} (${variante.talla}, ${variante.color})';
}

class SucursalLocal {
  SucursalLocal({required this.id, required this.nombre, this.ciudad, this.horario});
  final int id;
  final String nombre;
  final String? ciudad;
  final String? horario;
}

class ClienteLocal {
  ClienteLocal({required this.id, required this.nombre, required this.email});
  final int id;
  final String nombre;
  final String email;
}

class OperacionLocal {
  OperacionLocal({
    required this.id,
    required this.empresaId,
    required this.sucursalId,
    required this.usuarioId,
    required this.tipo,
    required this.payload,
    required this.estado,
    required this.intentos,
    required this.mensaje,
    required this.referencia,
    required this.comprobante,
    required this.detalle,
    required this.resumen,
    required this.creadoEn,
  });

  final String id; // UUID generado en el dispositivo (RN11)
  final int empresaId;
  final int? sucursalId;
  final int usuarioId;
  final String tipo; // VENTA_CONTADO | RESERVA
  final Map<String, dynamic> payload;
  String estado;
  int intentos;
  String mensaje;
  String? referencia;
  String? comprobante;
  Map<String, dynamic>? detalle; // en conflicto: {faltantes: [...]}
  final String resumen;
  final String creadoEn;

  bool get pendiente => estado == Estado.registradaLocal || estado == Estado.enviada;

  List<Map<String, dynamic>> get faltantes => ((detalle?['faltantes'] as List?) ?? const []).cast<Map<String, dynamic>>();

  factory OperacionLocal.desdeFila(Map<String, Object?> f) => OperacionLocal(
        id: f['id'] as String,
        empresaId: f['empresa_id'] as int,
        sucursalId: f['sucursal_id'] as int?,
        usuarioId: f['usuario_id'] as int,
        tipo: f['tipo'] as String,
        payload: jsonDecode(f['payload_json'] as String) as Map<String, dynamic>,
        estado: f['estado'] as String,
        intentos: f['intentos'] as int,
        mensaje: f['mensaje'] as String,
        referencia: f['referencia'] as String?,
        comprobante: f['comprobante'] as String?,
        detalle: f['detalle_json'] == null ? null : jsonDecode(f['detalle_json'] as String) as Map<String, dynamic>,
        resumen: f['resumen'] as String,
        creadoEn: f['creado_en'] as String,
      );

  Map<String, Object?> aFila() => {
        'id': id,
        'empresa_id': empresaId,
        'sucursal_id': sucursalId,
        'usuario_id': usuarioId,
        'tipo': tipo,
        'payload_json': jsonEncode(payload),
        'estado': estado,
        'intentos': intentos,
        'mensaje': mensaje,
        'referencia': referencia,
        'comprobante': comprobante,
        'detalle_json': detalle == null ? null : jsonEncode(detalle),
        'resumen': resumen,
        'creado_en': creadoEn,
      };
}

/// Lo que dejó una sincronización, para mostrarlo al usuario.
class ResumenSync {
  ResumenSync({this.enviadas = 0, this.confirmadas = 0, this.rechazadas = 0, this.enConflicto = 0, this.reintentar = 0, this.sinConexion = false, this.error});
  int enviadas, confirmadas, rechazadas, enConflicto, reintentar;
  bool sinConexion;
  String? error;
}
