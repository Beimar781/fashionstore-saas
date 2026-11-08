import 'package:flutter/foundation.dart';

import '../../../../core/network/api_client.dart';
import '../data/asistente_repository.dart';

const msgAsistenteSinConexion = 'Sin conexión: el asistente necesita Internet.';

/// Estado de la conversación con el asistente: los mensajes, si está buscando y el último error.
class ChatAsistente extends ChangeNotifier {
  ChatAsistente(this._repo, {this.responderLocal});

  final AsistenteRepository _repo;
  final Future<MensajeChat> Function(String texto, int? sucursalId)?
      responderLocal;

  final List<MensajeChat> mensajes = [];
  bool pensando = false;
  String? error;

  Future<void> enviar(String texto, {int? sucursalId}) async {
    texto = texto.trim();
    if (texto.isEmpty || pensando) return;
    mensajes.add(MensajeChat(esUsuario: true, texto: texto));
    pensando = true;
    error = null;
    notifyListeners();
    try {
      mensajes.add(await _repo.chat(mensajes, sucursalId));
    } on ApiException catch (e) {
      if (e.sinConexion && responderLocal != null) {
        try {
          mensajes.add(await responderLocal!(mensajes.last.texto, sucursalId));
        } on ApiException catch (local) {
          error = local.mensaje;
        } catch (_) {
          error = msgAsistenteSinConexion;
        }
      } else {
        error = e.sinConexion ? msgAsistenteSinConexion : e.mensaje;
      }
    }
    pensando = false;
    notifyListeners();
  }
}
