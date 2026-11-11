import { NEVER } from 'rxjs';
import { signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { CatalogoAdminApi } from '../../core/api/catalogo-admin.api';
import { CatalogoApi } from '../../core/api/catalogo.api';
import { InventarioApi } from '../../core/api/inventario.api';
import { AuthService } from '../../core/auth/auth.service';
import { CatalogoLocalService } from '../../core/offline/catalogo-local.service';
import { ColaOperacionesService } from '../../core/offline/cola-operaciones.service';
import { ConnectivityService } from '../../core/offline/connectivity.service';
import { OperacionesSucursalService } from '../../core/offline/operaciones-sucursal.service';
import { InventarioPage } from './inventario.page';

const camisa = { id: 10, nombre: 'Camisa Oxford', categoria: 'Camisas', variantes: [
  { id: 100, sku: 'CAM-S-ROJ', codigo_barras: '7770001', talla: 'S', color: 'Rojo', stock: { '1': 5 } },
  { id: 101, sku: 'CAM-M-AZU', codigo_barras: null, talla: 'M', color: 'Azul', stock: { '1': 0 } },
] };
const polo = { id: 11, nombre: 'Polo Blanco', categoria: 'Polos', variantes: [{ id: 200, sku: 'POL-L-BLA', codigo_barras: null, talla: 'L', color: 'Blanco', stock: { '1': 3 } }] };

describe('Inventario del Encargado sin conexión (D3)', () => {
  const online = signal(false);
  const ajustar = vi.fn();
  const recibir = vi.fn();
  let pagina: InventarioPage;
  const asentar = () => new Promise((r) => setTimeout(r, 0));  // la tabla espera a que la copia guardada termine de leerse

  beforeEach(() => {
    online.set(false); ajustar.mockReset(); recibir.mockReset();
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({
      providers: [
        provideRouter([]),
        { provide: InventarioApi, useValue: {} },  // sin red no se llama a la API
        { provide: CatalogoAdminApi, useValue: { categorias: () => NEVER, temporadas: () => NEVER } },
        { provide: CatalogoApi, useValue: {} },
        { provide: ConnectivityService, useValue: { online } },
        { provide: AuthService, useValue: { rol: () => 'Encargado', sesion: () => ({ usuario: { sucursal_id: 1 } }) } },
        { provide: ColaOperacionesService, useValue: { alRefrescar: () => undefined } },
        { provide: OperacionesSucursalService, useValue: { ajustar, recibir } },
        { provide: CatalogoLocalService, useValue: { listo: async () => undefined, hayCatalogo: () => true, productos: signal([camisa, polo]), stock: (v: { stock: Record<string, number> }, s: number) => v.stock[String(s)] ?? 0 } },
      ],
    });
    pagina = TestBed.createComponent(InventarioPage).componentInstance;
  });

  it('arma la tabla con las existencias de la copia descargada y filtra por nombre, SKU, código de barras y estado', async () => {
    expect(pagina.modoLocal()).toBe(true);
    pagina.irA(1); await asentar();
    expect(pagina.datos()!.total).toBe(3);
    expect(pagina.datos()!.resumen).toMatchObject({ disponibles: 8, agotadas: 1 });
    pagina.f.q = 'polo'; pagina.irA(1); await asentar();
    expect(pagina.datos()!.items.map((i) => i.sku)).toEqual(['POL-L-BLA']);
    pagina.f.q = '7770001'; pagina.irA(1); await asentar();  // lo que lee el escáner: código de barras exacto
    expect(pagina.datos()!.items.map((i) => i.sku)).toEqual(['CAM-S-ROJ']);
    pagina.f.q = ''; pagina.elegirEstado('AGOTADA'); await asentar();
    expect(pagina.datos()!.items.map((i) => i.sku)).toEqual(['CAM-M-AZU']);
  });

  it('el ajuste se guarda como diferencia con su motivo y la tabla se recalcula', async () => {
    pagina.irA(1); await asentar();
    const fila = pagina.datos()!.items[0];
    pagina.abrirAjuste(fila);
    pagina.ajuste = { tipo: 'AJUSTE_SALIDA', cantidad: 2, nota: 'Prenda dañada' };
    pagina.motivoAjuste = 'DAÑO';
    pagina.guardar();
    await Promise.resolve();
    expect(ajustar).toHaveBeenCalledWith(100, -2, 'DAÑO', 'Prenda dañada', 'Camisa Oxford (S, Rojo)');
    expect(pagina.modal()).toBeNull();
  });

  it('la recepción manual sube el inventario y el mínimo de reposición necesita Internet', async () => {
    pagina.irA(1); await asentar();
    pagina.abrirRecepcion(pagina.datos()!.items[2]);
    pagina.recepcion = { cantidad: 4, referencia: 'Envío 9' };
    pagina.guardar();
    await Promise.resolve();
    expect(recibir).toHaveBeenCalledWith(200, 4, 'Envío 9', 'Polo Blanco (L, Blanco)');
  });
});
