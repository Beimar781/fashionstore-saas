import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:http/http.dart' as http;

import '../config/api_config.dart';

/// Error de comunicación o de negocio con mensaje listo para mostrar al usuario.
class ApiException implements Exception {
  ApiException(this.mensaje, {this.statusCode, this.sinConexion = false, this.motivo = ''});

  final String mensaje;
  final int? statusCode;

  /// Detalle que da el banco cuando rechaza un pago con tarjeta (402).
  final String motivo;

  /// `true` cuando no hubo respuesta del servidor (sin Internet o servidor caído).
  final bool sinConexion;

  @override
  String toString() => mensaje;
}

/// Archivo que devolvió el servidor (por ejemplo, el comprobante PDF) y el nombre que sugirió en `Content-Disposition`.
class ArchivoDescargado {
  ArchivoDescargado(this.bytes, this.nombre);

  final List<int> bytes;
  final String? nombre;
}

/// Cliente REST compartido por todos los paquetes (la misma API que usa la PWA Angular).
/// Agrega el token Bearer y, ante un 401, intenta renovar la sesión una vez.
class ApiClient {
  ApiClient({required this.obtenerToken, required this.renovarToken});

  final Future<String?> Function() obtenerToken;
  final Future<bool> Function() renovarToken;

  Future<Map<String, dynamic>> get(String ruta) async => _mapa(await _enviar('GET', ruta));

  /// GET que devuelve una lista JSON (por ejemplo, las operaciones del usuario).
  Future<List<dynamic>> getLista(String ruta) async {
    final datos = await _enviar('GET', ruta);
    return datos is List ? datos : <dynamic>[];
  }

  Future<Map<String, dynamic>> post(String ruta, Map<String, dynamic> cuerpo, {bool autenticado = true}) async =>
      _mapa(await _enviar('POST', ruta, cuerpo: cuerpo, autenticado: autenticado));

  Future<Map<String, dynamic>> put(String ruta, Map<String, dynamic> cuerpo) async => _mapa(await _enviar('PUT', ruta, cuerpo: cuerpo));

  Future<Map<String, dynamic>> delete(String ruta) async => _mapa(await _enviar('DELETE', ruta));

  /// GET de un archivo binario con el token de la sesión (si caduca, se renueva una vez).
  Future<ArchivoDescargado> descargar(String ruta, {bool reintento = false}) async {
    final token = await obtenerToken();
    try {
      final respuesta = await http
          .get(Uri.parse('${ApiConfig.baseUrl}$ruta'), headers: {if (token != null) 'Authorization': 'Bearer $token'})
          .timeout(const Duration(seconds: 30));
      if (respuesta.statusCode == 401 && !reintento && await renovarToken()) return await descargar(ruta, reintento: true);
      if (respuesta.statusCode != 200) throw ApiException('No se pudo descargar el archivo.', statusCode: respuesta.statusCode);
      final nombre = RegExp(r'filename="?([^";]+)"?').firstMatch(respuesta.headers['content-disposition'] ?? '')?.group(1);
      return ArchivoDescargado(respuesta.bodyBytes, nombre);
    } on SocketException {
      throw ApiException('Sin conexión con el servidor.', sinConexion: true);
    } on TimeoutException {
      throw ApiException('Sin conexión con el servidor.', sinConexion: true);
    } on http.ClientException {
      throw ApiException('Sin conexión con el servidor.', sinConexion: true);
    }
  }

  Map<String, dynamic> _mapa(dynamic datos) => datos is Map<String, dynamic> ? datos : <String, dynamic>{};

  Future<dynamic> _enviar(String metodo, String ruta,
      {Map<String, dynamic>? cuerpo, bool autenticado = true, bool reintento = false}) async {
    final uri = Uri.parse('${ApiConfig.baseUrl}$ruta');
    final cabeceras = <String, String>{'Content-Type': 'application/json'};
    if (autenticado) {
      final token = await obtenerToken();
      if (token != null) cabeceras['Authorization'] = 'Bearer $token';
    }
    try {
      final http.Response respuesta;
      switch (metodo) {
        case 'GET':
          respuesta = await http.get(uri, headers: cabeceras).timeout(const Duration(seconds: 12));
        case 'DELETE':
          respuesta = await http.delete(uri, headers: cabeceras).timeout(const Duration(seconds: 12));
        case 'PUT':
          respuesta = await http.put(uri, headers: cabeceras, body: jsonEncode(cuerpo ?? {})).timeout(const Duration(seconds: 12));
        default:
          respuesta = await http.post(uri, headers: cabeceras, body: jsonEncode(cuerpo ?? {})).timeout(const Duration(seconds: 12));
      }

      if (respuesta.statusCode == 401 && autenticado && !reintento && await renovarToken()) {
        return await _enviar(metodo, ruta, cuerpo: cuerpo, autenticado: autenticado, reintento: true);
      }
      final datos = respuesta.body.isEmpty ? <String, dynamic>{} : jsonDecode(utf8.decode(respuesta.bodyBytes));
      if (respuesta.statusCode >= 200 && respuesta.statusCode < 300) return datos;
      final detalle = datos is Map ? datos['detail'] : null;
      final motivo = datos is Map ? datos['motivo'] : null;
      throw ApiException(
        detalle is String ? detalle : 'No se pudo completar la operación.',
        statusCode: respuesta.statusCode,
        motivo: motivo is String ? motivo : '',
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
