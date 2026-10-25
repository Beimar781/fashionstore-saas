import { Injectable } from '@angular/core';
import { DBSchema, IDBPDatabase, openDB } from 'idb';

/**
 * Almacenamiento local de la PWA (IndexedDB). Aquí vive lo que permite operar sin conexión:
 *  - sesion: contexto de sesión (CU-02, paso 8)
 *  - catalogo / operaciones: se completan en el Lote 2 (CU-37 descarga de catálogo, CU-38/39 operaciones pendientes)
 *  - cache_meta: fecha de la última sincronización (RN16: avisar que la información puede estar desactualizada)
 */
interface FashionDB extends DBSchema {
  sesion: { key: string; value: unknown };
  catalogo: { key: number; value: { id: number; empresa_id: number } };
  operaciones: { key: string; value: { id: string; estado: string; empresa_id: number; sucursal_id: number | null } };
  cache_meta: { key: string; value: unknown };
}

@Injectable({ providedIn: 'root' })
export class LocalDbService {
  private dbPromise: Promise<IDBPDatabase<FashionDB>> | null = null;

  private db(): Promise<IDBPDatabase<FashionDB>> {
    this.dbPromise ??= openDB<FashionDB>('fashionstore', 1, {
      upgrade(db) {
        db.createObjectStore('sesion');
        db.createObjectStore('catalogo', { keyPath: 'id' });
        db.createObjectStore('operaciones', { keyPath: 'id' });
        db.createObjectStore('cache_meta');
      },
    });
    return this.dbPromise;
  }

  async guardarSesion(valor: unknown): Promise<void> {
    try { await (await this.db()).put('sesion', valor, 'actual'); } catch { /* sin IndexedDB: se usa solo localStorage */ }
  }
  async leerSesion<T>(): Promise<T | undefined> {
    try { return (await (await this.db()).get('sesion', 'actual')) as T | undefined; } catch { return undefined; }
  }
  async borrarSesion(): Promise<void> {
    try { await (await this.db()).delete('sesion', 'actual'); } catch { /* noop */ }
  }
  async marcarSincronizacion(): Promise<void> {
    try { await (await this.db()).put('cache_meta', new Date().toISOString(), 'ultima_sincronizacion'); } catch { /* noop */ }
  }
  async ultimaSincronizacion(): Promise<string | undefined> {
    try { return (await (await this.db()).get('cache_meta', 'ultima_sincronizacion')) as string | undefined; } catch { return undefined; }
  }
}
