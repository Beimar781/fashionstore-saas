import 'fake-indexeddb/auto';
import { openDB } from 'idb';
import { beforeEach, describe, expect, it } from 'vitest';
import { OperacionLocal } from '../offline.models';
import { LocalDbService } from './local-db.service';

const venta = (id: string, estado: OperacionLocal['estado'] = 'REGISTRADA_LOCAL'): OperacionLocal => ({
  id, empresa_id: 1, sucursal_id: 1, usuario_id: 5, tipo: 'VENTA_CONTADO', estado, intentos: 0, mensaje: '', referencia: null, comprobante: null, detalle: null,
  creada_en: '2026-11-01T10:00:00Z', resumen: 'Venta',
  payload: { items: [{ variante_id: 100, cantidad: 2, precio_unitario: '40.00' }, { variante_id: 101, cantidad: 1, precio_unitario: '90.00' }], forma_pago: 'EFECTIVO', monto_recibido: '200.00', cliente_email: null },
});

const reserva = (id: string): OperacionLocal => ({
  id, empresa_id: 1, sucursal_id: 1, usuario_id: 5, tipo: 'RESERVA', estado: 'REGISTRADA_LOCAL', intentos: 0, mensaje: '', referencia: null, comprobante: null, detalle: null,
  creada_en: '2026-11-01T11:00:00Z', resumen: 'Reserva', payload: { sucursal_id: 1, programada_para: '2026-11-20T10:00', notas: 'x', items: [{ variante_id: 100, cantidad: 3 }] },
});

describe('almacenamiento local relacional (§6.3)', () => {
  beforeEach(() => { (globalThis as any).indexedDB = new (globalThis as any).IDBFactory(); });

  it('al registrar una venta y una reserva se guardan sus cabeceras y líneas', async () => {
    const db = new LocalDbService();
    await db.guardarOperacion(venta('v-1'));
    await db.guardarOperacion(reserva('r-1'));
    expect((await db.detalleDeVenta('v-1')).map((l) => l.cantidad)).toEqual([2, 1]);
    expect((await db.detalleDeReserva('r-1'))[0].cantidad).toBe(3);
  });

  it('cambiar de estado no borra ni duplica el detalle, y deja el resultado', async () => {
    const db = new LocalDbService();
    const o = venta('v-1');
    await db.guardarOperacion(o);
    o.estado = 'CONFIRMADA'; o.referencia = 'PED-1'; o.comprobante = 'CMP-001-000001';
    await db.guardarOperacion(o);
    expect(await db.detalleDeVenta('v-1')).toHaveLength(2);
    expect((await db.resultadoDe('v-1'))?.comprobante).toBe('CMP-001-000001');
  });

  it('el cuerpo que viaja al servidor se arma desde el detalle', async () => {
    const db = new LocalDbService();
    const o = venta('v-1');
    await db.guardarOperacion(o);
    const cuerpo = await db.payloadDesdeDetalle(o);
    expect((cuerpo['items'] as { cantidad: number }[]).map((i) => i.cantidad)).toEqual([2, 1]);
    expect(cuerpo['forma_pago']).toBe('EFECTIVO');
  });

  it('borrar una operación terminada borra también su detalle y su resultado', async () => {
    const db = new LocalDbService();
    await db.guardarOperacion(venta('v-1', 'CONFIRMADA'));
    await db.guardarOperacion(venta('v-2'));
    await db.borrarOperacion('v-1');
    expect(await db.detalleDeVenta('v-1')).toHaveLength(0);
    expect(await db.resultadoDe('v-1')).toBeUndefined();
    expect(await db.detalleDeVenta('v-2')).toHaveLength(2);
  });

  it('el registro técnico guarda cada intento y se lee del más reciente al más antiguo', async () => {
    const db = new LocalDbService();
    await db.anotarIntento({ operacion_id: 'v-1', tipo: 'VENTA_CONTADO', intento: 1, fecha: '2026-11-01T10:00:00Z', resultado: 'SIN_RESPUESTA', codigo: 'SIN_RED', motivo: '' });
    await db.anotarIntento({ operacion_id: 'v-1', tipo: 'VENTA_CONTADO', intento: 2, fecha: '2026-11-01T10:05:00Z', resultado: 'CONFIRMADA', codigo: '200', motivo: '' });
    const filas = await db.registroSincronizacion();
    expect(filas.map((f) => f.intento)).toEqual([2, 1]);
  });

  it('RNF03 y migración: una cola de la versión 2 sobrevive a la actualización y sus ventas pasan a los almacenes de detalle', async () => {
    const vieja = await openDB('fashionstore', 2, {
      upgrade(db) {
        db.createObjectStore('sesion'); db.createObjectStore('catalogo', { keyPath: 'id' }); db.createObjectStore('operaciones', { keyPath: 'id' });
        db.createObjectStore('cache_meta'); db.createObjectStore('carrito_local');
      },
    });
    await vieja.put('operaciones', venta('v-1'));
    await vieja.put('operaciones', reserva('r-1'));
    await vieja.put('operaciones', { ...venta('c-1'), tipo: 'COMPRA', payload: { items: [] } });
    vieja.close();

    const db = new LocalDbService();
    const ids = (await db.operaciones()).map((o) => o.id).sort();
    expect(ids).toEqual(['c-1', 'r-1', 'v-1']);  // ninguna operación se perdió
    expect(await db.detalleDeVenta('v-1')).toHaveLength(2);
    expect(await db.detalleDeReserva('r-1')).toHaveLength(1);
  });
});
