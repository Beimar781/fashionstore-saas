import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:http/http.dart' as http;

import '../config/api_config.dart';

/// Error de comunicación o de negocio con mensaje listo para mostrar al usuario.
class ApiException implements Exception {
  ApiException(this.mensaje, {this.statusCode, this.sinConexion = false});

  final String mensaje;
  final int? statusCode;

  /// `true` cuando no hubo respuesta del servidor (sin Internet o servidor caído).
  final bool sinConexion;

  @override
  String toString() => mensaje;
}

/// Cliente REST compartido por todos los paquetes (la misma API que usa la PWA Angular).
/// Agrega el token Bearer y, ante un 401, intenta renovar la sesión una vez.
class ApiClient {
  ApiClient({required this.obtenerToken, required this.renovarToken});

  final Future<String?> Function() obtenerToken;
  final Future<bool> Function() renovarToken;

  Future<Map<String, dynamic>> get(String ruta) => _enviar('GET', ruta);

  Future<Map<String, dynamic>> post(String ruta, Map<String, dynamic> cuerpo,
          {bool autenticado = true}) =>
      _enviar('POST', ruta, cuerpo: cuerpo, autenticado: autenticado);

  Future<Map<String, dynamic>> _enviar(String metodo, String ruta,
      {Map<String, dynamic>? cuerpo, bool autenticado = true, bool reintento = false}) async {
    final uri = Uri.parse('${ApiConfig.baseUrl}$ruta');
    final cabeceras = <String, String>{'Content-Type': 'application/json'};
    if (autenticado) {
      final token = await obtenerToken();
      if (token != null) cabeceras['Authorization'] = 'Bearer $token';
    }
    try {
      final respuesta = metodo == 'GET'
          ? await http.get(uri, headers: cabeceras).timeout(const Duration(seconds: 12))
          : await http
              .post(uri, headers: cabeceras, body: jsonEncode(cuerpo ?? {}))
              .timeout(const Duration(seconds: 12));

      if (respuesta.statusCode == 401 && autenticado && !reintento && await renovarToken()) {
        return _enviar(metodo, ruta, cuerpo: cuerpo, autenticado: autenticado, reintento: true);
      }
      final datos = respuesta.body.isEmpty
          ? <String, dynamic>{}
          : jsonDecode(utf8.decode(respuesta.bodyBytes)) as Map<String, dynamic>;
      if (respuesta.statusCode >= 200 && respuesta.statusCode < 300) return datos;
      final detalle = datos['detail'];
      throw ApiException(
        detalle is String ? detalle : 'No se pudo completar la operación.',
        statusCode: respuesta.statusCode,
      );
    } on SocketException {
      throw ApiException('Sin conexión con el servidor.', sinConexion: true);
    } on TimeoutException {
      throw ApiException('Sin conexión con el servidor.', sinConexion: true);
    } on http.ClientException {
      throw ApiException('Sin conexión con el servidor.', sinConexion: true);
    }
  }
}
