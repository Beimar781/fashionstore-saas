import 'package:fashionstore_movil/core/network/api_client.dart';
import 'package:fashionstore_movil/primer_parcial/ia/asistente/data/asistente_repository.dart';
import 'package:fashionstore_movil/primer_parcial/ia/asistente/presentation/chat_asistente.dart';
import 'package:flutter_test/flutter_test.dart';

class ApiSinRed extends ApiClient {
  ApiSinRed()
      : super(obtenerToken: () async => null, renovarToken: () async => false);

  @override
  Future<Map<String, dynamic>> post(String ruta, Map<String, dynamic> cuerpo,
          {bool autenticado = true}) async =>
      throw ApiException('Sin conexión', sinConexion: true);
}

void main() {
  test('cuando falta Internet usa respuesta local y la marca como sin IA',
      () async {
    final chat = ChatAsistente(
      AsistenteRepository(ApiSinRed()),
      responderLocal: (texto, _) async => MensajeChat(
          esUsuario: false,
          texto: 'Encontré una camisa.',
          respuestaLocal: true),
    );
    await chat.enviar('camisa roja');
    expect(chat.mensajes.map((m) => m.esUsuario), [true, false]);
    expect(chat.mensajes.last.respuestaLocal, isTrue);
    expect(chat.mensajes.last.texto, 'Encontré una camisa.');
    chat.dispose();
  });
}
