import 'dart:math' as math;
import 'dart:typed_data';
import 'dart:ui';

import 'package:fashionstore_movil/core/network/api_client.dart';
import 'package:fashionstore_movil/primer_parcial/ia/vestidor/data/vestidor_repository.dart';
import 'package:fashionstore_movil/primer_parcial/ia/vestidor/domain/anclaje.dart';
import 'package:fashionstore_movil/primer_parcial/ia/vestidor/domain/cuerpo.dart';
import 'package:fashionstore_movil/primer_parcial/ia/vestidor/domain/filtro_one_euro.dart';
import 'package:fashionstore_movil/primer_parcial/ia/vestidor/domain/guia.dart';
import 'package:fashionstore_movil/primer_parcial/ia/vestidor/domain/metricas.dart';
import 'package:fashionstore_movil/primer_parcial/ia/vestidor/presentation/vestidor_controller.dart';
import 'package:flutter_test/flutter_test.dart';

/// Pose frontal: hombros separados `ancho` (centrados), caderas debajo. Puntos de 0 a 1.
PoseCuerpo pose({double ancho = 0.30, double yHombros = 0.30, double yCaderas = 0.62, double confianza = 0.9, double confianzaCaderas = 0.9, double dyHombros = 0}) {
  final izq = 0.5 - ancho / 2;
  final der = 0.5 + ancho / 2;
  return PoseCuerpo(
    hombroIzq: PuntoCuerpo(izq, yHombros - dyHombros / 2, confianza),
    hombroDer: PuntoCuerpo(der, yHombros + dyHombros / 2, confianza),
    caderaIzq: PuntoCuerpo(izq + 0.03, yCaderas, confianzaCaderas),
    caderaDer: PuntoCuerpo(der - 0.03, yCaderas, confianzaCaderas),
  );
}

class ApiFalsa extends ApiClient {
  ApiFalsa() : super(obtenerToken: () async => null, renovarToken: () async => false);

  Map<String, dynamic> respuesta = {};
  ApiException? fallo;
  int consultas = 0;

  @override
  Future<Map<String, dynamic>> get(String ruta) async {
    consultas++;
    if (fallo != null) throw fallo!;
    return respuesta;
  }
}

Map<String, dynamic> _producto({bool admite = true, List<Map<String, dynamic>>? colores}) => {
      'producto_id': 7,
      'producto': 'Camisa Oxford',
      'admite': admite,
      'mensaje': admite ? null : 'Esta prenda no admite vestidor.',
      'colores': colores ??
          (!admite ? <Map<String, dynamic>>[] : [
            {'color_id': 1, 'color': 'Azul', 'codigo_hex': '#0000FF', 'listo': false, 'imagen_url': null, 'ancho': null, 'alto': null, 'anclaje': null},
            {
              'color_id': 2, 'color': 'Rojo', 'codigo_hex': '#FF0000', 'listo': true, 'imagen_url': '/media/1/productos/7/rojo.png', 'ancho': 400, 'alto': 480,
              'anclaje': {'y_hombros': 0.10, 'ancho_hombros': 0.85, 'y_cadera': 0.92, 'ajuste': 1.0},
            },
          ]),
      'escala_tallas': admite ? {'S': 0.96, 'M': 1.0, 'XL': 1.1} : <String, dynamic>{},
    };

void main() {
  group('Filtro One Euro', () {
    test('una señal constante no cambia', () {
      final f = FiltroOneEuro();
      for (var i = 0; i < 20; i++) {
        expect(f.filtrar(0.5, i / 30), closeTo(0.5, 1e-9));
      }
    });

    test('quita el temblor: la salida oscila mucho menos que la entrada', () {
      final f = FiltroOneEuro();
      var maxEntrada = 0.0, maxSalida = 0.0;
      for (var i = 0; i < 60; i++) {
        final ruido = (i.isEven ? 0.01 : -0.01);
        final salida = f.filtrar(0.5 + ruido, i / 30);
        if (i > 10) {
          maxEntrada = math.max(maxEntrada, ruido.abs());
          maxSalida = math.max(maxSalida, (salida - 0.5).abs());
        }
      }
      expect(maxSalida, lessThan(maxEntrada / 2));
    });

    test('sigue un movimiento real sin quedarse atrás', () {
      final f = FiltroOneEuro();
      f.filtrar(0, 0);
      var salida = 0.0;
      for (var i = 1; i <= 12; i++) {
        salida = f.filtrar(1, i / 30);
      }
      expect(salida, greaterThan(0.85));
    });

    test('suaviza los cuatro puntos y se puede reiniciar', () {
      final f = FiltroPose();
      f.filtrar(pose(), 0);
      final b = f.filtrar(pose(ancho: 0.32), 1 / 30);
      expect(b.hombroDer.x, inInclusiveRange(0.65, 0.66));
      f.reiniciar();
      expect(f.filtrar(pose(ancho: 0.4), 5).hombroDer.x, closeTo(0.7, 1e-9));
    });
  });

  group('Anclaje de la prenda', () {
    const area = Size(300, 400);
    const proporcion = 400 / 480;
    const anclaje = Anclaje();

    test('de frente: centrada en los hombros y escalada con hombros y torso', () {
      final c = colocarPrenda(pose: pose(), anclaje: anclaje, escalaTalla: 1.0, area: area, proporcionPng: proporcion);
      expect(c.angulo, closeTo(0, 1e-9));
      expect(c.ancho, closeTo(114.35, 0.1));
      expect(c.alto, closeTo(c.ancho / proporcion, 1e-9));
      expect(c.centro.dx, closeTo(150, 1e-9));
      expect(c.centro.dy, closeTo(120 + 0.4 * c.alto, 0.01));  // la línea de hombros del PNG queda sobre los hombros
    });

    test('sin caderas visibles el ancho sale solo de los hombros', () {
      final c = colocarPrenda(pose: pose(confianzaCaderas: 0.05), anclaje: anclaje, escalaTalla: 1.0, area: area, proporcionPng: proporcion);
      expect(c.ancho, closeTo(90 / 0.85, 1e-6));
    });

    test('la talla y el ajuste fino multiplican la escala', () {
      final base = colocarPrenda(pose: pose(confianzaCaderas: 0), anclaje: anclaje, escalaTalla: 1.0, area: area, proporcionPng: proporcion);
      final xl = colocarPrenda(pose: pose(confianzaCaderas: 0), anclaje: const Anclaje(ajuste: 1.2), escalaTalla: 1.1, area: area, proporcionPng: proporcion);
      expect(xl.ancho, closeTo(base.ancho * 1.1 * 1.2, 1e-6));
    });

    test('con los hombros inclinados la prenda gira igual', () {
      final c = colocarPrenda(pose: pose(dyHombros: 0.04), anclaje: anclaje, escalaTalla: 1.0, area: area, proporcionPng: proporcion);
      expect(c.angulo, closeTo(math.atan2(16, 90), 1e-9));
      expect(c.angulo, greaterThan(0));
    });

    test('da lo mismo cuál hombro se llame izquierdo (con la cámara en espejo se intercambian)', () {
      final p = pose();
      final cambiado = PoseCuerpo(hombroIzq: p.hombroDer, hombroDer: p.hombroIzq, caderaIzq: p.caderaDer, caderaDer: p.caderaIzq);
      final a = colocarPrenda(pose: p, anclaje: anclaje, escalaTalla: 1.0, area: area, proporcionPng: proporcion);
      final b = colocarPrenda(pose: cambiado, anclaje: anclaje, escalaTalla: 1.0, area: area, proporcionPng: proporcion);
      expect((a.centro - b.centro).distance, lessThan(1e-9));
      expect(a.ancho, closeTo(b.ancho, 1e-9));
    });
  });

  group('Guía y bloqueo', () {
    test('cada situación tiene su mensaje', () {
      expect(evaluarPose(null), Guia.sinPersona);
      expect(evaluarPose(pose(confianza: 0.1)), Guia.subeLaCamara);
      expect(evaluarPose(pose(ancho: 0.10)), Guia.acercate);
      expect(evaluarPose(pose(ancho: 0.90)), Guia.alejate);
      expect(evaluarPose(pose(ancho: 0.16, yCaderas: 0.90)), Guia.ponteDeFrente);  // de lado los hombros se juntan
      expect(evaluarPose(pose()), Guia.bien);
      expect(mensajesGuia[Guia.acercate], 'Acércate un poco');
    });

    test('basta una confianza de 0.30 (el móvil viejo pedía 0.42)', () {
      expect(evaluarPose(pose(confianza: 0.31)), Guia.bien);
      expect(evaluarPose(pose(confianza: 0.29)), Guia.subeLaCamara);
    });

    test('bloquea con 2 cuadros buenos y avisa solo la primera vez', () {
      final b = BloqueoPose();
      expect(b.registrar(pose()), isFalse);
      expect(b.bloqueado, isFalse);
      expect(b.registrar(pose()), isTrue);
      expect(b.bloqueado, isTrue);
      expect(b.registrar(pose()), isFalse);
    });

    test('con 1 cuadro bueno también se puede bloquear', () {
      expect(BloqueoPose(cuadrosParaBloquear: 1).registrar(pose()), isTrue);
    });

    test('un cuadro malo suelto no apaga la prenda, pero 8 seguidos sí', () {
      final b = BloqueoPose();
      b.registrar(pose());
      b.registrar(pose());
      b.registrar(null);
      expect(b.bloqueado, isTrue);
      for (var i = 0; i < 7; i++) {
        b.registrar(null);
      }
      expect(b.bloqueado, isFalse);
      expect(b.registrar(pose()), isFalse);
      expect(b.registrar(pose()), isTrue);  // para volver a engancharla bastan 2 cuadros buenos
    });
  });

  group('Métricas de rendimiento', () {
    test('FPS, latencia media y tiempo hasta ver la prenda', () {
      var ahora = DateTime(2026, 10, 29, 12);
      final m = MedidorRendimiento(reloj: () => ahora);
      for (var i = 0; i < 20; i++) {
        ahora = ahora.add(const Duration(milliseconds: 50));
        m.registrarCuadro(const Duration(milliseconds: 40));
      }
      expect(m.fps, 20);
      expect(m.latenciaMs, 40);
      expect(m.cumpleFps, isTrue);
      m.prendaVisible();
      expect(m.prendaVisibleMs, 990);  // desde que llegó el primer cuadro (a los 50 ms, menos los 40 ms que tardó su detección) hasta el último a los 1000 ms
      expect(m.cumplePrenda, isTrue);  // 990 ms: justo dentro de la meta de 1 segundo
      ahora = ahora.add(const Duration(seconds: 2));
      final lento = MedidorRendimiento(reloj: () => ahora)..registrarCuadro(const Duration(milliseconds: 100));
      ahora = ahora.add(const Duration(milliseconds: 1500));
      lento.prendaVisible();
      expect(lento.cumplePrenda, isFalse);  // 1.6 s: no cumple
    });

    test('la prenda aparece en menos de 1 segundo y los FPS bajos se notan', () {
      var ahora = DateTime(2026, 10, 29, 12);
      final m = MedidorRendimiento(reloj: () => ahora);
      for (var i = 0; i < 5; i++) {
        ahora = ahora.add(const Duration(milliseconds: 150));
        m.registrarCuadro(const Duration(milliseconds: 100));
      }
      m.prendaVisible();
      expect(m.prendaVisibleMs, lessThan(1000));
      expect(m.cumplePrenda, isTrue);
      expect(m.fps, 5);
      expect(m.cumpleFps, isFalse);
      ahora = ahora.add(const Duration(seconds: 3));
      m.registrarCuadro(const Duration(milliseconds: 100));
      expect(m.fps, 1);  // los cuadros de hace más de un segundo ya no cuentan
    });
  });

  group('Datos del vestidor', () {
    late ApiFalsa api;
    late int descargas;
    late VestidorRepository repo;

    setUp(() {
      api = ApiFalsa()..respuesta = _producto();
      descargas = 0;
      repo = VestidorRepository(api, descargar: (uri) async {
        descargas++;
        return Uint8List.fromList([137, 80, 78, 71]);
      });
    });

    test('interpreta la respuesta del servidor: colores listos, anclaje y escala por talla', () async {
      final p = await repo.producto(7);
      expect(p.admite, isTrue);
      expect(p.colores.map((c) => c.listo), [false, true]);
      expect(p.colores[1].proporcion, closeTo(400 / 480, 1e-9));
      expect(p.colores[1].anclaje!.anchoHombros, 0.85);
      expect(p.escalaDe('S'), 0.96);
      expect(p.escalaDe('xl'), 1.1);
      expect(p.escalaDe('30'), 1.0);  // talla numérica o desconocida: valor por defecto
    });

    test('la imagen se pide al servidor de medios (no a /api) y se guarda en memoria', () async {
      expect(VestidorRepository.urlDeImagen('/media/1/productos/7/rojo.png').toString(), 'http://10.0.2.2:8000/media/1/productos/7/rojo.png');
      await repo.imagen('/media/a.png');
      await repo.imagen('/media/a.png');
      expect(descargas, 1);
    });

    test('precargar deja todo en memoria y nunca falla', () async {
      await repo.precargar(7);
      await repo.precargar(7);
      expect((api.consultas, descargas), (1, 1));
      api.fallo = ApiException('Sin conexión con el servidor.', sinConexion: true);
      await VestidorRepository(api).precargar(99);  // no lanza
    });

    test('una prenda que no es superior no admite vestidor', () async {
      api.respuesta = _producto(admite: false);
      final p = await repo.producto(7, forzar: true);
      expect((p.admite, p.mensaje), (false, 'Esta prenda no admite vestidor.'));
      expect(p.colores, isEmpty);
    });
  });

  group('Controlador del vestidor', () {
    late ApiFalsa api;
    late VestidorController c;

    setUp(() {
      api = ApiFalsa()..respuesta = _producto();
      c = VestidorController(VestidorRepository(api, descargar: (_) async => Uint8List.fromList([1, 2, 3])), 7);
    });

    test('al cargar elige el primer color con imagen y la talla pedida', () async {
      await c.cargar(tallaInicial: 'M');
      expect((c.cargando, c.error, c.color?.nombre, c.talla), (false, null, 'Rojo', 'M'));
      expect(c.tallas, ['M', 'S', 'XL']);
      expect(c.png, isNotNull);
    });

    test('la prenda aparece al segundo cuadro bueno y se mide el tiempo', () async {
      await c.cargar();
      expect(c.colocacion(const Size(300, 400)), isNull);
      c.registrarDeteccion(pose(), const Duration(milliseconds: 30), 0.0);
      expect(c.prendaVisible, isFalse);
      c.registrarDeteccion(pose(), const Duration(milliseconds: 30), 0.05);
      expect(c.prendaVisible, isTrue);
      expect(c.colocacion(const Size(300, 400)), isNotNull);
      expect(c.metricas.prendaVisibleMs, isNotNull);
    });

    test('la talla cambia el tamaño de la prenda', () async {
      await c.cargar(tallaInicial: 'S');
      c.registrarDeteccion(pose(confianzaCaderas: 0), const Duration(milliseconds: 30), 0.0);
      c.registrarDeteccion(pose(confianzaCaderas: 0), const Duration(milliseconds: 30), 0.05);
      final s = c.colocacion(const Size(300, 400))!.ancho;
      c.elegirTalla('XL');
      expect(c.colocacion(const Size(300, 400))!.ancho, closeTo(s / 0.96 * 1.1, 1e-6));
    });

    test('si la persona se va, la prenda se oculta y la guía lo dice', () async {
      await c.cargar();
      c.registrarDeteccion(pose(), const Duration(milliseconds: 30), 0.0);
      c.registrarDeteccion(pose(), const Duration(milliseconds: 30), 0.05);
      for (var i = 0; i < 8; i++) {
        c.registrarDeteccion(null, const Duration(milliseconds: 30), 0.1 + i * 0.05);
      }
      expect((c.prendaVisible, c.guia), (false, Guia.sinPersona));
    });

    test('una prenda sin vestidor o un error del servidor se informan', () async {
      api.respuesta = _producto(admite: false);
      await c.cargar();
      expect((c.producto!.admite, c.color), (false, null));
      final otra = VestidorController(VestidorRepository(api), 8);  // un producto que todavía no está en memoria
      api.fallo = ApiException('No tiene permisos para esta operación.', statusCode: 403);
      await otra.cargar();
      expect(otra.error, 'No tiene permisos para esta operación.');
    });
  });
}
