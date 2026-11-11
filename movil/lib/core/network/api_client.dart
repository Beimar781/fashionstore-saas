import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:http/http.dart' as http;

import '../config/api_config.dart';
import 'lecturas_locales.dart';

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
  /// «Simular sin conexión» (§B11): con esto activo toda llamada falla como si no hubiera red. Sirve para demostrar el modo sin conexión sin apagar el WiFi.
  static bool simularSinConexion = false;

  /// Quién se entera de si el servidor respondió (true) o no (false): es la única fuente de verdad del indicador «En línea / Sin conexión».
  static void Function(bool respondio)? alDetectarServidor;

  /// Fecha de la última lectura entregada desde la copia local («Datos al…»); null si lo último que se leyó vino del servidor.
  static String? lecturaLocalDesde;

  /// Rutas que nunca se guardan: la sesión, lo que genera la IA, las notificaciones y la descarga del catálogo, que tiene su propio almacén.
  static const _noGuardar = ['/auth/', '/asistente', '/vestidor', '/pagos/config', '/notificaciones', '/offline/catalogo', '/ia/'];

  ApiClient({required this.obtenerToken, required this.renovarToken, http.Client? cliente, this.lecturas, this.cuenta}) : _cliente = cliente ?? http.Client();

  /// Copia de las lecturas y la cuenta a la que pertenecen (empresa:usuario). Sin cuenta no se guarda ni se lee nada.
  LecturasLocales? lecturas;
  Future<String?> Function()? cuenta;

  final Future<String?> Function() obtenerToken;
  final Future<bool> Function() renovarToken;
  final http.Client _cliente;

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
    if (simularSinConexion) throw ApiException('Sin conexión con el servidor.', sinConexion: true);
    final token = await obtenerToken();
    try {
      final respuesta = await _cliente
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

  /// Una lectura (GET) con red se guarda; si el servidor no responde (sin Internet, caído o «Simular sin conexión») se entrega la última copia de esa cuenta.
  Future<dynamic> _enviar(String metodo, String ruta,
      {Map<String, dynamic>? cuerpo, bool autenticado = true, bool reintento = false}) async {
    final guardable = metodo == 'GET' && lecturas != null && autenticado && !_noGuardar.any(ruta.contains);
    try {
      final datos = await _enviarAlServidor(metodo, ruta, cuerpo: cuerpo, autenticado: autenticado, reintento: reintento);
      if (guardable) {
        lecturaLocalDesde = null;
        unawaited(_guardarLectura(ruta, datos));
      }
      return datos;
    } on ApiException catch (e) {
      if (!e.sinConexion || !guardable) rethrow;
      final copia = await _leerLectura(ruta);
      if (copia == null) rethrow;
      lecturaLocalDesde = copia.fecha;
      return copia.datos;
    }
  }

  Future<String?> _clave(String ruta) async {
    final c = await cuenta?.call();
    return c == null ? null : '$c|$ruta';
  }

  Future<void> _guardarLectura(String ruta, dynamic datos) async {
    try {
      final clave = await _clave(ruta);
      if (clave != null) await lecturas!.guardar(clave, datos);
    } catch (_) {
      // sin espacio o sin base: la pantalla funciona igual con red
    }
  }

  Future<LecturaGuardada?> _leerLectura(String ruta) async {
    try {
      final clave = await _clave(ruta);
      return clave == null ? null : await lecturas!.leer(clave);
    } catch (_) {
      return null;
    }
  }

  Future<dynamic> _enviarAlServidor(String metodo, String ruta,
      {Map<String, dynamic>? cuerpo, bool autenticado = true, bool reintento = false}) async {
    try {
      final datos = await _enviarSinAviso(metodo, ruta, cuerpo: cuerpo, autenticado: autenticado, reintento: reintento);
      alDetectarServidor?.call(true);
      return datos;
    } on ApiException catch (e) {
      alDetectarServidor?.call(!e.sinConexion); // un 4xx o 5xx también es una respuesta del servidor
      rethrow;
    }
  }

  Future<dynamic> _enviarSinAviso(String metodo, String ruta,
      {Map<String, dynamic>? cuerpo, bool autenticado = true, bool reintento = false}) async {
    if (simularSinConexion) throw ApiException('Sin conexión con el servidor.', sinConexion: true);
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
          respuesta = await _cliente.get(uri, headers: cabeceras).timeout(const Duration(seconds: 12));
        case 'DELETE':
          respuesta = await _cliente.delete(uri, headers: cabeceras).timeout(const Duration(seconds: 12));
        case 'PUT':
          respuesta = await _cliente.put(uri, headers: cabeceras, body: jsonEncode(cuerpo ?? {})).timeout(const Duration(seconds: 12));
        default:
          respuesta = await _cliente.post(uri, headers: cabeceras, body: jsonEncode(cuerpo ?? {})).timeout(const Duration(seconds: 12));
      }

      if (respuesta.statusCode == 401 && autenticado && !reintento && await renovarToken()) {
        return await _enviarSinAviso(metodo, ruta, cuerpo: cuerpo, autenticado: autenticado, reintento: true);
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
