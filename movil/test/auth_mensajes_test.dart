import 'package:fashionstore_movil/features/auth/data/auth_offline.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('la autenticación explica qué acciones necesitan conexión', () {
    expect(mensajeAuthSinConexion('iniciar sesión'),
        'Sin conexión: necesita Internet para iniciar sesión.');
    expect(mensajeAuthSinConexion('crear su cuenta'),
        'Sin conexión: necesita Internet para crear su cuenta.');
    expect(mensajeAuthSinConexion('recuperar su contraseña'),
        'Sin conexión: necesita Internet para recuperar su contraseña.');
  });
}
