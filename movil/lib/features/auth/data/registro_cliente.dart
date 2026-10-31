/// CU-01 · Datos para crear una cuenta de cliente en la tienda (empresa) que se visita. Las validaciones son las del servidor.
class RegistroCliente {
  const RegistroCliente({required this.codigoEmpresa, required this.nombre, this.apellidos = '', required this.email, required this.password});

  final String codigoEmpresa;
  final String nombre;
  final String apellidos;
  final String email;
  final String password;

  static const msgPassword = 'La contraseña debe tener al menos 8 caracteres.';

  static String? validarCodigo(String? v) => (v ?? '').trim().isEmpty ? 'Ingrese el código de la tienda.' : null;
  static String? validarNombre(String? v) => (v ?? '').trim().isEmpty ? 'Ingrese su nombre.' : null;
  static String? validarEmail(String? v) => RegExp(r'^[^@\s]+@[^@\s]+\.[^@\s]+$').hasMatch((v ?? '').trim()) ? null : 'Ingrese un correo válido.';
  static String? validarPassword(String? v) => (v ?? '').length < 8 ? msgPassword : null;

  /// Cuerpo de `POST /auth/registro`.
  Map<String, dynamic> aCuerpo() => {
        'codigo_empresa': codigoEmpresa.trim(),
        'nombre': nombre.trim(),
        'apellidos': apellidos.trim(),
        'email': email.trim(),
        'password': password,
      };
}
