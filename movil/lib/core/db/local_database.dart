import 'package:path/path.dart';
import 'package:sqflite/sqflite.dart';

/// Persistencia local en SQLite (RNF03: lo registrado sin conexión sobrevive al cierre de la app).
///
/// Lote 1: se usa la tabla `sesion` (CU-02, paso 8: guardar la sesión para operar sin conexión).
/// Las demás tablas se crean desde ahora para el Lote 2 (CU-37 catálogo local, CU-38/39 operaciones
/// pendientes y su sincronización) y llevan siempre empresa y sucursal (RN11).
class LocalDatabase {
  LocalDatabase._();
  static final LocalDatabase instance = LocalDatabase._();

  Database? _db;

  Future<Database> get database async => _db ??= await _abrir();

  Future<Database> _abrir() async {
    final ruta = join(await getDatabasesPath(), 'fashionstore.db');
    return openDatabase(
      ruta,
      version: 1,
      onConfigure: (db) async => db.execute('PRAGMA foreign_keys = ON'),
      onCreate: (db, version) async {
        await db.execute('''
          CREATE TABLE sesion (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            access_token TEXT NOT NULL,
            refresh_token TEXT NOT NULL,
            contexto_json TEXT NOT NULL,
            actualizado_en TEXT NOT NULL
          )''');
        await db.execute('''
          CREATE TABLE sucursales_autorizadas (
            id INTEGER PRIMARY KEY,
            empresa_id INTEGER NOT NULL,
            nombre TEXT NOT NULL
          )''');
        await db.execute('''
          CREATE TABLE productos_locales (
            id INTEGER PRIMARY KEY,
            empresa_id INTEGER NOT NULL,
            nombre TEXT NOT NULL,
            precio REAL NOT NULL,
            descargado_en TEXT NOT NULL
          )''');
        await db.execute('''
          CREATE TABLE operaciones_pendientes (
            id TEXT PRIMARY KEY,
            empresa_id INTEGER NOT NULL,
            sucursal_id INTEGER,
            tipo TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            estado TEXT NOT NULL CHECK (estado IN
              ('REGISTRADA_LOCAL','ENVIADA','CONFIRMADA','RECHAZADA','EN_CONFLICTO')),
            intentos INTEGER NOT NULL DEFAULT 0,
            resultado TEXT,
            creado_en TEXT NOT NULL
          )''');
        await db.execute(
            'CREATE INDEX ix_operaciones_estado ON operaciones_pendientes (empresa_id, estado)');
      },
    );
  }
}
