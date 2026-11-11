import { TestBed } from '@angular/core/testing';
import { signal } from '@angular/core';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { CatalogoAdminApi } from '../../../core/api/catalogo-admin.api';
import { ProveedoresApi } from '../../../core/api/proveedores.api';
import { AuthService } from '../../../core/auth/auth.service';
import { ColaOperacionesService } from '../../../core/offline/cola-operaciones.service';
import { ConnectivityService } from '../../../core/offline/connectivity.service';
import { AbastecimientoPage } from './abastecimiento.page';

describe('Proponer producto del Proveedor con y sin conexión (D3)', () => {
  const online = signal(false);
  const registrar = vi.fn(async (..._args: unknown[]) => ({}));
  const crearPropuesta = vi.fn(() => ({ subscribe: ({ next }: { next: () => void }) => next() }));
  let pagina: AbastecimientoPage;

  beforeEach(() => {
    online.set(false); registrar.mockClear(); crearPropuesta.mockClear();
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({
      providers: [
        { provide: ProveedoresApi, useValue: { crearPropuesta, propuestas: () => ({ subscribe: () => undefined }), lotes: () => ({ subscribe: () => undefined }) } },
        { provide: CatalogoAdminApi, useValue: {} },
        { provide: AuthService, useValue: { rol: () => 'Proveedor', sesion: () => ({ usuario: { id: 9 } }) } },
        { provide: ConnectivityService, useValue: { online } },
        { provide: ColaOperacionesService, useValue: { registrar, alRefrescar: () => undefined } },
      ],
    });
    pagina = TestBed.createComponent(AbastecimientoPage).componentInstance;
    pagina.abrirPropuesta();
    Object.assign(pagina.propuesta, { nombre: 'Chompa de lana', descripcion: 'Abrigada', coleccion_id: 3, genero: 'UNISEX', precio_base: 180, material: 'Lana' });
  });

  it('sin conexión la propuesta queda en la cola con el precio como texto, sin llamar al servidor', async () => {
    await pagina.enviarPropuesta();
    expect(crearPropuesta).not.toHaveBeenCalled();
    expect(registrar).toHaveBeenCalledOnce();
    const [tipo, payload, sucursal, resumen] = registrar.mock.calls[0];
    expect([tipo, sucursal, resumen]).toEqual(['PROPUESTA_PROVEEDOR', null, 'Propuesta de producto: Chompa de lana']);
    expect(payload).toMatchObject({ nombre: 'Chompa de lana', coleccion_id: 3, precio_base: '180' });
    expect(pagina.modalPropuesta()).toBe(false);
  });

  it('con conexión se envía directo al servidor y no pasa por la cola', async () => {
    online.set(true);
    await pagina.enviarPropuesta();
    expect(crearPropuesta).toHaveBeenCalledOnce();
    expect(registrar).not.toHaveBeenCalled();
  });
});

