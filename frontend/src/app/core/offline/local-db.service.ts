import { Injectable } from '@angular/core';
import { DBSchema, IDBPDatabase, openDB } from 'idb';
import { MetaCatalogo, OperacionLocal, ProductoLocal } from '../offline.models';

/**
 * Almacenamiento local de la PWA (IndexedDB). Aquí vive lo que permite operar sin conexión (RNF03):
 *  - sesion: contexto de sesión (CU-02, paso 8)
 *  - catalogo: productos con sus variantes, precios y stock descargados (CU-37)
 *  - operaciones: cola de operaciones con su estado local (CU-38, CU-39); sobreviven al cierre del navegador
 *  - cache_meta: fecha de la última sincronización y datos de la descarga (RN16: avisar que la información puede estar desactualizada)
 */
interface FashionDB extends DBSchema {
  sesion: { key: string; value: unknown };
  catalogo: { key: number; value: ProductoLocal };
  operaciones: { key: string; value: OperacionLocal };
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

  // ---- CU-37: catálogo local ----
  async guardarCatalogo(productos: ProductoLocal[], meta: MetaCatalogo): Promise<void> {
    const db = await this.db();
    const tx = db.transaction(['catalogo', 'cache_meta'], 'readwrite');
    await tx.objectStore('catalogo').clear();
    for (const p of productos) await tx.objectStore('catalogo').put(p);
    await tx.objectStore('cache_meta').put(meta, 'catalogo');
    await tx.done;
  }
  async leerCatalogo(): Promise<ProductoLocal[]> {
    try { return await (await this.db()).getAll('catalogo'); } catch { return []; }
  }
  async metaCatalogo(): Promise<MetaCatalogo | undefined> {
    try { return (await (await this.db()).get('cache_meta', 'catalogo')) as MetaCatalogo | undefined; } catch { return undefined; }
  }
  async actualizarProducto(p: ProductoLocal): Promise<void> {
    try { await (await this.db()).put('catalogo', p); } catch { /* noop */ }
  }
  async borrarCatalogo(): Promise<void> {
    try {
      const db = await this.db();
      await db.clear('catalogo');
      await db.delete('cache_meta', 'catalogo');
    } catch { /* noop */ }
  }

  // ---- CU-38 y CU-39: cola de operaciones ----
  async guardarOperacion(o: OperacionLocal): Promise<void> { await (await this.db()).put('operaciones', o); }
  async operaciones(): Promise<OperacionLocal[]> {
    try { return await (await this.db()).getAll('operaciones'); } catch { return []; }
  }
  async borrarOperacion(id: string): Promise<void> { try { await (await this.db()).delete('operaciones', id); } catch { /* noop */ } }
}
