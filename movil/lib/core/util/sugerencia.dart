/// Distancia de edición entre dos palabras (cuántas letras hay que cambiar, quitar o agregar).
int distanciaEdicion(String a, String b) {
  var anterior = List<int>.generate(b.length + 1, (j) => j);
  for (var i = 1; i <= a.length; i++) {
    final actual = List<int>.filled(b.length + 1, 0)..[0] = i;
    for (var j = 1; j <= b.length; j++) {
      final costo = a[i - 1] == b[j - 1] ? 0 : 1;
      actual[j] = [anterior[j] + 1, actual[j - 1] + 1, anterior[j - 1] + costo].reduce((x, y) => x < y ? x : y);
    }
    anterior = actual;
  }
  return anterior[b.length];
}

/// «¿Quiso decir…?»: la palabra conocida más parecida a lo escrito (a lo sumo 2 letras de diferencia); null si no hay ninguna razonable.
String? sugerirPalabra(String escrito, Iterable<String> conocidas) {
  final q = escrito.trim().toLowerCase();
  if (q.length < 3) return null;
  String? mejor;
  var mejorDistancia = 3;
  for (final palabra in conocidas) {
    final p = palabra.toLowerCase();
    if (p == q) return null;
    final d = distanciaEdicion(q, p);
    if (d < mejorDistancia) {
      mejorDistancia = d;
      mejor = palabra;
    }
  }
  return mejor;
}
