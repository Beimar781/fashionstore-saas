import { signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { of } from 'rxjs';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { OfflineApi } from '../api/offline.api';
import { VestidorApi } from '../api/vestidor.api';
import { AuthService } from '../auth/auth.service';
import { CatalogoLocalService } from './catalogo-local.service';
import { ConnectivityService } from './connectivity.service';
import { LocalDbService } from './local-db.service';

const catalogo = { generado_en: '2026-11-10T10:00:00Z', empresa_id: 1, sucursales: [], clientes: [], productos: [{ id: 1, nombre: 'Camisa', categoria: 'Camisas', variantes: [] }] };

describe('Descarga automática del catálogo (D2)', () => {
  const online = signal(true);
  const autenticado = signal(true);
  const rol = signal('Cajero');
  const descargar = vi.fn();
  let guardado: unknown[] = [];
  let meta: { generado_en: string; empresa_id: number; sucursales: unknown[]; clientes: unknown[] } | undefined;

  async function arrancar(copiaPrevia: unknown[] = [], minutosDeAntiguedad?: number) {
    guardado = copiaPrevia;
    meta = minutosDeAntiguedad === undefined ? undefined : { generado_en: new Date(Date.now() - minutosDeAntiguedad * 60000).toISOString(), empresa_id: 1, sucursales: [], clientes: [] };
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({
      providers: [
        { provide: OfflineApi, useValue: { catalogo: () => { descargar(); return of(catalogo); } } },
        { provide: VestidorApi, useValue: {} },
        { provide: ConnectivityService, useValue: { online } },
        { provide: AuthService, useValue: { autenticado, sesion: () => ({ usuario: { rol: rol() }, suscripcion: { plan: { offline: true } } }), rol: () => rol() } },
        { provide: LocalDbService, useValue: { leerCatalogo: async () => guardado, metaCatalogo: async () => meta, guardarCatalogo: async (p: unknown[]) => { guardado = p; }, marcarSincronizacion: async () => undefined } },
      ],
    });
    TestBed.inject(CatalogoLocalService);
    TestBed.tick();
    await new Promise((r) => setTimeout(r, 20));
    TestBed.tick();
  }

  beforeEach(() => { online.set(true); autenticado.set(true); rol.set('Cajero'); descargar.mockReset(); });

  it('sin copia y con red, el cajero descarga el catálogo solo, sin ir a otra pantalla', async () => {
    await arrancar();
    expect(descargar).toHaveBeenCalledTimes(1);
  });

  it('si ya hay copia no vuelve a descargarla (solo se actualiza cuando vence)', async () => {
    await arrancar([{ id: 1 }]);
    expect(descargar).not.toHaveBeenCalled();
  });

  it('F · al iniciar sesión renueva la copia si tiene más de 15 minutos (no vende con existencias viejas), y si es reciente no', async () => {
    await arrancar([{ id: 1 }], 40);
    expect(descargar).toHaveBeenCalledTimes(1);
    descargar.mockReset();
    await arrancar([{ id: 1 }], 5);
    expect(descargar).not.toHaveBeenCalled();
  });

  it('sin red espera: al volver la red descarga', async () => {
    online.set(false);
    await arrancar();
    expect(descargar).not.toHaveBeenCalled();
    online.set(true);
    TestBed.tick();
    await new Promise((r) => setTimeout(r, 20));
    expect(descargar).toHaveBeenCalledTimes(1);
  });

  it('sin sesión iniciada no descarga nada', async () => {
    autenticado.set(false);
    await arrancar();
    expect(descargar).not.toHaveBeenCalled();
  });
});
