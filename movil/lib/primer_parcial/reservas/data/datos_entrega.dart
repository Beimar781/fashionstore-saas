/// Mismos mensajes que el servidor (CU-11): el formulario los muestra antes de enviar.
const msgNit = 'Ingrese su NIT o CI para la facturación.';
const msgDireccion = 'Ingrese la dirección de entrega.';

/// Entrega y facturación de la compra digital (CU-11): retiro en la sucursal o entrega a domicilio, y NIT o CI con razón social opcional.
class DatosEntrega {
  const DatosEntrega({this.domicilio = false, this.direccion = '', this.nitCi = '', this.razonSocial = ''});

  final bool domicilio;
  final String direccion;
  final String nitCi;
  final String razonSocial;

  /// Devuelve el mensaje del primer dato que falta, o null si todo está completo.
  String? validar() {
    if (nitCi.trim().length < 3) return msgNit;
    if (domicilio && direccion.trim().isEmpty) return msgDireccion;
    return null;
  }

  /// Cuerpo de `POST /compras/checkout`. En retiro no se envía dirección.
  Map<String, dynamic> aCuerpo() => {
        'tipo_entrega': domicilio ? 'DELIVERY' : 'RETIRO',
        'direccion_entrega': domicilio ? direccion.trim() : '',
        'nit_ci': nitCi.trim(),
        'razon_social': razonSocial.trim(),
      };
}
