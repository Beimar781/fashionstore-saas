import 'package:fashionstore_movil/core/network/api_client.dart';
import 'package:fashionstore_movil/features/auth/data/sesion.dart';
import 'package:fashionstore_movil/primer_parcial/ia/asistente/data/asistente_repository.dart';
import 'package:fashionstore_movil/primer_parcial/ia/asistente/presentation/chat_asistente.dart';
import 'package:flutter_test/flutter_test.dart';

/// Doble del servidor: guarda lo que se le envía y responde lo preparado.
class ApiFalsa extends ApiClient {
  ApiFalsa() : super(obtenerToken: () async => null, renovarToken: () async => false);

  ApiException? fallo;
  final cuerpos = <Map<String, dynamic>>[];

  @override
  Future<Map<String, dynamic>> post(String ruta, Map<String, dynamic> cuerpo, {bool autenticado = true}) async {
    expect(ruta, '/asistente/chat');
    cuerpos.add(cuerpo);
    if (fallo != null) throw fallo!;
    return {
      'respuesta': 'Encontré estas camisas.',
      'productos': [
        {'id': 3, 'nombre': 'Camisa Oxford', 'categoria': 'Camisas', 'precio_final': '120.00'}
      ],
      'sugerencias': ['Ver más baratas'],
    };
  }
}

Sesion _sesion({required bool ia}) => Sesion({
      'usuario': {'id': 1, 'nombre': 'A', 'apellidos': 'B', 'email': 'a@b.com', 'rol': 'Cliente'},
      'empresa': {'id': 1, 'codigo': 'EMP-B', 'razon_social': 'Estilo Andino'},
      'suscripcion': {
        'estado': 'ACTIVA',
        'plan': {'nombre': ia ? 'Profesional' : 'Básico', 'max_sucursales': 2, 'reportes_ia': ia, 'offline': true},
      },
    });

void main() {
  test('El asistente guarda la conversación con las prendas y las sugerencias del servidor', () async {
    final api = ApiFalsa();
    final chat = ChatAsistente(AsistenteRepository(api));
    await chat.enviar('  una camisa para el trabajo ', sucursalId: 2);
    expect(chat.mensajes.map((m) => m.esUsuario), [true, false]);
    expect(chat.mensajes.last.productos.single['nombre'], 'Camisa Oxford');
    expect(chat.mensajes.last.sugerencias, ['Ver más baratas']);
    expect(chat.pensando, isFalse);
    expect(api.cuerpos.single, {
      'mensajes': [
        {'rol': 'usuario', 'texto': 'una camisa para el trabajo'}
      ],
      'sucursal_id': 2,
    });
  });

  test('Un segundo mensaje envía toda la conversación y un texto vacío no envía nada', () async {
    final api = ApiFalsa();
    final chat = ChatAsistente(AsistenteRepository(api));
    await chat.enviar('hola');
    await chat.enviar('   ');
    await chat.enviar('algo más barato');
    expect(api.cuerpos, hasLength(2));
    expect((api.cuerpos.last['mensajes'] as List).map((m) => (m as Map)['rol']), ['usuario', 'asistente', 'usuario']);
    expect(api.cuerpos.last['sucursal_id'], isNull);
  });

  test('Sin conexión: «Sin conexión: el asistente necesita Internet.»', () async {
    final api = ApiFalsa()..fallo = ApiException('Sin conexión con el servidor.', sinConexion: true);
    final chat = ChatAsistente(AsistenteRepository(api));
    await chat.enviar('hola');
    expect(chat.error, 'Sin conexión: el asistente necesita Internet.');
    expect(chat.pensando, isFalse);
  });

  test('Plan sin IA (403): se muestra el mensaje del servidor', () async {
    final api = ApiFalsa()..fallo = ApiException('Su plan no incluye esta funcionalidad. Cambie al plan Profesional.', statusCode: 403);
    final chat = ChatAsistente(AsistenteRepository(api));
    await chat.enviar('hola');
    expect(chat.error, 'Su plan no incluye esta funcionalidad. Cambie al plan Profesional.');
  });

  test('La entrada del asistente depende del plan: solo con reportes_ia', () {
    expect(_sesion(ia: true).iaHabilitada, isTrue);
    expect(_sesion(ia: false).iaHabilitada, isFalse);
  });
}
