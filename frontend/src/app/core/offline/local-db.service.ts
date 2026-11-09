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
  carrito_local: { key: string; value: unknown };
  // §6.3: ventas y reservas con sus detalles, resultados y registro técnico de la sincronización (cuelgan de `operaciones`, la bandeja de salida)
  ventas: { key: string; value: FilaVenta; indexes: { por_fecha: string } };
  detalle_venta: { key: string; value: LineaLocal & { operacion_id: string }; indexes: { por_operacion: string } };
  reservas: { key: string; value: FilaReserva; indexes: { por_fecha: string } };
  detalle_reserva: { key: string; value: LineaLocal & { operacion_id: string }; indexes: { por_operacion: string } };
  resultados_sync: { key: string; value: ResultadoLocal; indexes: { por_estado: string; por_fecha: string } };
  registro_sincronizacion: { key: number; value: IntentoSync; indexes: { por_fecha: string } };
}

export interface LineaLocal { variante_id: number; cantidad: number; precio_unitario?: string | null }
export interface FilaVenta { operacion_id: string; empresa_id: number; sucursal_id: number | null; usuario_id: number; cliente_email: string | null; forma_pago: string; monto_recibido: string; total: string; registrada_en: string }
export interface FilaReserva { operacion_id: string; empresa_id: number; sucursal_id: number | null; usuario_id: number; programada_para: string | null; notas: string; registrada_en: string }
export interface ResultadoLocal { operacion_id: string; estado: string; mensaje: string; referencia: string | null; comprobante: string | null; actualizado_en: string }
export interface IntentoSync { id?: number; operacion_id: string; tipo: string; intento: number; fecha: string; resultado: string; codigo: string; motivo: string }

/** Líneas y cabecera de una venta o reserva, sacadas del cuerpo con que se registró. */
function desglosar(o: OperacionLocal) {
  const items = ((o.payload['items'] as LineaLocal[] | undefined) ?? []).map((i) => ({ variante_id: i.variante_id, cantidad: i.cantidad, precio_unitario: i.precio_unitario != null ? String(i.precio_unitario) : null }));
  if (o.tipo === 'VENTA_CONTADO') {
    const total = items.reduce((s, i) => s + Number(i.precio_unitario ?? 0) * i.cantidad, 0);
    const venta: FilaVenta = { operacion_id: o.id, empresa_id: o.empresa_id, sucursal_id: o.sucursal_id, usuario_id: o.usuario_id, cliente_email: (o.payload['cliente_email'] as string | null) ?? null, forma_pago: String(o.payload['forma_pago'] ?? 'EFECTIVO'), monto_recibido: String(o.payload['monto_recibido'] ?? '0'), total: total.toFixed(2), registrada_en: o.creada_en };
    return { venta, reserva: null, items };
  }
  if (o.tipo === 'RESERVA') {
    const reserva: FilaReserva = { operacion_id: o.id, empresa_id: o.empresa_id, sucursal_id: (o.payload['sucursal_id'] as number | undefined) ?? o.sucursal_id, usuario_id: o.usuario_id, programada_para: (o.payload['programada_para'] as string | undefined) ?? null, notas: String(o.payload['notas'] ?? ''), registrada_en: o.creada_en };
    return { venta: null, reserva, items };
  }
  return { venta: null, reserva: null, items };
}

@Injectable({ providedIn: 'root' })
export class LocalDbService {
  private dbPromise: Promise<IDBPDatabase<FashionDB>> | null = null;

  private db(): Promise<IDBPDatabase<FashionDB>> {
    this.dbPromise ??= openDB<FashionDB>('fashionstore', 3, {
      async upgrade(db, anterior, _nueva, tx) {
        if (!db.objectStoreNames.contains('sesion')) db.createObjectStore('sesion');
        if (!db.objectStoreNames.contains('catalogo')) db.createObjectStore('catalogo', { keyPath: 'id' });
        if (!db.objectStoreNames.contains('operaciones')) db.createObjectStore('operaciones', { keyPath: 'id' });
        if (!db.objectStoreNames.contains('cache_meta')) db.createObjectStore('cache_meta');
        if (!db.objectStoreNames.contains('carrito_local')) db.createObjectStore('carrito_local');
        if (anterior < 3) {
          // versión 3: almacenes relacionales de §6.3. La cola existente NO se toca: sus ventas y reservas se copian a los almacenes nuevos.
          db.createObjectStore('ventas', { keyPath: 'operacion_id' }).createIndex('por_fecha', 'registrada_en');
          db.createObjectStore('detalle_venta', { autoIncrement: true }).createIndex('por_operacion', 'operacion_id');
          db.createObjectStore('reservas', { keyPath: 'operacion_id' }).createIndex('por_fecha', 'registrada_en');
          db.createObjectStore('detalle_reserva', { autoIncrement: true }).createIndex('por_operacion', 'operacion_id');
          const resultados = db.createObjectStore('resultados_sync', { keyPath: 'operacion_id' });
          resultados.createIndex('por_estado', 'estado');
          resultados.createIndex('por_fecha', 'actualizado_en');
          db.createObjectStore('registro_sincronizacion', { keyPath: 'id', autoIncrement: true }).createIndex('por_fecha', 'fecha');
          for (const o of (await tx.objectStore('operaciones').getAll()) as OperacionLocal[]) await LocalDbService.copiarDetalle(tx, o);
        }
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

  async guardarCarritoLocal(clave: string, valor: unknown): Promise<void> { await (await this.db()).put('carrito_local', valor, clave); }
  async leerCarritoLocal<T>(clave: string): Promise<T | undefined> { try { return (await (await this.db()).get('carrito_local', clave)) as T | undefined; } catch { return undefined; } }
  async borrarCarritoLocal(clave: string): Promise<void> { try { await (await this.db()).delete('carrito_local', clave); } catch { /* noop */ } }
  async guardarComprasClienteLocal(clave: string, valor: unknown): Promise<void> { await (await this.db()).put('cache_meta', valor, `compras_cliente_${clave}`); }
  async leerComprasClienteLocal<T>(clave: string): Promise<T | undefined> { try { return (await (await this.db()).get('cache_meta', `compras_cliente_${clave}`)) as T | undefined; } catch { return undefined; } }
  async guardarComprobanteLocal(id: number, blob: Blob): Promise<void> { await (await this.db()).put('cache_meta', blob, `comprobante_${id}`); }
  async leerComprobanteLocal(id: number): Promise<Blob | undefined> { try { return (await (await this.db()).get('cache_meta', `comprobante_${id}`)) as Blob | undefined; } catch { return undefined; } }
  async guardarReservasClienteLocal(clave: string, valor: unknown): Promise<void> { await (await this.db()).put('cache_meta', valor, `reservas_cliente_${clave}`); }
  async leerReservasClienteLocal<T>(clave: string): Promise<T | undefined> { try { return (await (await this.db()).get('cache_meta', `reservas_cliente_${clave}`)) as T | undefined; } catch { return undefined; } }
  async guardarAvisosLocal(clave: string, avisos: unknown): Promise<void> { await (await this.db()).put('cache_meta', avisos, `avisos_${clave}`); }
  async leerAvisosLocal<T>(clave: string): Promise<T | undefined> { try { return (await (await this.db()).get('cache_meta', `avisos_${clave}`)) as T | undefined; } catch { return undefined; } }
  async guardarLecturasPendientes(clave: string, ids: number[]): Promise<void> { await (await this.db()).put('cache_meta', [...new Set(ids)], `avisos_leer_${clave}`); }
  async leerLecturasPendientes(clave: string): Promise<number[]> { try { return ((await (await this.db()).get('cache_meta', `avisos_leer_${clave}`)) as number[] | undefined) ?? []; } catch { return []; } }

  // ---- CU-38 y CU-39: cola de operaciones ----
  /** Copia la venta o reserva y sus líneas a los almacenes de detalle (sin duplicar: borra las líneas anteriores de esa operación). */
  static async copiarDetalle(tx: { objectStore: (n: any) => any }, o: OperacionLocal): Promise<void> {
    const { venta, reserva, items } = desglosar(o);
    if (!venta && !reserva) return;
    const nombreCab = venta ? 'ventas' : 'reservas', nombreDet = venta ? 'detalle_venta' : 'detalle_reserva';
    await tx.objectStore(nombreCab).put(venta ?? reserva);
    const det = tx.objectStore(nombreDet);
    for (const clave of await det.index('por_operacion').getAllKeys(o.id)) await det.delete(clave);
    for (const i of items) await det.add({ ...i, operacion_id: o.id });
    if (o.estado !== 'REGISTRADA_LOCAL' && o.estado !== 'ENVIADA') await tx.objectStore('resultados_sync').put({ operacion_id: o.id, estado: o.estado, mensaje: o.mensaje, referencia: o.referencia, comprobante: o.comprobante, actualizado_en: new Date().toISOString() });
  }

  async guardarOperacion(o: OperacionLocal): Promise<void> {
    const db = await this.db();
    const tx = db.transaction(['operaciones', 'ventas', 'detalle_venta', 'reservas', 'detalle_reserva', 'resultados_sync'], 'readwrite');
    await tx.objectStore('operaciones').put(o);
    const yaTieneDetalle = o.tipo === 'VENTA_CONTADO' ? await tx.objectStore('ventas').get(o.id) : o.tipo === 'RESERVA' ? await tx.objectStore('reservas').get(o.id) : true;
    if (!yaTieneDetalle) await LocalDbService.copiarDetalle(tx, o);  // al registrar: se crea el detalle; al cambiar de estado NO se borra ni se rehace (§5.4)
    if (o.estado !== 'REGISTRADA_LOCAL' && o.estado !== 'ENVIADA') await tx.objectStore('resultados_sync').put({ operacion_id: o.id, estado: o.estado, mensaje: o.mensaje, referencia: o.referencia, comprobante: o.comprobante, actualizado_en: new Date().toISOString() });
    await tx.done;
  }

  /** El cuerpo que viaja al servidor se arma desde el detalle (la fuente de los datos). Si la operación no tiene detalle, se usa su cuerpo guardado. */
  async payloadDesdeDetalle(o: OperacionLocal): Promise<Record<string, unknown>> {
    try {
      const db = await this.db();
      const lineas = o.tipo === 'VENTA_CONTADO' ? await db.getAllFromIndex('detalle_venta', 'por_operacion', o.id) : o.tipo === 'RESERVA' ? await db.getAllFromIndex('detalle_reserva', 'por_operacion', o.id) : [];
      if (!lineas.length) return o.payload;
      const items = lineas.map((l) => ({ variante_id: l.variante_id, cantidad: l.cantidad, ...(l.precio_unitario != null ? { precio_unitario: l.precio_unitario } : {}) }));
      return { ...o.payload, items };
    } catch { return o.payload; }
  }

  /** RNF10: una fila por intento, con código y motivo técnico, sin datos personales. */
  async anotarIntento(i: IntentoSync): Promise<void> { try { await (await this.db()).add('registro_sincronizacion', i); } catch { /* el registro es de ayuda: nunca debe impedir sincronizar */ } }
  async registroSincronizacion(limite = 100): Promise<IntentoSync[]> {
    try { return (await (await this.db()).getAllFromIndex('registro_sincronizacion', 'por_fecha')).reverse().slice(0, limite); } catch { return []; }
  }
  async detalleDeVenta(id: string) { return (await this.db()).getAllFromIndex('detalle_venta', 'por_operacion', id); }
  async detalleDeReserva(id: string) { return (await this.db()).getAllFromIndex('detalle_reserva', 'por_operacion', id); }
  async resultadoDe(id: string) { return (await this.db()).get('resultados_sync', id); }
  async operaciones(): Promise<OperacionLocal[]> {
    try { return await (await this.db()).getAll('operaciones'); } catch { return []; }
  }
  async borrarOperacion(id: string): Promise<void> {
    try {
      const db = await this.db();
      const tx = db.transaction(['operaciones', 'ventas', 'detalle_venta', 'reservas', 'detalle_reserva', 'resultados_sync'], 'readwrite');
      await tx.objectStore('operaciones').delete(id);
      await tx.objectStore('ventas').delete(id);
      await tx.objectStore('reservas').delete(id);
      await tx.objectStore('resultados_sync').delete(id);
      for (const nombre of ['detalle_venta', 'detalle_reserva'] as const) {
        const det = tx.objectStore(nombre);
        for (const clave of await det.index('por_operacion').getAllKeys(id)) await det.delete(clave);
      }
      await tx.done;
    } catch { /* noop */ }
  }
}
