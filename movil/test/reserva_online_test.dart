import 'dart:convert';

import 'package:fashionstore_movil/core/network/api_client.dart';
import 'package:fashionstore_movil/primer_parcial/reservas/data/reserva_borrador.dart';
import 'package:fashionstore_movil/primer_parcial/reservas/data/reservas_repository.dart';
import 'package:flutter_test/flutter_test.dart';

PrendaElegida _prenda({int id = 1, int max = 5}) => PrendaElegida(varianteId: id, producto: 'Camisa Oxford', sku: 'CAM-S-ROJ', talla: 'S', color: 'Rojo', max: max);

class ApiFalsa extends ApiClient {
  ApiFalsa() : super(obtenerToken: () async => null, renovarToken: () async => false);

  final llamadas = <(String, Map<String, dynamic>)>[];

  @override
  Future<Map<String, dynamic>> post(String ruta, Map<String, dynamic> cuerpo, {bool autenticado = true}) async {
    llamadas.add((ruta, cuerpo));
    return {'codigo': 'RES-1'};
  }
}

void main() {
  late Map<String, String> disco;
  late ReservaBorrador borrador;

  setUp(() {
    disco = {};
    borrador = ReservaBorrador(leer: (clave) async => disco[clave], guardar: (clave, valor) async => disco[clave] = valor);
  });

  test('Agregar la misma prenda suma de a una, sin pasar de 10 ni de lo disponible', () async {
    await borrador.usarUsuario(7);
    borrador.agregar(_prenda(max: 3));
    for (var i = 0; i < 5; i++) {
      borrador.agregar(_prenda(max: 3));
    }
    expect(borrador.prendas.single.cantidad, 3);
    borrador.agregar(_prenda(id: 2, max: 50));
    for (var i = 0; i < 20; i++) {
      borrador.cambiarCantidad(2, borrador.prendas.last.cantidad + 1);
    }
    expect(borrador.prendas.last.cantidad, 10);
    expect(borrador.total, 13);
  });

  test('La cantidad nunca baja de 1 y quitar y vaciar funcionan', () async {
    await borrador.usarUsuario(7);
    borrador.agregar(_prenda());
    borrador.agregar(_prenda(id: 2));
    borrador.cambiarCantidad(1, 0);
    expect(borrador.prendas.first.cantidad, 1);
    borrador.quitar(1);
    expect(borrador.prendas.map((p) => p.varianteId), [2]);
    borrador.vaciar();
    expect(borrador.prendas, isEmpty);
  });

  test('El borrador se guarda por usuario y cada uno recupera el suyo', () async {
    await borrador.usarUsuario(7);
    borrador.agregar(_prenda());
    await borrador.usarUsuario(8);
    expect(borrador.prendas, isEmpty);
    borrador.agregar(_prenda(id: 9));
    await borrador.usarUsuario(7);
    expect(borrador.prendas.single.varianteId, 1);
    final otro = ReservaBorrador(leer: (c) async => disco[c], guardar: (c, v) async => disco[c] = v);
    await otro.usarUsuario(8);
    expect(otro.prendas.single.varianteId, 9);
    await otro.usarUsuario(null);
    expect(otro.prendas, isEmpty);
  });

  test('El cuerpo de la reserva es el mismo que envía la web', () async {
    await borrador.usarUsuario(7);
    borrador.agregar(_prenda());
    borrador.cambiarCantidad(1, 2);
    final cuerpo = borrador.aCuerpo(sucursalId: 4, cuando: DateTime(2026, 11, 3, 9, 5), notas: ' llego tarde ');
    expect(cuerpo, {
      'sucursal_id': 4,
      'programada_para': '2026-11-03T09:05',
      'notas': 'llego tarde',
      'items': [
        {'variante_id': 1, 'cantidad': 2},
      ],
    });
    final api = ApiFalsa();
    expect((await ReservasRepository(api).reservar(cuerpo))['codigo'], 'RES-1');
    expect(api.llamadas.single.$1, '/reservas');
    expect(jsonEncode(api.llamadas.single.$2), jsonEncode(cuerpo));
  });

  test('Cancelar envía el motivo (opcional, sin espacios sobrantes)', () async {
    final api = ApiFalsa();
    final repo = ReservasRepository(api);
    await repo.cancelar(3, motivo: '  No puedo ir ');
    await repo.cancelar(4);
    expect(api.llamadas[0].$1, '/reservas/3/cancelar');
    expect(api.llamadas[0].$2, {'motivo': 'No puedo ir'});
    expect(api.llamadas[1].$2, {'motivo': ''});
  });
}
