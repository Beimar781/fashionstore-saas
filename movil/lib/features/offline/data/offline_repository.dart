import 'dart:convert';
import 'dart:io';

import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';
import 'package:http/http.dart' as http;
import 'package:sqflite/sqflite.dart';

import '../../../core/db/local_database.dart';
import '../../../core/network/api_client.dart';
import '../../../core/network/url_imagen.dart';
import '../../../core/network/imagen_prenda.dart';
import '../../../core/util/uuid.dart';
import 'detalle_local.dart';
import 'modelos.dart';

/// Acceso a datos del paquete Operación offline (CU-37 a CU-39): SQLite local + la API de sincronización.
///
/// - El catálogo se descarga una vez con conexión y se consulta sin ella (CU-37); siempre se guarda de cuándo es (RN16).
/// - Toda operación nace con un UUID del dispositivo y queda en SQLite (RN11, RNF03). Al sincronizar pasa a ENVIADA y NO se borra hasta que el
///   servidor la confirme o rechace (RN12); si falla la comunicación vuelve a REGISTRADA_LOCAL y se reintenta (RNF06). Reenviarla no la duplica (RNF05).
class OfflineRepository {
  OfflineRepository(this._api);

  final ApiClient _api;

  Future<Database> get _db => LocalDatabase.instance.database;

  // ---------------- CU-37: catálogo local ----------------
  Future<void> descargarCatalogo() async {
    final c = await _api.get('/offline/catalogo');
    await guardarCatalogo(c);
    final rutas = <String?>[];
    for (final producto
        in (c['productos'] as List).cast<Map<String, dynamic>>()) {
      rutas.add(producto['imagen'] as String?);
      for (final imagen in (producto['imagenes'] as List? ?? const [])) {
        rutas.add((imagen as Map<String, dynamic>)['url'] as String?);
      }
    }
    await precalentarImagenes(rutas);
    await _descargarVestidor(c['productos'] as List);
  }

  Future<void> _descargarVestidor(List productos) async {
    if (productos.isEmpty) return;
    final db = await _db;
    final dir = Directory(
        p.join((await getApplicationSupportDirectory()).path, 'vestidor'));
    await dir.create(recursive: true);
    for (final producto in productos.cast<Map<String, dynamic>>()) {
      try {
        final datos = await _api.get('/vestidor/productos/${producto['id']}');
        final colores = (datos['colores'] as List).cast<Map<String, dynamic>>();
        for (var i = 0; i < colores.length; i++) {
          final ruta = colores[i]['imagen_url'] as String?;
          if (ruta == null || colores[i]['anclaje'] == null) continue;
          final url = urlImagen(ruta);
          if (url == null) continue;
          try {
            final r = await http
                .get(Uri.parse(url))
                .timeout(const Duration(seconds: 15));
            if (r.statusCode == 200) {
              final archivo = p.join(dir.path, '${producto['id']}_$i.png');
              await File(archivo).writeAsBytes(r.bodyBytes, flush: true);
              colores[i]['archivo_local'] = archivo;
            }
          } catch (_) {
            /* Una imagen no disponible no invalida el resto del catálogo. */
          }
        }
        datos['colores'] = colores;
        await db.insert('vestidor_local',
            {'producto_id': producto['id'], 'producto_json': jsonEncode(datos)},
            conflictAlgorithm: ConflictAlgorithm.replace);
      } catch (_) {
        /* Solo se conservan productos vestibles que el servidor haya descrito. */
      }
    }
  }

  /// Guarda en SQLite lo que devolvió `GET /offline/catalogo` (separado para poder probarlo sin red).
  Future<void> guardarCatalogo(Map<String, dynamic> c) async {
    final db = await _db;
    final empresaId = c['empresa_id'] as int;
    final ahora = DateTime.now().toIso8601String();
    await db.transaction((tx) async {
      for (final t in [
        'productos_locales',
        'sucursales_autorizadas',
        'clientes_locales'
      ]) {
        await tx.delete(t);
      }
      for (final s in (c['sucursales'] as List).cast<Map<String, dynamic>>()) {
        await tx.insert('sucursales_autorizadas', {
          'id': s['id'],
          'empresa_id': empresaId,
          'nombre': s['nombre'],
          'ciudad': s['ciudad'],
          'direccion': s['direccion'],
          'horario': s['horario'],
        });
      }
      for (final p in (c['productos'] as List).cast<Map<String, dynamic>>()) {
        await tx.insert('productos_locales', {
          'id': p['id'],
          'empresa_id': empresaId,
          'nombre': p['nombre'],
          'categoria': p['categoria'],
          'genero': p['genero'],
          'imagen': p['imagen'],
          'variantes_json': jsonEncode(p['variantes']),
          'descargado_en': ahora,
        });
      }
      for (final cl in (c['clientes'] as List).cast<Map<String, dynamic>>()) {
        await tx.insert('clientes_locales', {
          'id': cl['id'],
          'empresa_id': empresaId,
          'nombre': cl['nombre'],
          'email': cl['email']
        });
      }
      await tx.insert(
          'meta',
          {
            'clave': 'catalogo_generado_en',
            'valor': c['generado_en'] as String
          },
          conflictAlgorithm: ConflictAlgorithm.replace);
      await tx.insert(
          'meta', {'clave': 'ultima_sincronizacion', 'valor': ahora},
          conflictAlgorithm: ConflictAlgorithm.replace);
    });
  }

  Future<String?> catalogoGeneradoEn() => _meta('catalogo_generado_en');
  Future<String?> ultimaSincronizacion() => _meta('ultima_sincronizacion');

  Future<String?> _meta(String clave) async {
    final f =
        await (await _db).query('meta', where: 'clave = ?', whereArgs: [clave]);
    return f.isEmpty ? null : f.first['valor'] as String;
  }

  Future<List<ProductoLocal>> _productos() async {
    final filas =
        await (await _db).query('productos_locales', orderBy: 'nombre');
    return [
      for (final f in filas)
        ProductoLocal(
          id: f['id'] as int,
          nombre: f['nombre'] as String,
          categoria: f['categoria'] as String,
          genero: f['genero'] as String?,
          imagen: f['imagen'] as String?,
          variantes: [
            for (final v in jsonDecode(f['variantes_json'] as String) as List)
              VarianteLocal.fromJson(v as Map<String, dynamic>)
          ],
        ),
    ];
  }

  Future<bool> hayCatalogo() async =>
      Sqflite.firstIntValue(await (await _db)
          .rawQuery('SELECT COUNT(*) FROM productos_locales'))! >
      0;

  /// Búsqueda local por nombre, categoría, SKU o código de barras.
  Future<List<PrendaLocal>> buscar(String texto, {int limite = 60}) async {
    final q = texto.trim().toLowerCase();
    final salida = <PrendaLocal>[];
    for (final p in await _productos()) {
      final coincideProducto = q.isEmpty ||
          p.nombre.toLowerCase().contains(q) ||
          p.categoria.toLowerCase().contains(q);
      for (final v in p.variantes) {
        if (coincideProducto ||
            v.sku.toLowerCase().contains(q) ||
            (v.codigoBarras ?? '').toLowerCase() == q) {
          salida.add(PrendaLocal(p, v));
        }
      }
    }
    return salida.take(limite).toList();
  }

  Future<List<SucursalLocal>> sucursales() async {
    final filas =
        await (await _db).query('sucursales_autorizadas', orderBy: 'nombre');
    return [
      for (final f in filas)
        SucursalLocal(
            id: f['id'] as int,
            nombre: f['nombre'] as String,
            ciudad: f['ciudad'] as String?,
            horario: f['horario'] as String?)
    ];
  }

  Future<List<ClienteLocal>> clientes() async {
    final filas =
        await (await _db).query('clientes_locales', orderBy: 'nombre');
    return [
      for (final f in filas)
        ClienteLocal(
            id: f['id'] as int,
            nombre: f['nombre'] as String,
            email: f['email'] as String)
    ];
  }

  Future<void> guardarCarritoCliente(
      Map<String, dynamic> carrito, int empresaId, int usuarioId) async {
    await (await _db).insert(
        'meta',
        {
          'clave': 'carrito_cliente_${empresaId}_$usuarioId',
          'valor': jsonEncode(carrito)
        },
        conflictAlgorithm: ConflictAlgorithm.replace);
  }

  Future<Map<String, dynamic>?> carritoClienteLocal(
      int empresaId, int usuarioId) async {
    final filas = await (await _db).query('meta',
        where: 'clave = ?',
        whereArgs: ['carrito_cliente_${empresaId}_$usuarioId']);
    if (filas.isEmpty) return null;
    try {
      return jsonDecode(filas.first['valor'] as String) as Map<String, dynamic>;
    } catch (_) {
      return null;
    }
  }

  Future<void> limpiarCarritoCliente(int empresaId, int usuarioId) async {
    await (await _db).delete('meta',
        where: 'clave = ?',
        whereArgs: ['carrito_cliente_${empresaId}_$usuarioId']);
  }

  /// Al registrar sin conexión se descuenta del stock local lo comprometido; el servidor vuelve a validar al sincronizar.
  Future<void> comprometerStock(
      List<Map<String, dynamic>> items, int sucursalId) async {
    final db = await _db;
    for (final p in await _productos()) {
      var cambio = false;
      for (final v in p.variantes) {
        for (final it in items.where((i) => i['variante_id'] == v.id)) {
          v.stock[sucursalId] =
              ((v.stock[sucursalId] ?? 0) - (it['cantidad'] as int))
                  .clamp(0, 1 << 30)
                  .toInt();
          cambio = true;
        }
      }
      if (cambio) {
        await db.update(
            'productos_locales',
            {
              'variantes_json':
                  jsonEncode([for (final v in p.variantes) v.toJson()])
            },
            where: 'id = ?',
            whereArgs: [p.id]);
      }
    }
  }

  // ---------------- CU-38 y CU-39: cola de operaciones ----------------
  Future<OperacionLocal> registrar({
    required String tipo,
    required Map<String, dynamic> payload,
    required int? sucursalId,
    required String resumen,
    required int usuarioId,
    required int empresaId,
  }) async {
    final op = OperacionLocal(
      id: generarUuid(),
      empresaId: empresaId,
      sucursalId: sucursalId,
      usuarioId: usuarioId,
      tipo: tipo,
      payload: payload,
      estado: Estado.registradaLocal,
      intentos: 0,
      mensaje: '',
      referencia: null,
      comprobante: null,
      detalle: null,
      resumen: resumen,
      creadoEn: DateTime.now().toUtc().toIso8601String(),
    );
    final db = await _db;
    await db.transaction((tx) async {
      await tx.insert('operaciones_pendientes', op.aFila());
      await DetalleLocal.guardar(tx, id: op.id, tipo: tipo, empresaId: empresaId, sucursalId: sucursalId, usuarioId: usuarioId, payload: payload, creadoEn: op.creadoEn);
    });
    return op;
  }

  /// Actualiza la operación (o la crea). No usa «reemplazar»: borrar y volver a insertar eliminaría en cascada su detalle.
  Future<void> _guardar(OperacionLocal o) async {
    final db = await _db;
    final cambiadas = await db.update('operaciones_pendientes', o.aFila(), where: 'id = ?', whereArgs: [o.id]);
    if (cambiadas == 0) await db.insert('operaciones_pendientes', o.aFila());
  }

  /// El cuerpo que viaja al servidor: se arma desde el detalle relacional (la fuente de los datos), no desde un JSON aparte.
  Future<Map<String, dynamic>> _cuerpoDe(OperacionLocal o) async => DetalleLocal.payloadDesdeDetalle(await _db, o.id, o.tipo, o.payload);

  /// Deja el resultado de la operación y una fila técnica del intento (RNF10). El motivo nunca lleva datos personales.
  Future<void> _anotarResultado(OperacionLocal o, String resultado, String codigo) async {
    final db = await _db;
    await DetalleLocal.guardarResultado(db, id: o.id, estado: o.estado, mensaje: o.mensaje, referencia: o.referencia, comprobante: o.comprobante);
    await DetalleLocal.anotarIntento(db, id: o.id, tipo: o.tipo, intento: o.intentos, resultado: resultado, codigo: codigo, motivo: o.estado == Estado.rechazada || o.estado == Estado.enConflicto ? o.mensaje : '');
  }

  /// Texto del registro técnico de sincronización, para copiarlo y mandarlo a soporte.
  Future<String> diagnostico() async => DetalleLocal.diagnostico(await _db);

  Future<List<Map<String, Object?>>> registroSincronizacion({int limite = 100}) async =>
      (await _db).query('registro_sincronizacion', orderBy: 'id DESC', limit: limite);

  /// Las operaciones del usuario en este dispositivo, de la más reciente a la más antigua.
  Future<List<OperacionLocal>> operaciones(int usuarioId, int empresaId) async {
    final filas = await (await _db).query('operaciones_pendientes',
        where: 'usuario_id = ? AND empresa_id = ?',
        whereArgs: [usuarioId, empresaId],
        orderBy: 'creado_en DESC');
    return [for (final f in filas) OperacionLocal.desdeFila(f)];
  }

  Future<void> borrarOperacionLocal(String id) async => (await _db)
      .delete('operaciones_pendientes', where: 'id = ?', whereArgs: [id]);

  Future<void> guardarReservasVistas(
      List<Map<String, dynamic>> reservas, int usuarioId, int empresaId) async {
    await (await _db).insert(
        'meta',
        {
          'clave': 'reservas_vistas_${empresaId}_$usuarioId',
          'valor': jsonEncode(reservas),
        },
        conflictAlgorithm: ConflictAlgorithm.replace);
  }

  Future<List<Map<String, dynamic>>> reservasVistas(
      int usuarioId, int empresaId) async {
    final filas = await (await _db).query('meta',
        where: 'clave = ?',
        whereArgs: ['reservas_vistas_${empresaId}_$usuarioId']);
    if (filas.isEmpty) return [];
    try {
      return (jsonDecode(filas.first['valor'] as String) as List)
          .cast<Map<String, dynamic>>();
    } catch (_) {
      return [];
    }
  }

  Future<void> guardarComprasVistas(
      List<Map<String, dynamic>> compras, int usuarioId, int empresaId) async {
    await (await _db).insert(
        'meta',
        {
          'clave': 'compras_vistas_${empresaId}_$usuarioId',
          'valor': jsonEncode(compras)
        },
        conflictAlgorithm: ConflictAlgorithm.replace);
  }

  Future<List<Map<String, dynamic>>> comprasVistas(
      int usuarioId, int empresaId) async {
    final filas = await (await _db).query('meta',
        where: 'clave = ?',
        whereArgs: ['compras_vistas_${empresaId}_$usuarioId']);
    if (filas.isEmpty) return [];
    try {
      return (jsonDecode(filas.first['valor'] as String) as List)
          .cast<Map<String, dynamic>>();
    } catch (_) {
      return [];
    }
  }

  /// CU-38: envía por lote lo pendiente, en el orden en que ocurrió, y actualiza el estado de cada operación con la respuesta.
  Future<ResumenSync> sincronizar(int usuarioId, int empresaId) async {
    final resumen = ResumenSync();
    final todas = await operaciones(usuarioId, empresaId);
    final lote = todas.where((o) => o.pendiente).toList()
      ..sort((a, b) => a.creadoEn.compareTo(b.creadoEn));
    if (lote.isEmpty) {
      await refrescarEstados(usuarioId, empresaId);
      return resumen;
    }
    for (final o in lote) {
      o.estado = Estado.enviada; // RN12: enviada, pero todavía guardada
      o.intentos += 1;
      await _guardar(o);
    }
    resumen.enviadas = lote.length;
    try {
      final r = await _api.post('/offline/sincronizar', {
        'operaciones': [
          for (final o in lote)
            {
              'id': o.id,
              'tipo': o.tipo,
              'creada_en': o.creadoEn,
              'sucursal_id': o.sucursalId,
              'payload': await _cuerpoDe(o)
            },
        ],
        'hora_dispositivo': DateTime.now().toUtc().toIso8601String(), // con zona horaria: el servidor compara con su reloj (§7.2)
      });
      final avisoReloj = r['aviso_reloj'] as String?;
      if (avisoReloj != null) resumen.avisos.add(avisoReloj);
      for (final res
          in (r['resultados'] as List).cast<Map<String, dynamic>>()) {
        final o = lote.where((x) => x.id == res['id']).firstOrNull;
        if (o == null) continue;
        final estado = res['estado'] as String;
        if (estado == 'ERROR') {
          o.estado = Estado
              .registradaLocal; // el servidor no pudo procesarla ahora: se conserva y se reintenta (RNF06)
          resumen.reintentar++;
        } else {
          o.estado = estado;
          o.referencia = res['referencia'] as String?;
          o.comprobante = res['comprobante'] as String?;
          o.detalle = res['detalle'] as Map<String, dynamic>?;
          if (estado == Estado.confirmada) resumen.confirmadas++;
          if (estado == Estado.rechazada) resumen.rechazadas++;
          if (estado == Estado.enConflicto) resumen.enConflicto++;
          _avisarAlCliente(resumen, o, res['mensaje'] as String);
        }
        o.mensaje = res['mensaje'] as String;
        await _guardar(o);
        await _anotarResultado(o, o.estado, estado == 'ERROR' ? '5xx' : '200');
      }
      await _poner('ultima_sincronizacion', DateTime.now().toIso8601String());
    } on ApiException catch (e) {
      for (final o in lote) {
        o.estado = Estado.registradaLocal; // sin respuesta no se pierde nada
        await _guardar(o);
        await _anotarResultado(o, 'SIN_RESPUESTA', e.sinConexion ? 'SIN_RED' : '${e.statusCode ?? 'ERROR'}');
      }
      resumen.sinConexion = e.sinConexion;
      resumen.error = e.sinConexion
          ? 'Sin conexión con el servidor: las operaciones siguen guardadas y se reintentarán.'
          : e.mensaje;
      return resumen;
    }
    await refrescarEstados(usuarioId, empresaId);
    return resumen;
  }

  /// Mensaje emergente para el cliente (además del push y de la campana): su compra o reserva no alcanzó, o su compra quedó lista para pagar.
  void _avisarAlCliente(ResumenSync resumen, OperacionLocal o, String mensaje) {
    if (o.tipo == 'VENTA_CONTADO') return;
    final nombre = o.tipo == 'COMPRA' ? 'compra' : 'reserva';
    if (o.estado == Estado.enConflicto) {
      resumen.avisos.add(
          'Su $nombre no se pudo realizar porque la prenda se agotó. No se le cobró nada.');
    } else if (o.estado == Estado.rechazada) {
      resumen.avisos.add('Su $nombre no se pudo realizar: $mensaje');
    } else if (o.estado == Estado.confirmada && o.tipo == 'COMPRA') {
      resumen.avisos.add(
          'Su compra ${o.referencia} está lista: págela con tarjeta en «Mis compras».');
    }
  }

  /// CU-39: una operación que quedó en conflicto y el Encargado resolvió cambia de estado también aquí.
  Future<void> refrescarEstados(int usuarioId, int empresaId) async {
    final enConflicto = (await operaciones(usuarioId, empresaId))
        .where((o) => o.estado == Estado.enConflicto)
        .toList();
    if (enConflicto.isEmpty) return;
    try {
      final servidor = (await _api.getLista('/offline/operaciones'))
          .cast<Map<String, dynamic>>();
      for (final s in servidor) {
        final o = enConflicto.where((x) => x.id == s['id']).firstOrNull;
        if (o != null && s['estado'] != Estado.enConflicto) {
          o.estado = s['estado'] as String;
          o.mensaje = s['mensaje'] as String;
          o.referencia = s['referencia'] as String?;
          o.comprobante = s['comprobante'] as String?;
          o.detalle = s['detalle'] as Map<String, dynamic>?;
          await _guardar(o);
        }
      }
    } on ApiException {
      // sin conexión: se vuelve a intentar después
    }
  }

  Future<void> _poner(String clave, String valor) async =>
      (await _db).insert('meta', {'clave': clave, 'valor': valor},
          conflictAlgorithm: ConflictAlgorithm.replace);

  /// Solo se pueden quitar del dispositivo las operaciones que el servidor ya confirmó o rechazó (RN12).
  Future<int> limpiarTerminadas(int usuarioId, int empresaId) async =>
      (await _db).delete(
        'operaciones_pendientes',
        where: 'usuario_id = ? AND empresa_id = ? AND estado IN (?, ?)',
        whereArgs: [usuarioId, empresaId, Estado.confirmada, Estado.rechazada],
      );
}
