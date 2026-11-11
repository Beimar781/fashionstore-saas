import { signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { of, throwError } from 'rxjs';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { rutaMedia } from '../api.config';
import { ComprasApi } from '../api/compras.api';
import { AuthService } from '../auth/auth.service';
import { Carrito, ItemCarrito } from '../compras.models';
import { CatalogoLocalService } from '../offline/catalogo-local.service';
import { ColaOperacionesService } from '../offline/cola-operaciones.service';
import { ConnectivityService } from '../offline/connectivity.service';
import { LocalDbService } from '../offline/local-db.service';
import { ToastService } from '../ui/toast.service';
import { CarritoEstadoService } from './carrito-estado.service';

const item = (id: number, variante: number, cantidad: number): ItemCarrito => ({ id, variante_id: variante, producto_id: 1, sku: `S${variante}`, producto: 'Camisa', talla: 'S', color: 'Rojo', imagen: null, cantidad, precio: '100.00', precio_final: '100.00', subtotal: (100 * cantidad).toFixed(2), disponible: 5, estado: 'OK' });
const servidor = (): Carrito => ({ sucursal_id: 1, sucursal: 'Centro', items: [item(11, 100, 2), item(12, 200, 1)], total_unidades: 3, subtotal: '300.00', descuento: '0.00', iva_incluido: '0.00', total: '300.00', puede_pagar: true, avisos: [] });

describe('Carrito sin conexión (E2)', () => {
  const guardado = new Map<string, unknown>();
  const llamadas: string[] = [];
  let estado: CarritoEstadoService;
  let falla = false;

  beforeEach(async () => {
    guardado.clear(); llamadas.length = 0; falla = false;
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({ providers: [
      { provide: ComprasApi, useValue: {
        carrito: () => of(servidor()),
        cambiarCantidad: (id: number, c: number) => { llamadas.push(`cantidad ${id}=${c}`); return falla ? throwError(() => ({ status: 0 })) : of(servidor()); },
        quitar: (id: number) => { llamadas.push(`quitar ${id}`); return of(servidor()); },
        vaciar: () => { llamadas.push('vaciar'); return of(servidor()); },
      } },
      { provide: AuthService, useValue: { rol: () => 'Administrador', sesion: () => ({ empresa: { id: 1 }, usuario: { id: 5 } }) } },
      { provide: LocalDbService, useValue: {
        guardarCarritoLocal: async (k: string, v: unknown) => { guardado.set(k, v); }, leerCarritoLocal: async (k: string) => guardado.get(k), borrarCarritoLocal: async (k: string) => { guardado.delete(k); } } },
      { provide: CatalogoLocalService, useValue: { meta: () => null } }, { provide: ColaOperacionesService, useValue: {} }, { provide: ToastService, useValue: { error: vi.fn() } },
      { provide: ConnectivityService, useValue: { online: signal(false) } },
    ] });
    estado = TestBed.inject(CarritoEstadoService);
    guardado.set('espejo:1:5', servidor());  // lo último que mostró el servidor
  });

  it('cambiar la cantidad y quitar sin red se ven enseguida en la vista y no tocan el servidor', async () => {
    const [a, b] = servidor().items;
    await estado.cambiarCantidadSinConexion(a, 4);
    await estado.quitarSinConexion(b);
    const vista = await estado.vistaSinConexion();
    expect(vista!.items.map((i) => [i.id, i.cantidad])).toEqual([[11, 4]]);
    expect(vista!.total).toBe('400.00');
    expect(vista!.iva_incluido).toBe('46.02');  // F · el IVA incluido sin conexión ya no es 0,00: 400 × 13 ÷ 113
    expect(llamadas).toEqual([]);
  });

  it('no deja pasar de las unidades disponibles ni de 10', async () => {
    const [a] = servidor().items;
    await expect(estado.cambiarCantidadSinConexion(a, 6)).rejects.toThrow('No hay más unidades disponibles');
    await expect(estado.cambiarCantidadSinConexion(a, 0)).rejects.toThrow('entre 1 y 10');
  });

  it('al volver la red se repiten los cambios en orden sobre el carrito del servidor y quedan limpios', async () => {
    const [a, b] = servidor().items;
    await estado.cambiarCantidadSinConexion(a, 3);
    await estado.quitarSinConexion(b);
    await estado.refrescar();
    expect(llamadas).toEqual(['cantidad 11=3', 'quitar 12']);
    expect(estado.ediciones()).toEqual([]);
    expect(guardado.has('ediciones:1:5')).toBe(false);
  });

  it('si la red se cae a mitad del reenvío, lo que falta espera para la próxima vez', async () => {
    const [a, b] = servidor().items;
    await estado.cambiarCantidadSinConexion(a, 3);
    await estado.quitarSinConexion(b);
    falla = true;
    await estado.refrescar();
    expect(estado.ediciones().length).toBe(2);
    expect(guardado.has('ediciones:1:5')).toBe(true);
  });

  it('vaciar sin red deja la vista vacía; una compra sin conexión limpia la copia y los cambios pendientes', async () => {
    await estado.vaciarSinConexion();
    expect((await estado.vistaSinConexion())!.items).toEqual([]);
    await estado.cambiarCantidadSinConexion(item(11, 100, 2), 1).catch(() => undefined);
    guardado.set('espejo:1:5', servidor());
    TestBed.inject(ColaOperacionesService).registrar = vi.fn(async () => ({}) as never);
    await estado.registrarCompraLocal({ tipo_entrega: 'RETIRO', direccion_entrega: '', nit_ci: '123', razon_social: '' }, undefined, servidor());
    expect(guardado.has('espejo:1:5')).toBe(false);
    expect(estado.ediciones()).toEqual([]);
  });
});

describe('Rutas de imagen (E2)', () => {
  it('el catálogo descargado trae la ruta de la base y se deja como /media/…, igual que la API en línea', () => {
    expect(rutaMedia('2/productos/5/abc.jpg')).toBe('/media/2/productos/5/abc.jpg');
    expect(rutaMedia('/media/2/productos/5/abc.jpg')).toBe('/media/2/productos/5/abc.jpg');
    expect(rutaMedia('https://cdn.ejemplo.com/a.jpg')).toBe('https://cdn.ejemplo.com/a.jpg');
    expect(rutaMedia(null)).toBeNull();
  });
});
