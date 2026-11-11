import { signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { Router } from '@angular/router';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { OfflineApi } from '../api/offline.api';
import { AuthService } from '../auth/auth.service';
import { OperacionLocal } from '../offline.models';
import { EstadoConexionComponent } from '../ui/estado-conexion.component';
import { ToastService } from '../ui/toast.service';
import { CatalogoLocalService } from './catalogo-local.service';
import { ColaOperacionesService } from './cola-operaciones.service';
import { ConnectivityService } from './connectivity.service';
import { etiquetaDispositivo, lineaDeTiempo } from './linea-de-tiempo';
import { IntentoSync, LocalDbService } from './local-db.service';
import { rutaDeLaCola } from './rutas-cola';

const op = (extra: Partial<OperacionLocal> = {}): OperacionLocal => ({
  id: 'op-1', empresa_id: 1, sucursal_id: 1, usuario_id: 5, tipo: 'VENTA_CONTADO', payload: {}, estado: 'REGISTRADA_LOCAL', intentos: 0, mensaje: '', referencia: null, comprobante: null, detalle: null,
  creada_en: '2026-11-10T10:00:00Z', resumen: 'Venta de prueba', ...extra,
});
const intento = (n: number, resultado: string, extra: Partial<IntentoSync> = {}): IntentoSync => ({ operacion_id: 'op-1', tipo: 'VENTA_CONTADO', intento: n, fecha: `2026-11-10T10:0${n}:00Z`, resultado, codigo: '200', motivo: '', ...extra });

describe('Línea de tiempo de una operación (D5)', () => {
  it('pendiente: solo está registrada en este dispositivo y se enviará al volver la conexión', () => {
    const pasos = lineaDeTiempo(op(), [], 'Chrome en Windows');
    expect(pasos.map((p) => p.texto)).toEqual(['Registrada en este dispositivo (Chrome en Windows)', 'Pendiente: se enviará sola al volver la conexión']);
  });

  it('con un intento sin respuesta y luego confirmada, cuenta cada envío con su fecha', () => {
    const pasos = lineaDeTiempo(op({ estado: 'CONFIRMADA' }), [intento(2, 'CONFIRMADA'), intento(1, 'SIN_RESPUESTA', { codigo: 'SIN_RED' })], 'Chrome en Windows');
    expect(pasos.map((p) => p.texto)).toEqual([
      'Registrada en este dispositivo (Chrome en Windows)', 'Envío 1: el servidor no respondió (SIN_RED); se reintentará', 'Envío 2: confirmada por el servidor']);
    expect(pasos[2].tipo).toBe('ok');
  });

  it('un conflicto que el Encargado resolvió termina en «resuelta»', () => {
    const conflicto = intento(1, 'EN_CONFLICTO', { motivo: 'No hay existencias suficientes' });
    expect(lineaDeTiempo(op({ estado: 'CONFIRMADA' }), [conflicto]).at(-1)!.texto).toBe('Resuelta por el Encargado: reintentada y confirmada');
    expect(lineaDeTiempo(op({ estado: 'RECHAZADA' }), [conflicto]).at(-1)!.texto).toBe('Resuelta por el Encargado: descartada');
    expect(lineaDeTiempo(op({ estado: 'EN_CONFLICTO' }), [conflicto]).at(-1)!.tipo).toBe('warn');
  });

  it('ignora los envíos de otras operaciones y nombra el dispositivo', () => {
    expect(lineaDeTiempo(op(), [intento(1, 'CONFIRMADA', { operacion_id: 'otra' })]).length).toBe(2);
    expect(etiquetaDispositivo('Mozilla/5.0 (Windows NT 10.0) Chrome/120 Safari/537')).toBe('Chrome en Windows');
    expect(etiquetaDispositivo('Mozilla/5.0 (Linux; Android 14) Chrome/120 Mobile Safari/537')).toBe('Chrome en Android');
  });
});

describe('Deshacer una operación sin sincronizar (D5)', () => {
  const moverStock = vi.fn(async (..._a: unknown[]) => undefined);
  const restaurarDevolvible = vi.fn(async (..._a: unknown[]) => undefined);
  const borrarOperacion = vi.fn(async (..._a: unknown[]) => undefined);
  let cola: ColaOperacionesService;
  let toast: ToastService;

  beforeEach(() => {
    moverStock.mockClear(); restaurarDevolvible.mockClear(); borrarOperacion.mockClear();
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({
      providers: [
        { provide: OfflineApi, useValue: {} },
        { provide: AuthService, useValue: { autenticado: () => false, sesion: () => ({ usuario: { id: 5 }, empresa: { id: 1 } }), rol: () => 'Cajero' } },
        { provide: ConnectivityService, useValue: { online: signal(false) } },
        { provide: LocalDbService, useValue: { operaciones: async () => [], ultimaSincronizacion: async () => undefined, guardarOperacion: async () => undefined, borrarOperacion } },
        { provide: CatalogoLocalService, useValue: { moverStock, restaurarDevolvible } },
      ],
    });
    cola = TestBed.inject(ColaOperacionesService);
    toast = TestBed.inject(ToastService);
  });

  it('una venta sin enviar sale de la cola y su stock vuelve a la copia local', async () => {
    const venta = await cola.registrar('VENTA_CONTADO', { items: [{ variante_id: 100, cantidad: 2 }] }, 1, 'Venta', { stock: [{ variante_id: 100, delta: -2 }] });
    expect(cola.puedeDeshacer(venta)).toBe(true);
    expect(await cola.deshacer(venta)).toBe(true);
    expect(borrarOperacion).toHaveBeenCalledWith(venta.id);
    expect(moverStock).toHaveBeenCalledWith(100, 1, 2);  // lo que había bajado, sube otra vez
    expect(cola.operaciones()).toEqual([]);
    expect(toast.toasts().at(-1)!.texto).toContain('el inventario local volvió a como estaba');
  });

  it('una recepción o un ajuste se deshacen con la diferencia contraria y una devolución restaura lo devolvible', async () => {
    const recepcion = await cola.registrar('RECEPCION', {}, 1, 'Recepción', { stock: [{ variante_id: 100, delta: 5 }] });
    await cola.deshacer(recepcion);
    expect(moverStock).toHaveBeenLastCalledWith(100, 1, -5);
    const devolucion = await cola.registrar('DEVOLUCION', {}, 1, 'Devolución', { devuelto: { comprobante: 'CMP-001-000007', items: [{ pedido_item_id: 31, cantidad: 1 }] } });
    await cola.deshacer(devolucion);
    expect(restaurarDevolvible).toHaveBeenCalledWith('CMP-001-000007', [{ pedido_item_id: 31, cantidad: 1 }]);
  });

  it('lo que ya se envió, la atención de reservas y el cobro de una reserva no se deshacen', async () => {
    const enviada = await cola.registrar('VENTA_CONTADO', {}, 1, 'Venta');
    cola.operaciones.update((l) => l.map((o) => (o.id === enviada.id ? { ...o, estado: 'ENVIADA' } : o)));
    expect(await cola.deshacer(enviada)).toBe(false);
    expect(cola.puedeDeshacer(op({ tipo: 'ATENDER_RESERVA' }))).toBe(false);
    expect(cola.puedeDeshacer(op({ tipo: 'PREPARAR_RESERVA' }))).toBe(false);
    expect(cola.puedeDeshacer(op({ payload: { reserva_codigo: 'RSV-1' } }))).toBe(false);
    expect(cola.puedeDeshacer(op({ estado: 'CONFIRMADA' }))).toBe(false);
    expect(borrarOperacion).not.toHaveBeenCalled();
  });
});

describe('Indicador de estado de la barra superior (D5)', () => {
  const online = signal(true);
  const sincronizando = signal(false);
  const pendientes = signal<unknown[]>([]);
  const navegar = vi.fn();
  let rol = 'Cajero';

  beforeEach(() => {
    online.set(true); sincronizando.set(false); pendientes.set([]); navegar.mockClear(); rol = 'Cajero';
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({
      providers: [
        { provide: ConnectivityService, useValue: { online } },
        { provide: ColaOperacionesService, useValue: { pendientes, sincronizando } },
        { provide: AuthService, useValue: { rol: () => rol } },
        { provide: Router, useValue: { navigateByUrl: navegar } },
      ],
    });
  });

  it('muestra en línea, sin conexión o sincronizando, con el número de pendientes', () => {
    const f = TestBed.createComponent(EstadoConexionComponent);
    const texto = () => (f.nativeElement as HTMLElement).textContent!.replace(/\s+/g, ' ').trim();
    f.detectChanges();
    expect(texto()).toBe('En línea');
    online.set(false); pendientes.set([1, 2, 3]); f.detectChanges();
    expect(texto()).toBe('Sin conexión3');
    online.set(true); sincronizando.set(true); f.detectChanges();
    expect(texto()).toBe('Sincronizando…3');
  });

  it('al tocarlo abre el detalle de la cola según el rol', () => {
    const f = TestBed.createComponent(EstadoConexionComponent);
    f.detectChanges();
    (f.nativeElement.querySelector('button') as HTMLButtonElement).click();
    expect(navegar).toHaveBeenLastCalledWith('/pos/offline?pestana=operaciones');
    expect(rutaDeLaCola('Cliente')).toBe('/tienda/offline?pestana=operaciones');
    expect(rutaDeLaCola('Encargado')).toBe('/sucursal/offline?pestana=operaciones');
    expect(rutaDeLaCola('Administrador')).toBe('/empresa/conflictos');
    expect(rutaDeLaCola('Proveedor')).toBe('/proveedor');
    expect(rutaDeLaCola('SuperAdministrador')).toBeNull();
  });
});
