import { signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ComprasApi } from '../../../core/api/compras.api';
import { AuthService } from '../../../core/auth/auth.service';
import { CarritoEstadoService } from '../../../core/carrito/carrito-estado.service';
import { TarjetaGuardada } from '../../../core/compras.models';
import { ConnectivityService } from '../../../core/offline/connectivity.service';
import { LocalDbService } from '../../../core/offline/local-db.service';
import { CheckoutPage, MSG_AUTORIZAR, MSG_TARJETA_NUEVA, tarjetasVigentes } from './checkout.page';

const visa: TarjetaGuardada = { id: 7, marca: 'Visa', ultimos4: '4242', exp_mes: 12, exp_anio: 2099 };
const vencida: TarjetaGuardada = { id: 8, marca: 'Mastercard', ultimos4: '4444', exp_mes: 1, exp_anio: 2020 };
const carrito = { sucursal_id: 1, sucursal: 'Centro', items: [{ id: 1, variante_id: 100, producto: 'Camisa', talla: 'S', color: 'Rojo', cantidad: 2, subtotal: '200.00' }], total_unidades: 2, subtotal: '200.00', descuento: '0.00', iva_incluido: '0.00', total: '200.00', puede_pagar: true, avisos: [] };

describe('Pago con tarjeta guardada sin conexión (D4)', () => {
  const online = signal(false);
  const registrarCompraLocal = vi.fn(async (..._args: unknown[]) => undefined);
  const guardarTarjetasLocal = vi.fn(async (..._args: unknown[]) => undefined);
  const tarjetasApi = vi.fn(() => ({ subscribe: ({ next }: { next: (t: TarjetaGuardada[]) => void }) => next([visa]) }));
  let pagina: CheckoutPage;

  beforeEach(async () => {
    online.set(false); registrarCompraLocal.mockClear(); guardarTarjetasLocal.mockClear(); tarjetasApi.mockClear();
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({
      providers: [
        provideRouter([]),
        { provide: ComprasApi, useValue: { tarjetas: tarjetasApi, carrito: () => ({ subscribe: () => undefined }) } },
        { provide: ConnectivityService, useValue: { online } },
        { provide: AuthService, useValue: { sesion: () => ({ empresa: { id: 1 }, usuario: { id: 5 } }) } },
        { provide: LocalDbService, useValue: { leerTarjetasLocal: async () => [visa, vencida], guardarTarjetasLocal } },
        { provide: CarritoEstadoService, useValue: { vistaSinConexion: async () => carrito, carritoLocal: signal(carrito), cargarLocal: async () => undefined, guardarLocal: async () => undefined, fijar: () => undefined, refrescar: async () => undefined, registrarCompraLocal } },
      ],
    });
    pagina = TestBed.createComponent(CheckoutPage).componentInstance;
    await pagina.ngOnInit();
    TestBed.tick();
    await new Promise((r) => setTimeout(r, 10));
    pagina.form.nit_ci = '1234567';
  });

  it('solo ofrece las tarjetas guardadas que no están vencidas y explica que una tarjeta nueva necesita Internet', () => {
    expect(tarjetasVigentes([visa, vencida], new Date(2026, 10, 10)).map((t) => t.id)).toEqual([7]);
    expect(pagina.tarjetas().map((t) => t.ultimos4)).toEqual(['4242']);
    expect(pagina.msgTarjetaNueva).toBe(MSG_TARJETA_NUEVA);
    expect(MSG_TARJETA_NUEVA).toBe('Para usar una tarjeta nueva necesita Internet. Puede pagar con una tarjeta guardada o dejar la compra por pagar.');
  });

  it('pagar con la tarjeta guardada exige la autorización expresa del cobro y envía solo su identificador', async () => {
    pagina.tarjetaElegida = 7;
    pagina.crearPedido();
    expect(pagina.errorDatos()).toBe(MSG_AUTORIZAR);  // sin «Autorizo el cobro…» no se guarda
    expect(registrarCompraLocal).not.toHaveBeenCalled();
    pagina.autorizo = true;
    pagina.crearPedido();
    await new Promise((r) => setTimeout(r, 10));
    expect(registrarCompraLocal).toHaveBeenCalledOnce();
    const [datos, pago] = registrarCompraLocal.mock.calls[0];
    expect(datos).toMatchObject({ nit_ci: '1234567', tipo_entrega: 'RETIRO' });
    expect(pago).toEqual({ tarjeta_guardada_id: 7, marca: 'Visa', ultimos4: '4242' });  // ni número, ni fecha, ni CVC
    expect(pagina.cobroAutorizado()).toBe('Visa terminada en 4242');
  });

  it('«Dejar por pagar» guarda la compra sin tarjeta', async () => {
    pagina.tarjetaElegida = 0;
    pagina.crearPedido();
    await new Promise((r) => setTimeout(r, 10));
    expect(registrarCompraLocal.mock.calls[0][1]).toBeUndefined();
    expect(pagina.cobroAutorizado()).toBe('');
  });

  it('con conexión se guarda la lista de tarjetas para ofrecerlas después sin red', async () => {
    online.set(true);
    await pagina.ngOnInit();
    expect(tarjetasApi).toHaveBeenCalled();
    expect(guardarTarjetasLocal).toHaveBeenCalledWith('1:5', [visa]);
  });
});
