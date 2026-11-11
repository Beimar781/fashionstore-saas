import { signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { beforeEach, describe, expect, it } from 'vitest';
import { AuthService } from '../auth/auth.service';
import { ToastService } from '../ui/toast.service';
import { devolucionDeEfectivo, motivoParaCliente, MSG_AGOTADA } from '../../features/offline/operaciones-con-problema.component';
import { AvisosConexionService, MSG_SIN_RED } from './avisos-conexion.service';
import { ColaOperacionesService, ResumenSync } from './cola-operaciones.service';
import { ConnectivityService } from './connectivity.service';

describe('Avisos globales de conexión (D1)', () => {
  const online = signal(true);
  const pendientes = signal<unknown[]>([]);
  const ultimoResumen = signal<ResumenSync | null>(null);
  let toast: ToastService;

  beforeEach(() => {
    online.set(true); pendientes.set([]); ultimoResumen.set(null);
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({
      providers: [
        { provide: ConnectivityService, useValue: { online } },
        { provide: ColaOperacionesService, useValue: { pendientes, ultimoResumen } },
        { provide: AuthService, useValue: { autenticado: () => true, rol: () => 'Cajero' } },
      ],
    });
    toast = TestBed.inject(ToastService);
    TestBed.inject(AvisosConexionService);
    TestBed.tick();
  });

  const textos = () => toast.toasts().map((t) => t.texto);

  it('al arrancar con red no avisa nada', () => {
    expect(textos()).toEqual([]);
  });

  it('al perder la red avisa que las acciones se guardan en el dispositivo', () => {
    online.set(false); TestBed.tick();
    expect(textos()).toEqual([MSG_SIN_RED]);
  });

  it('al volver la red anuncia cuántas operaciones sincroniza y luego el resumen con «Ver detalle»', () => {
    online.set(false); TestBed.tick();
    pendientes.set([1, 2, 3]);
    online.set(true); TestBed.tick();
    expect(textos().at(-1)).toBe('Conexión restablecida. Sincronizando 3 operaciones…');
    ultimoResumen.set({ confirmadas: 1, conflictos: 1, rechazadas: 1 }); TestBed.tick();
    const resumen = toast.toasts().at(-1)!;
    expect(resumen.texto).toBe('Sincronización completa: 1 confirmadas, 1 en conflicto, 1 rechazadas');
    expect(resumen.accion).toEqual({ texto: 'Ver detalle', ruta: '/pos/offline' });
    expect(resumen.tipo).toBe('warn');
  });

  it('si vuelve la red sin nada pendiente solo dice «Conexión restablecida.»', () => {
    online.set(false); TestBed.tick();
    online.set(true); TestBed.tick();
    expect(textos().at(-1)).toBe('Conexión restablecida.');
  });

  it('una sola operación confirmada con red (sin reconexión) no repite el resumen global', () => {
    ultimoResumen.set({ confirmadas: 1, conflictos: 0, rechazadas: 0 }); TestBed.tick();
    expect(textos()).toEqual([]);
  });

  it('sin reconexión, si algo quedó en conflicto o se enviaron varias operaciones juntas, el resumen sí se anuncia', () => {
    ultimoResumen.set({ confirmadas: 0, conflictos: 1, rechazadas: 0 }); TestBed.tick();
    expect(textos()).toEqual(['Sincronización completa: 0 confirmadas, 1 en conflicto, 0 rechazadas']);
    ultimoResumen.set({ confirmadas: 2, conflictos: 0, rechazadas: 0 }); TestBed.tick();
    expect(textos().at(-1)).toBe('Sincronización completa: 2 confirmadas, 0 en conflicto, 0 rechazadas');
  });
});

describe('Conflictos visibles para quien los sufre (D1)', () => {
  it('el cliente lee que la prenda se agotó y que no se le cobró nada', () => {
    expect(motivoParaCliente({ estado: 'EN_CONFLICTO', mensaje: 'Stock insuficiente' })).toBe(MSG_AGOTADA);
  });

  it('si hubo devolución de dinero se muestra el mensaje del servidor', () => {
    const mensaje = 'Descartada por el Encargado. Se devolvieron Bs 100,00 en efectivo al cliente (nota ND-1).';
    expect(motivoParaCliente({ estado: 'RECHAZADA', mensaje })).toBe(mensaje);
  });

  it('el cajero ve el estado de la devolución del efectivo', () => {
    expect(devolucionDeEfectivo({ estado: 'EN_CONFLICTO', mensaje: '' })).toContain('Pendiente');
    expect(devolucionDeEfectivo({ estado: 'RECHAZADA', mensaje: 'Se devolvieron Bs 100 en efectivo al cliente (nota ND-1).' })).toBe('Efectivo devuelto al cliente.');
    expect(devolucionDeEfectivo({ estado: 'RECHAZADA', mensaje: 'Descartada.' })).toBe('Sin devolución registrada.');
  });
});
