import 'package:fashionstore_movil/core/network/api_client.dart';
import 'package:fashionstore_movil/features/offline/presentation/conflictos_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

/// Servidor falso: un conflicto de venta de contado y registro de cómo se resuelve.
class ApiFalsa extends ApiClient {
  ApiFalsa({this.sinRed = false, this.disponibles = 1}) : super(obtenerToken: () async => null, renovarToken: () async => false);

  final bool sinRed;
  final int disponibles;
  final resoluciones = <Map<String, dynamic>>[];

  @override
  Future<List<dynamic>> getLista(String ruta) async {
    if (sinRed) throw ApiException('Sin conexión con el servidor.', sinConexion: true);
    return [
      {
        'id': 'op-1', 'tipo': 'VENTA_CONTADO', 'estado': 'EN_CONFLICTO', 'sucursal': 'Centro', 'usuario': 'Ana Cajera', 'creada_en': '2026-11-10T10:00:00Z', 'intentos': 1,
        'mensaje': 'No hay existencias suficientes para esta operación. No se descontó nada.',
        'detalle': {
          'faltantes': [
            {'variante_id': 100, 'producto': 'Camisa Oxford', 'talla': 'S', 'color': 'Rojo', 'solicitadas': 3, 'disponibles': disponibles}
          ]
        },
        'monto_a_devolver': '300.00',
        'efectivo_recibido': '350.00',
      }
    ];
  }

  @override
  Future<Map<String, dynamic>> post(String ruta, Map<String, dynamic> cuerpo, {bool autenticado = true}) async {
    resoluciones.add({'ruta': ruta, ...cuerpo});
    return {'estado': 'RECHAZADA', 'mensaje': 'Se devolvieron Bs 300.00 en efectivo al cliente (nota NDV-1).', 'referencia': null};
  }
}

void main() {
  testWidgets('Muestra qué pasó, qué pidió el dispositivo y cuánto devolver; descartar devolviendo el efectivo exige revisar la prenda', (tester) async {
    final api = ApiFalsa();
    await tester.pumpWidget(MaterialApp(home: ConflictosScreen(api: api)));
    await tester.pumpAndSettle();
    expect(find.textContaining('Qué pasó: No hay existencias suficientes'), findsOneWidget);
    expect(find.textContaining('pidió 3, hoy hay 1, faltan 2'), findsOneWidget);
    expect(find.textContaining('El cliente entregó Bs 350.00 en caja'), findsOneWidget);
    expect(find.textContaining('debe devolverle Bs 300.00'), findsOneWidget);

    await tester.tap(find.text('Descartar…'));
    await tester.pumpAndSettle();
    await tester.enterText(find.byType(TextField), 'La prenda se agotó');
    await tester.tap(find.textContaining('Devolver el efectivo al cliente'));
    await tester.pumpAndSettle();
    final confirmar = find.widgetWithText(FilledButton, 'Descartar y devolver Bs 300.00');
    expect(tester.widget<FilledButton>(confirmar).onPressed, isNull); // sin revisar la prenda no se puede devolver el dinero
    for (final texto in ['Sin daños', 'Sin desgaste ni señales de uso', 'Conserva sus etiquetas']) {
      await tester.tap(find.text(texto));
    }
    await tester.pumpAndSettle();
    await tester.tap(confirmar);
    await tester.pumpAndSettle();
    expect(api.resoluciones.single, {
      'ruta': '/offline/conflictos/op-1/resolver',
      'accion': 'DESCARTAR',
      'motivo': 'La prenda se agotó',
      'devolver_dinero': true,
      'condicion': {'sin_danos': true, 'sin_desgaste': true, 'con_etiquetas': true},
    });
    expect(find.textContaining('Se devolvieron Bs 300.00'), findsOneWidget);
  });

  testWidgets('Con 0 o pocas unidades hoy, «Reintentar» queda deshabilitado y dice «Sin stock todavía»', (tester) async {
    final api = ApiFalsa();
    await tester.pumpWidget(MaterialApp(home: ConflictosScreen(api: api)));
    await tester.pumpAndSettle();
    expect(find.text('Sin stock todavía'), findsOneWidget);
    await tester.tap(find.text('Reintentar'), warnIfMissed: false);
    await tester.pumpAndSettle();
    expect(api.resoluciones, isEmpty);
  });

  testWidgets('Reintentar manda la acción al servidor', (tester) async {
    final api = ApiFalsa(disponibles: 3);
    await tester.pumpWidget(MaterialApp(home: ConflictosScreen(api: api)));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Reintentar'));
    await tester.pumpAndSettle();
    expect(api.resoluciones.single['accion'], 'REINTENTAR');
  });

  testWidgets('Sin conexión explica que los conflictos se resuelven con Internet', (tester) async {
    await tester.pumpWidget(MaterialApp(home: ConflictosScreen(api: ApiFalsa(sinRed: true))));
    await tester.pumpAndSettle();
    expect(find.textContaining('Sin conexión: los conflictos se resuelven cuando hay Internet.'), findsOneWidget);
  });
}
