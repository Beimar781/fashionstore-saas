import { signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap } from '@angular/router';
import { NEVER, of } from 'rxjs';
import { beforeEach, describe, expect, it } from 'vitest';
import { CatalogoApi } from '../../core/api/catalogo.api';
import { ComprasApi } from '../../core/api/compras.api';
import { InventarioApi } from '../../core/api/inventario.api';
import { VestidorApi } from '../../core/api/vestidor.api';
import { CarritoEstadoService } from '../../core/carrito/carrito-estado.service';
import { AprendizajeService } from '../../core/ia/aprendizaje.service';
import { CatalogoLocalService } from '../../core/offline/catalogo-local.service';
import { ColaOperacionesService } from '../../core/offline/cola-operaciones.service';
import { ConnectivityService } from '../../core/offline/connectivity.service';
import { ReservaBorradorService } from '../../core/reservas/reserva-borrador.service';
import { ToastService } from '../../core/ui/toast.service';
import { PrendaPage } from './prenda.page';

const prenda = { id: 1, publico_id: 'p1', nombre: 'Camisa', slug: 'camisa', categoria: 'Camisas', marca: null, genero: 'U', coleccion: '', temporada: '', precio: '100.00', precio_final: '100.00', promocion: null, imagen: null, colores: [], tallas: ['S'], disponible: true, descripcion: '', material: '', cuidado: '', imagenes: [] };
const opciones = {
  producto_id: 1, sucursal_id: null,
  colores: [{ id: 1, nombre: 'Rojo', codigo_hex: '#f00', disponible: true }],
  tallas: [{ id: 1, codigo: 'S', orden: 1, disponible: true }],
  variantes: [{ variante_id: 5, sku: 'CAM-S', talla_id: 1, talla: 'S', color_id: 1, color: 'Rojo', precio: '100.00', precio_final: '100.00', disponible: true, cantidad: 3, orden: 1 }],
};

describe('Ficha de prenda: elegir sucursal', () => {
  const errores: string[] = [];
  const productosLocales = signal<{ id: number }[]>([]);
  const disponibilidad = { subscribe: (o: { error: (e: unknown) => void }) => o.error({ status: 0 }) };

  function montar() {
    errores.length = 0;
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({
      providers: [
        { provide: CatalogoApi, useValue: { sucursales: () => of([]), prenda: () => of(prenda), opciones: () => of(opciones) } },
        { provide: VestidorApi, useValue: { producto: () => NEVER } },
        { provide: InventarioApi, useValue: { disponibilidad: () => disponibilidad } },
        { provide: ComprasApi, useValue: {} },
        { provide: CatalogoLocalService, useValue: { listo: async () => undefined, productos: productosLocales } },
        { provide: ConnectivityService, useValue: { online: signal(false) } },
        { provide: ActivatedRoute, useValue: { paramMap: of(convertToParamMap({ id: '1' })), snapshot: { queryParamMap: convertToParamMap({}) } } },
        { provide: ToastService, useValue: { error: (m: string) => errores.push(m), ok: () => undefined } },
        { provide: AprendizajeService, useValue: { vista: () => undefined } },
        { provide: ReservaBorradorService, useValue: { total: () => 0 } },
        { provide: CarritoEstadoService, useValue: { total: () => 0, sucursalId: () => null } },
        { provide: ColaOperacionesService, useValue: { alRefrescar: () => undefined } },
      ],
    });
    const fixture = TestBed.createComponent(PrendaPage);
    fixture.detectChanges();
    return fixture;
  }

  beforeEach(() => productosLocales.set([]));

  it('sin sucursal elegida muestra el texto junto al botón, que desaparece al elegirla', async () => {
    const fixture = montar();
    expect(fixture.nativeElement.textContent).toContain('Elija una sucursal para agregar al carrito.');
    fixture.componentInstance.sucursalId.set(2);
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).not.toContain('Elija una sucursal para agregar al carrito.');
  });

  it('sin conexión y con copia local no avisa; sin copia dice que no hay stock guardado', async () => {
    productosLocales.set([{ id: 1 }]);
    const conCopia = montar();
    await conCopia.whenStable();
    expect(errores).toEqual([]);
    productosLocales.set([]);
    const sinCopia = montar();
    await sinCopia.whenStable();
    expect(errores).toContain('Sin conexión: no hay stock guardado para esta sucursal.');
  });
});
