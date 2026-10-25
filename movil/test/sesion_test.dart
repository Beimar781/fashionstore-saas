import 'package:flutter_test/flutter_test.dart';
import 'package:fashionstore_movil/features/auth/data/sesion.dart';

void main() {
  test('Sesion interpreta el contexto de empresa, rol y plan (CU-02)', () {
    final s = Sesion({
      'usuario': {
        'id': 7, 'nombre': 'Ana', 'apellidos': 'Suárez', 'email': 'cajero@tienda.com',
        'rol': 'Cajero', 'sucursal_id': 1, 'sucursal_nombre': 'Sucursal Centro'
      },
      'empresa': {'id': 1, 'codigo': 'EMP-A', 'razon_social': 'Moda Urbana S.R.L.', 'estado': 'ACTIVA'},
      'suscripcion': {
        'estado': 'ACTIVA', 'fecha_inicio': '2026-10-25', 'fecha_vencimiento': '2027-10-25',
        'plan': {'nombre': 'Básico', 'max_sucursales': 2}
      },
      'panel': 'punto_venta',
      'restringido': false,
    });
    expect(s.rol, 'Cajero');
    expect(s.empresaCodigo, 'EMP-A');
    expect(s.planNombre, 'Básico');
    expect(s.maxSucursales, 2);
    expect(s.restringido, isFalse);
    expect(s.panel, 'punto_venta');
  });

  test('El SuperAdministrador no tiene empresa ni suscripción', () {
    final s = Sesion({
      'usuario': {'id': 1, 'nombre': 'Super', 'apellidos': 'Administrador', 'email': 's@f.com', 'rol': 'SuperAdministrador', 'sucursal_id': null, 'sucursal_nombre': null},
      'empresa': null, 'suscripcion': null, 'panel': 'plataforma', 'restringido': false,
    });
    expect(s.empresaCodigo, isNull);
    expect(s.planNombre, isNull);
  });
}
