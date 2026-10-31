import '../../../../core/network/api_client.dart';

/// Un mensaje de la conversación. Los del asistente traen además las prendas y las sugerencias que devolvió el servidor.
class MensajeChat {
  MensajeChat({required this.esUsuario, required this.texto, this.productos = const [], this.sugerencias = const []});

  final bool esUsuario;
  final String texto;
  final List<Map<String, dynamic>> productos;
  final List<String> sugerencias;
}

/// CU-07 · Acceso a la API del asistente de compras: la misma que usa la web.
class AsistenteRepository {
  AsistenteRepository(this._api);

  final ApiClient _api;

  /// `POST /asistente/chat` con toda la conversación; el último mensaje debe ser del cliente.
  Future<MensajeChat> chat(List<MensajeChat> conversacion, int? sucursalId) async {
    final r = await _api.post('/asistente/chat', {
      'mensajes': [for (final m in conversacion) {'rol': m.esUsuario ? 'usuario' : 'asistente', 'texto': m.texto}],
      'sucursal_id': sucursalId,
    });
    return MensajeChat(
      esUsuario: false,
      texto: r['respuesta'] as String,
      productos: ((r['productos'] as List?) ?? const []).cast<Map<String, dynamic>>(),
      sugerencias: ((r['sugerencias'] as List?) ?? const []).cast<String>(),
    );
  }
}
