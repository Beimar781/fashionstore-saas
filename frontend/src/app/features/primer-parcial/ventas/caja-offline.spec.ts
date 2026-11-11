import { signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { CajaApi } from '../../../core/api/caja.api';
import { AuthService } from '../../../core/auth/auth.service';
import { CatalogoLocalService } from '../../../core/offline/catalogo-local.service';
import { ColaOperacionesService } from '../../../core/offline/cola-operaciones.service';
import { ConnectivityService } from '../../../core/offline/connectivity.service';
import { CajaPage } from './caja.page';

const variante = { id: 100, sku: 'CAM-S-ROJ', codigo_barras: '7770001', talla: 'S', color: 'Rojo', precio: '100.00', precio_final: '90.00', promocion: 'Oferta', stock: { '1': 3 } };
const producto = { id: 10, nombre: 'Camisa Oxford', imagen: null, variantes: [variante] };
const prenda = { producto, variante };
const reservas = [
  { id: 7, codigo: 'RSV-LISTA', cliente: 'Ana Pérez', estado: 'PREPARADA', programada_para: '2026-11-12T11:00:00Z', items: [{ id: 1, variante_id: 100, producto: 'Camisa Oxford', talla: 'S', color: 'Rojo', cantidad: 2, estado: 'RESERVADO' }] },
  { id: 8, codigo: 'RSV-PEND', cliente: 'Luis', estado: 'PENDIENTE', programada_para: '2026-11-12T11:00:00Z', items: [] },
];

describe('Caja sin conexión (D2)', () => {
  const online = signal(false);
  const registrar = vi.fn();
  const comprometer = vi.fn();
  const actualizarExtras = vi.fn();
  let caja: CajaPage;

  beforeEach(() => {
    online.set(false);
    registrar.mockReset(); comprometer.mockReset(); actualizarExtras.mockReset();
    registrar.mockImplementation(async (tipo: string, payload: unknown, sucursal: number, resumen: string) => ({ id: 'abc123de-0000-4000-8000-000000000000', tipo, payload, sucursal_id: sucursal, resumen, creada_en: '2026-11-10T10:00:00Z', estado: 'REGISTRADA_LOCAL' }));
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({
      providers: [
        { provide: CajaApi, useValue: {} },  // sin red no se llama a la API
        { provide: ConnectivityService, useValue: { online } },
        { provide: AuthService, useValue: { sesion: () => ({ usuario: { id: 7, rol: 'Cajero', sucursal_id: 1 }, empresa: { id: 1, razon_social: 'Moda' } }), rol: () => 'Cajero', autenticado: () => true } },
        { provide: ColaOperacionesService, useValue: { operaciones: signal([]), pendientes: signal([]), alRefrescar: () => undefined, registrar } },
        { provide: CatalogoLocalService, useValue: { hayCatalogo: () => true, productos: signal([producto]), meta: signal({ reservas_sucursal: reservas }), buscar: () => [prenda], actualizarExtras, stock: (v: typeof variante, s: number) => v.stock[String(s) as '1'] ?? 0, comprometer } },
      ],
    });
    caja = TestBed.createComponent(CajaPage).componentInstance;
  });

  it('busca y escanea en la copia local, con el stock de la sucursal y el precio con promoción', () => {
    caja.consulta = 'camisa'; caja.buscar();
    expect(caja.resultados()).toHaveLength(1);
    expect(caja.resultados()[0]).toMatchObject({ variante_id: 100, producto: 'Camisa Oxford', precio_final: '90.00', disponible: 3 });
    caja.codigo = '7770001'; caja.escanear();
    expect(caja.lineas()).toHaveLength(1);
    caja.codigo = 'NO-EXISTE'; caja.escanear();
    expect(caja.errorBusqueda()).toContain('no coincide con ninguna prenda de la copia');
  });

  it('registra la venta de contado en la cola, baja el stock local y entrega el comprobante provisional LOC-…', async () => {
    caja.consulta = 'camisa'; caja.buscar();
    caja.agregar(caja.resultados()[0]);
    caja.cantidad(caja.lineas()[0], '2');
    caja.registrar();
    const venta = caja.venta()!;
    expect(venta.id).toBe(0);
    expect(caja.esLocal(venta)).toBe(true);
    expect(venta.total).toBe('180.00');

    caja.recibido = 100;
    await caja.cobrarCaja('EFECTIVO');
    expect(caja.errorCobro()).toBe('El efectivo recibido es menor al total de la venta.');  // no se registra nada
    expect(registrar).not.toHaveBeenCalled();

    caja.recibido = 200;
    await caja.cobrarCaja('EFECTIVO');
    await Promise.resolve();
    expect(registrar).toHaveBeenCalledOnce();
    const [tipo, payload, sucursal] = registrar.mock.calls[0];
    expect([tipo, sucursal]).toEqual(['VENTA_CONTADO', 1]);
    expect(payload).toMatchObject({ forma_pago: 'EFECTIVO', monto_recibido: '200.00', items: [{ variante_id: 100, cantidad: 2, precio_unitario: '90.00' }] });
    expect(comprometer).toHaveBeenCalledWith([{ variante_id: 100, cantidad: 2, precio_unitario: '90.00' }], 1);
    const cobro = caja.cobro()!;
    expect(cobro.pedido.comprobante_numero).toBe('LOC-001-ABC123');
    expect(cobro.pedido.comprobante_tipo).toBe('PROVISIONAL');
    expect(cobro.cambio).toBe('20.00');
  });

  it('cobra una reserva preparada con la copia local: lleva su código y no baja otra vez el stock apartado', async () => {
    caja.codigoReserva = 'rsv-lista'; caja.cargarReserva();
    expect(caja.errorReserva()).toBe('');
    expect(caja.reserva()?.cliente).toBe('Ana Pérez');
    caja.registrar();
    const venta = caja.venta()!;
    expect(venta.total).toBe('180.00');  // 2 × Bs 90 con el precio de la copia
    expect(venta.reserva_id).toBe(7);
    caja.recibido = 200;
    await caja.cobrarCaja('EFECTIVO');
    const [tipo, payload] = registrar.mock.calls[0];
    expect(tipo).toBe('VENTA_CONTADO');
    expect(payload).toMatchObject({ reserva_codigo: 'RSV-LISTA', monto_recibido: '200.00', items: [{ variante_id: 100, cantidad: 2 }] });
    expect(payload).not.toHaveProperty('cliente_email');
    expect(comprometer).not.toHaveBeenCalled();  // el stock de la reserva ya estaba apartado
    expect(actualizarExtras).toHaveBeenCalledOnce();  // la reserva sale de la copia local
  });

  it('una reserva sin preparar o desconocida no se puede cobrar sin conexión', () => {
    for (const codigo of ['RSV-PEND', 'RSV-NO-EXISTE']) {
      caja.codigoReserva = codigo; caja.cargarReserva();
      expect(caja.errorReserva()).toContain('no está lista para cobrar');
      expect(caja.reserva()).toBeNull();
    }
  });
});
