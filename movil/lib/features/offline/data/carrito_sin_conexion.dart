import 'dart:convert';

import '../../../core/network/api_client.dart';
import '../../../core/util/iva.dart';
import '../../../core/util/uuid.dart';
import '../../../primer_parcial/reservas/data/reservas_repository.dart';
import 'modelos.dart';
import 'offline_repository.dart';

/// E3 · El carrito del Cliente sin conexión, igual que en la web: lo último que mostró el servidor + los cambios hechos en el teléfono (cantidad, quitar, vaciar)
/// + las prendas agregadas sin conexión (ids negativos). Al volver la red los cambios se repiten en orden y las prendas nuevas se fusionan una sola vez (RN11).
class CarritoSinConexion {
  CarritoSinConexion(this.repo, {required this.empresaId, required this.usuarioId});

  final OfflineRepository repo;
  final int empresaId;
  final int usuarioId;

  String get _claveEdiciones => 'carrito_ediciones_${empresaId}_$usuarioId';
  String get _claveFusion => 'carrito_fusion_${empresaId}_$usuarioId';

  Future<List<Map<String, dynamic>>> ediciones() async {
    final texto = await repo.leerMeta(_claveEdiciones);
    return texto == null ? [] : (jsonDecode(texto) as List).cast<Map<String, dynamic>>();
  }

  Future<void> _guardarEdiciones(List<Map<String, dynamic>> lista) async =>
      lista.isEmpty ? repo.borrarMeta(_claveEdiciones) : repo.ponerMeta(_claveEdiciones, jsonEncode(lista));

  Future<Map<String, dynamic>?> _local() => repo.carritoClienteLocal(empresaId, usuarioId);

  Future<bool> hayCambios() async => (await ediciones()).isNotEmpty || ((await _local())?['items'] as List? ?? const []).isNotEmpty;

  /// El carrito tal como se ve sin conexión, con la misma forma que `/carrito`; null si nunca hubo uno en este teléfono.
  Future<Map<String, dynamic>?> vista(Map<String, dynamic>? servidor) async {
    final local = await _local();
    final nuevos = (local?['items'] as List? ?? const []).cast<Map<String, dynamic>>();
    if (servidor == null && nuevos.isEmpty) return null;
    if (servidor != null && nuevos.isEmpty && (await ediciones()).isEmpty) return servidor; // nada que mezclar: es el del servidor tal cual
    var items = [for (final i in (servidor?['items'] as List? ?? const [])) Map<String, dynamic>.from(i as Map)];
    for (final e in await ediciones()) {
      switch (e['tipo']) {
        case 'vaciar':
          items = [];
        case 'quitar':
          items = items.where((i) => i['id'] != e['item_id']).toList();
        default:
          for (final i in items.where((i) => i['id'] == e['item_id'])) {
            i['cantidad'] = e['cantidad'];
          }
      }
    }
    final prendas = nuevos.isEmpty ? <PrendaLocal>[] : await repo.buscar('', limite: 100000);
    for (final n in nuevos) {
      final p = prendas.where((x) => x.variante.id == n['variante_id']).firstOrNull;
      if (p == null) continue;
      items.add({
        'id': -(p.variante.id),
        'variante_id': p.variante.id,
        'producto': p.producto.nombre,
        'talla': p.variante.talla,
        'color': p.variante.color,
        'precio': p.variante.precio,
        'precio_final': p.variante.precioFinal,
        'cantidad': n['cantidad'],
        'disponible': p.variante.stockEn((local?['sucursal_id'] ?? servidor?['sucursal_id']) as int?),
        'estado': 'OK',
      });
    }
    final sucursalId = (servidor?['sucursal_id'] ?? local?['sucursal_id']) as int?;
    final sucursales = await repo.sucursales();
    return _calcular(items, sucursalId, servidor?['sucursal'] as String? ?? sucursales.where((s) => s.id == sucursalId).firstOrNull?.nombre, await repo.ivaPorcentaje());
  }

  Map<String, dynamic> _calcular(List<Map<String, dynamic>> items, int? sucursalId, String? sucursal, int ivaPorcentaje) {
    var subtotal = 0.0, total = 0.0;
    var unidades = 0;
    for (final i in items) {
      final c = i['cantidad'] as int;
      final precio = double.tryParse('${i['precio'] ?? i['precio_final']}') ?? 0;
      final final_ = double.tryParse('${i['precio_final']}') ?? 0;
      subtotal += precio * c;
      total += final_ * c;
      unidades += c;
      i['subtotal'] = (final_ * c).toStringAsFixed(2);
    }
    return {
      'sucursal_id': sucursalId,
      'sucursal': sucursal,
      'items': items,
      'total_unidades': unidades,
      'subtotal': subtotal.toStringAsFixed(2),
      'descuento': (subtotal - total).toStringAsFixed(2),
      'iva_incluido': ivaIncluido(total, ivaPorcentaje),
      'total': total.toStringAsFixed(2),
      'puede_pagar': items.isNotEmpty && items.every((i) => (i['disponible'] as int? ?? 0) >= (i['cantidad'] as int)),
      'avisos': <String>[],
    };
  }

  // ---- cambios hechos sin conexión ----
  Future<void> agregar(PrendaLocal prenda, int sucursalId) async {
    final local = await _local() ?? {'sucursal_id': sucursalId, 'tipo_entrega': 'RETIRO', 'direccion_entrega': '', 'nit_ci': '', 'razon_social': '', 'items': <Map<String, dynamic>>[]};
    final items = [for (final i in (local['items'] as List)) Map<String, dynamic>.from(i as Map)];
    final disponibles = prenda.variante.stockEn(sucursalId);
    final actual = items.where((i) => i['variante_id'] == prenda.variante.id).firstOrNull;
    if ((actual?['cantidad'] as int? ?? 0) >= disponibles) throw ApiException('No hay más unidades disponibles en el catálogo descargado.');
    if (actual != null) {
      actual['cantidad'] = (actual['cantidad'] as int) + 1;
    } else {
      items.add({'variante_id': prenda.variante.id, 'cantidad': 1});
    }
    await repo.guardarCarritoCliente({...local, 'sucursal_id': local['sucursal_id'] ?? sucursalId, 'items': items}, empresaId, usuarioId);
  }

  Future<void> cambiarCantidad(Map<String, dynamic> item, int cantidad) async {
    final disponible = item['disponible'] as int?;
    if (cantidad < 1 || cantidad > 10) throw ApiException('La cantidad debe estar entre 1 y 10.');
    if (disponible != null && cantidad > disponible) throw ApiException('No hay más unidades disponibles en el catálogo descargado.');
    if ((item['id'] as int) < 0) return _cambiarNueva(item['id'] as int, cantidad);
    await _guardarEdiciones([...await ediciones(), {'tipo': 'cantidad', 'item_id': item['id'], 'cantidad': cantidad}]);
  }

  Future<void> quitar(Map<String, dynamic> item) async {
    if ((item['id'] as int) < 0) return _cambiarNueva(item['id'] as int, 0);
    await _guardarEdiciones([...await ediciones(), {'tipo': 'quitar', 'item_id': item['id']}]);
  }

  Future<void> vaciar() async {
    await _guardarEdiciones([...await ediciones(), {'tipo': 'vaciar'}]);
    await repo.limpiarCarritoCliente(empresaId, usuarioId);
  }

  Future<void> _cambiarNueva(int idNegativo, int cantidad) async {
    final local = await _local();
    if (local == null) return;
    final items = [for (final i in (local['items'] as List)) Map<String, dynamic>.from(i as Map)];
    for (final i in items.where((i) => i['variante_id'] == -idNegativo)) {
      i['cantidad'] = cantidad;
    }
    items.removeWhere((i) => (i['cantidad'] as int) <= 0);
    if (items.isEmpty) {
      await repo.limpiarCarritoCliente(empresaId, usuarioId);
    } else {
      await repo.guardarCarritoCliente({...local, 'items': items}, empresaId, usuarioId);
    }
  }

  /// Una compra hecha sin conexión ya contiene todo: se limpian las prendas nuevas y los cambios pendientes.
  Future<void> alComprar() async {
    await repo.limpiarCarritoCliente(empresaId, usuarioId);
    await _guardarEdiciones([]);
  }

  // ---- al volver la red ----
  /// Repite los cambios sobre el carrito del servidor, en orden, y fusiona las prendas nuevas con un identificador fijo (si se corta, no se duplica).
  /// Devuelve cuántos cambios ya no se pudieron aplicar. Si la red se cae a mitad, lo que falta espera (lanza la excepción de conexión).
  Future<int> reenviar(ReservasRepository api) async {
    final pendientes = await ediciones();
    var rechazados = 0;
    for (var n = 0; n < pendientes.length; n++) {
      final e = pendientes[n];
      try {
        switch (e['tipo']) {
          case 'vaciar':
            await api.vaciarCarrito();
          case 'quitar':
            await api.quitar(e['item_id'] as int);
          default:
            await api.cambiarCantidad(e['item_id'] as int, e['cantidad'] as int);
        }
      } on ApiException catch (x) {
        if (x.sinConexion) {
          await _guardarEdiciones(pendientes.sublist(n));
          rethrow;
        }
        rechazados++;
      }
    }
    await _guardarEdiciones([]);
    final local = await _local();
    final nuevos = (local?['items'] as List? ?? const []).cast<Map<String, dynamic>>();
    if (nuevos.isNotEmpty) {
      final fusionId = await repo.leerMeta(_claveFusion) ?? generarUuid();
      await repo.ponerMeta(_claveFusion, fusionId);
      final r = await api.fusionarCarrito(fusionId, local!['sucursal_id'] as int, [for (final i in nuevos) {'variante_id': i['variante_id'], 'cantidad': i['cantidad']}]);
      rechazados += (r['rechazadas'] as List? ?? const []).length;
      await repo.limpiarCarritoCliente(empresaId, usuarioId);
      await repo.borrarMeta(_claveFusion);
    }
    return rechazados;
  }
}
