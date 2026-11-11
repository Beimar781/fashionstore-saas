import { Component, signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { AuthService } from '../auth/auth.service';
import { NecesitaInternetDirective } from '../ui/necesita-internet.directive';
import { ToastService } from '../ui/toast.service';
import { CatalogoLocalService } from './catalogo-local.service';
import { ColaOperacionesService } from './cola-operaciones.service';
import { ConnectivityService } from './connectivity.service';
import { OperacionesSucursalService } from './operaciones-sucursal.service';
import { UltimaConsultaService } from './ultima-consulta.service';

describe('Tareas de la sucursal sin conexión (D3)', () => {
  const registrar = vi.fn(async (..._args: unknown[]) => ({}));
  const moverStock = vi.fn(async () => undefined);
  const actualizarExtras = vi.fn(async () => undefined);
  let tareas: OperacionesSucursalService;

  beforeEach(() => {
    registrar.mockClear(); moverStock.mockClear(); actualizarExtras.mockClear();
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({
      providers: [
        { provide: AuthService, useValue: { sesion: () => ({ usuario: { sucursal_id: 1 } }) } },
        { provide: ColaOperacionesService, useValue: { registrar } },
        { provide: CatalogoLocalService, useValue: { moverStock, actualizarExtras } },
      ],
    });
    tareas = TestBed.inject(OperacionesSucursalService);
  });

  it('la recepción y el ajuste quedan en la cola y cambian el stock local al instante', async () => {
    await tareas.recibir(100, 5, ' Envío 7 ', 'Camisa (S, Rojo)');
    expect(registrar).toHaveBeenLastCalledWith('RECEPCION', { variante_id: 100, cantidad: 5, referencia: 'Envío 7' }, 1, 'Recepción de 5× Camisa (S, Rojo)');
    expect(moverStock).toHaveBeenLastCalledWith(100, 1, 5);
    await tareas.ajustar(100, -2, 'MERMA', ' una menos ', 'Camisa (S, Rojo)');
    expect(registrar).toHaveBeenLastCalledWith('AJUSTE_INVENTARIO', { variante_id: 100, diferencia: -2, motivo: 'MERMA', nota: 'una menos' }, 1, 'Ajuste de -2× Camisa (S, Rojo) (MERMA)');
    expect(moverStock).toHaveBeenLastCalledWith(100, 1, -2);
  });

  it('preparar, marcar «no encontrada» y atender actualizan la copia de la reserva', async () => {
    const reservas = [{ id: 7, codigo: 'RSV-7', estado: 'PENDIENTE', programada_para: '', items: [{ id: 1, estado: 'RESERVADO' }] }, { id: 8, codigo: 'RSV-8', estado: 'PENDIENTE', programada_para: '', items: [] }];
    const r = reservas[0] as never;
    await tareas.preparar(r);
    await tareas.noEncontrada(r, 1);
    await tareas.atender(r, true);
    expect(registrar.mock.calls.map((c) => c[0])).toEqual(['PREPARAR_RESERVA', 'PRENDA_NO_ENCONTRADA', 'ATENDER_RESERVA']);
    expect(registrar.mock.calls[2][1]).toEqual({ reserva_id: 7, llevara_prendas: true });
    for (const cambio of actualizarExtras.mock.calls as unknown as [(m: { reservas_sucursal: typeof reservas }) => void][]) cambio[0]({ reservas_sucursal: reservas });
    expect(reservas[0].estado).toBe('EN_PROBADOR');  // lleva las prendas: se cobra en Caja
    expect(reservas[0].items[0].estado).toBe('NO_ENCONTRADO');
    await tareas.atender(reservas[1] as never, false);
    const quitar = (actualizarExtras.mock.calls.at(-1) as unknown as [(m: { reservas_sucursal: typeof reservas }) => void])[0];
    const copia = { reservas_sucursal: [...reservas] };
    quitar(copia);
    expect(copia.reservas_sucursal.map((x) => x.id)).toEqual([7]);  // la que no lleva nada sale de la copia
  });
});

@Component({ selector: 'app-prueba', imports: [NecesitaInternetDirective], template: `<button necesitaInternet="Exportar necesita Internet." (click)="veces = veces + 1">Exportar</button>` })
class PruebaComponent { veces = 0; }

describe('Botones que necesitan Internet (D3)', () => {
  const online = signal(true);
  let toast: ToastService;

  beforeEach(() => {
    online.set(true);
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({ providers: [{ provide: ConnectivityService, useValue: { online } }] });
    toast = TestBed.inject(ToastService);
  });

  it('con red el botón funciona; sin red se apaga, explica el motivo y no ejecuta la acción', () => {
    const fixture = TestBed.createComponent(PruebaComponent);
    fixture.detectChanges();
    const boton = fixture.nativeElement.querySelector('button') as HTMLButtonElement;
    boton.click();
    expect(fixture.componentInstance.veces).toBe(1);
    online.set(false);
    fixture.detectChanges();
    expect(boton.classList.contains('sin-internet')).toBe(true);
    expect(boton.title).toBe('Exportar necesita Internet.');
    boton.click();
    expect(fixture.componentInstance.veces).toBe(1);  // la acción no se ejecutó
    expect(toast.toasts().at(-1)!.texto).toBe('Exportar necesita Internet.');
    online.set(true);
    fixture.detectChanges();
    boton.click();
    expect(fixture.componentInstance.veces).toBe(2);
  });
});

describe('Datos al… (D3)', () => {
  it('recuerda cuándo llegaron datos del servidor y lo olvida al cerrar sesión', () => {
    localStorage.clear();
    TestBed.resetTestingModule();
    const ultima = TestBed.inject(UltimaConsultaService);
    expect(ultima.momento()).toBeNull();
    ultima.registrar();
    expect(ultima.momento()).not.toBeNull();
    expect(new UltimaConsultaService().momento()).toBe(ultima.momento());  // sobrevive a recargar la página
    ultima.olvidar();
    expect(ultima.momento()).toBeNull();
    expect(new UltimaConsultaService().momento()).toBeNull();
  });
});
