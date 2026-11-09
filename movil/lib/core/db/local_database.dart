import 'package:path/path.dart';
import 'package:sqflite/sqflite.dart';

import '../../features/offline/data/detalle_local.dart';

/// Persistencia local en SQLite (RNF03: lo registrado sin conexión sobrevive al cierre de la app).
///
/// - `sesion`: contexto de sesión (CU-02, paso 8: guardar la sesión para operar sin conexión).
/// - `sucursales_autorizadas`, `productos_locales`, `clientes_locales` y `meta`: el catálogo descargado (CU-37) y de cuándo es (RN16).
/// - `operaciones_pendientes`: la cola de operaciones sin conexión (venta de contado, reserva y compra del cliente) con su estado (CU-38, CU-39). Llevan siempre empresa, sucursal y usuario (RN11).
class LocalDatabase {
  LocalDatabase._();
  static final LocalDatabase instance = LocalDatabase._();

  static const version = 5;

  Database? _db;
  String? _rutaPrueba;

  Future<Database> get database async => _db ??= await _abrir();

  /// Solo para pruebas: abre la base en otra ruta (por ejemplo, en memoria).
  Future<void> reiniciar({String? ruta}) async {
    await _db?.close();
    _db = null;
    _rutaPrueba = ruta;
  }

  Future<Database> _abrir() async {
    final ruta =
        _rutaPrueba ?? join(await getDatabasesPath(), 'fashionstore.db');
    return openDatabase(
      ruta,
      version: version,
      onConfigure: (db) async => db.execute('PRAGMA foreign_keys = ON'),
      onCreate: (db, v) async {
        await db.execute('''
          CREATE TABLE sesion (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            access_token TEXT NOT NULL,
            refresh_token TEXT NOT NULL,
            contexto_json TEXT NOT NULL,
            actualizado_en TEXT NOT NULL
          )''');
        await _crearTablasOffline(db);
        await db.execute(
            'CREATE TABLE vestidor_local (producto_id INTEGER PRIMARY KEY, producto_json TEXT NOT NULL)');
      },
      onUpgrade: (db, anterior, nueva) async {
        if (anterior < 2) {
          // la versión 1 solo tenía tablas vacías para el catálogo y las operaciones: se rehacen conservando la sesión
          for (final t in [
            'operaciones_pendientes',
            'productos_locales',
            'sucursales_autorizadas'
          ]) {
            await db.execute('DROP TABLE IF EXISTS $t');
          }
          await _crearTablasOffline(db);
        } else if (anterior < 3) {
          // la versión 3 admite la operación COMPRA del cliente: SQLite no cambia un CHECK, así que la tabla se rehace SIN perder lo pendiente de sincronizar
          await db.execute(
              'ALTER TABLE operaciones_pendientes RENAME TO operaciones_pendientes_v2');
          await db.execute('DROP INDEX IF EXISTS ix_operaciones_estado');
          await _crearOperaciones(db);
          await db.execute(
              'INSERT INTO operaciones_pendientes SELECT * FROM operaciones_pendientes_v2');
          await db.execute('DROP TABLE operaciones_pendientes_v2');
        }
        if (anterior < 4) {
          await db.execute(
              'CREATE TABLE vestidor_local (producto_id INTEGER PRIMARY KEY, producto_json TEXT NOT NULL)');
        }
        if (anterior < 5) {
          // la versión 5 admite CANCELAR_RESERVA en la cola (antes el CHECK la rechazaba) y agrega el almacenamiento relacional de §6.3.
          // La cola se rehace SIN perder ninguna operación pendiente y las ventas y reservas que ya tenía pasan a sus tablas de detalle.
          if (anterior >= 2) {
            await db.execute('ALTER TABLE operaciones_pendientes RENAME TO operaciones_pendientes_v4');
            await db.execute('DROP INDEX IF EXISTS ix_operaciones_estado');
            await _crearOperaciones(db);
            await db.execute('INSERT INTO operaciones_pendientes SELECT * FROM operaciones_pendientes_v4');
            await db.execute('DROP TABLE operaciones_pendientes_v4');
          }
          await DetalleLocal.crearTablas(db);
          await DetalleLocal.poblarDesdeOperaciones(db);
        }
      },
    );
  }

  Future<void> _crearTablasOffline(Database db) async {
    await db.execute('''
      CREATE TABLE sucursales_autorizadas (
        id INTEGER PRIMARY KEY,
        empresa_id INTEGER NOT NULL,
        nombre TEXT NOT NULL,
        ciudad TEXT,
        direccion TEXT,
        horario TEXT
      )''');
    await db.execute('''
      CREATE TABLE productos_locales (
        id INTEGER PRIMARY KEY,
        empresa_id INTEGER NOT NULL,
        nombre TEXT NOT NULL,
        categoria TEXT NOT NULL,
        genero TEXT,
        imagen TEXT,
        variantes_json TEXT NOT NULL,
        descargado_en TEXT NOT NULL
      )''');
    await db.execute('''
      CREATE TABLE clientes_locales (
        id INTEGER PRIMARY KEY,
        empresa_id INTEGER NOT NULL,
        nombre TEXT NOT NULL,
        email TEXT NOT NULL
      )''');
    await db.execute(
        'CREATE TABLE meta (clave TEXT PRIMARY KEY, valor TEXT NOT NULL)');
    await _crearOperaciones(db);
    await DetalleLocal.crearTablas(db); // las tablas de detalle cuelgan de la cola: se crean después de ella (y nunca antes de rehacerla en una migración)
  }

  Future<void> _crearOperaciones(Database db) async {
    await db.execute('''
      CREATE TABLE operaciones_pendientes (
        id TEXT PRIMARY KEY,
        empresa_id INTEGER NOT NULL,
        sucursal_id INTEGER,
        usuario_id INTEGER NOT NULL,
        tipo TEXT NOT NULL CHECK (tipo IN ('VENTA_CONTADO','RESERVA','COMPRA','CANCELAR_RESERVA')),
        payload_json TEXT NOT NULL,
        estado TEXT NOT NULL CHECK (estado IN
          ('REGISTRADA_LOCAL','ENVIADA','CONFIRMADA','RECHAZADA','EN_CONFLICTO')),
        intentos INTEGER NOT NULL DEFAULT 0,
        mensaje TEXT NOT NULL DEFAULT '',
        referencia TEXT,
        comprobante TEXT,
        detalle_json TEXT,
        resumen TEXT NOT NULL DEFAULT '',
        creado_en TEXT NOT NULL
      )''');
    await db.execute(
        'CREATE INDEX ix_operaciones_estado ON operaciones_pendientes (empresa_id, usuario_id, estado)');
  }
}
