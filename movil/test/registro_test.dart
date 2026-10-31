import 'package:fashionstore_movil/features/auth/data/registro_cliente.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('El código de la tienda, el nombre y el correo son obligatorios', () {
    expect(RegistroCliente.validarCodigo('  '), 'Ingrese el código de la tienda.');
    expect(RegistroCliente.validarCodigo('EMP-A'), isNull);
    expect(RegistroCliente.validarNombre(''), 'Ingrese su nombre.');
    expect(RegistroCliente.validarNombre('Ana'), isNull);
    expect(RegistroCliente.validarEmail('sin-arroba'), 'Ingrese un correo válido.');
    expect(RegistroCliente.validarEmail('a@b'), 'Ingrese un correo válido.');
    expect(RegistroCliente.validarEmail(' ana@correo.com '), isNull);
  });

  test('La contraseña lleva el mismo mensaje que el servidor si tiene menos de 8 caracteres', () {
    expect(RegistroCliente.validarPassword('1234567'), 'La contraseña debe tener al menos 8 caracteres.');
    expect(RegistroCliente.validarPassword(null), 'La contraseña debe tener al menos 8 caracteres.');
    expect(RegistroCliente.validarPassword('12345678'), isNull);
  });

  test('El cuerpo es el de la web: código, nombre, apellidos, correo y contraseña', () {
    const r = RegistroCliente(codigoEmpresa: ' EMP-A ', nombre: ' Ana ', apellidos: ' Pérez ', email: ' ana@correo.com ', password: ' clave 1234 ');
    expect(r.aCuerpo(), {'codigo_empresa': 'EMP-A', 'nombre': 'Ana', 'apellidos': 'Pérez', 'email': 'ana@correo.com', 'password': ' clave 1234 '});
  });
}
