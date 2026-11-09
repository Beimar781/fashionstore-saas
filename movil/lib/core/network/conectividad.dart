import 'package:connectivity_plus/connectivity_plus.dart';

/// Avisa en el acto cuando el teléfono pierde o recupera la red (true = hay red). Es la señal que usa el modo sin conexión para sincronizar sin esperar.
Stream<bool> conectividadDelDispositivo() => Connectivity()
    .onConnectivityChanged
    .map((estados) => estados.any((e) => e != ConnectivityResult.none))
    .distinct();
