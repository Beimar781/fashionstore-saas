import 'package:flutter/material.dart';

/// Aviso con botón de acción que SÍ se cierra solo: en Flutter un SnackBar con `action` se queda fijo salvo que se pida `persist: false`.
SnackBar avisoConAccion(String texto, {required String etiqueta, required VoidCallback alPulsar, Duration duracion = const Duration(seconds: 5)}) =>
    SnackBar(content: Text(texto), duration: duracion, persist: false, action: SnackBarAction(label: etiqueta, onPressed: alPulsar));
