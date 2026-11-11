import { signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { beforeEach, describe, expect, it } from 'vitest';
import { ComprasApi } from '../../../core/api/compras.api';
import { AuthService } from '../../../core/auth/auth.service';
import { CarritoEstadoService } from '../../../core/carrito/carrito-estado.service';
import { ConnectivityService } from '../../../core/offline/connectivity.service';
import { LocalDbService } from '../../../core/offline/local-db.service';
import { CheckoutPage } from './checkout.page';

const espejo = { sucursal_id: 1, sucursal: 'Centro', items: [{ id: 1, variante_id: 100, producto: 'Camisa', talla: 'S', color: 'Rojo', cantidad: 1, subtotal: '100.00' }], total_unidades: 1, subtotal: '100.00', descuento: '0.00', iva_incluido: '0.00', total: '100.00', puede_pagar: true, avisos: [] };

describe('Checkout abierto sin conexión (E1)', () => {
  const online = signal(false);
  let hayEspejo = false;

  const crear = async () => {
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({
      providers: [
        provideRouter([]),
        { provide: ComprasApi, useValue: { tarjetas: () => ({ subscribe: () => undefined }), carrito: () => ({ subscribe: ({ next }: { next: (c: unknown) => void }) => next(espejo) }) } },
        { provide: ConnectivityService, useValue: { online } },
        { provide: AuthService, useValue: { sesion: () => ({ empresa: { id: 1 }, usuario: { id: 5 } }) } },
        { provide: LocalDbService, useValue: { leerTarjetasLocal: async () => [], guardarTarjetasLocal: async () => undefined } },
        { provide: CarritoEstadoService, useValue: { carritoLocal: signal(null), cargarLocal: async () => undefined, vistaSinConexion: async () => (hayEspejo ? espejo : null), fijar: () => undefined, refrescar: async () => undefined } },
      ],
    });
    const f = TestBed.createComponent(CheckoutPage);
    await f.componentInstance.ngOnInit();
    f.detectChanges();
    return f;
  };

  beforeEach(() => { online.set(false); hayEspejo = false; });

  it('sin carrito guardado explica qué hacer en vez de quedar en «Cargando…»', async () => {
    const f = await crear();
    const texto = (f.nativeElement as HTMLElement).textContent!;
    expect(texto).toContain('Su carrito no está guardado en este dispositivo. Ábralo con conexión una vez.');
    expect(texto).not.toContain('Cargando…');
  });

  it('con la copia del carrito del servidor lo muestra sin red y, al volver la red, se recarga solo', async () => {
    hayEspejo = true;
    const f = await crear();
    expect(f.componentInstance.carrito()?.total).toBe('100.00');
    expect(f.componentInstance.sinCarrito()).toBe(false);
    online.set(true);
    TestBed.tick();
    await new Promise((r) => setTimeout(r, 20));
    expect(f.componentInstance.carrito()?.total).toBe('100.00');  // lo volvió a pedir al servidor
  });
});
