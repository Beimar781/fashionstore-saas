import { TestBed } from '@angular/core/testing';
import { of } from 'rxjs';
import { beforeEach, describe, expect, it } from 'vitest';
import { ComprasApi } from '../api/compras.api';
import { AuthService } from '../auth/auth.service';
import { TarjetaGuardada } from '../compras.models';
import { estadoLegible } from '../offline/estado-legible';
import { LocalDbService } from '../offline/local-db.service';
import { TarjetasGuardadasService } from './tarjetas-guardadas.service';

const visa: TarjetaGuardada = { id: 7, marca: 'Visa', ultimos4: '4242', exp_mes: 12, exp_anio: 2099 };
const master: TarjetaGuardada = { id: 8, marca: 'Mastercard', ultimos4: '4444', exp_mes: 11, exp_anio: 2099 };

describe('Copia de tarjetas guardadas para comprar sin conexión (H)', () => {
  const copia = new Map<string, unknown>();
  let servidor: TarjetaGuardada[] = [];
  let service: TarjetasGuardadasService;

  beforeEach(() => {
    copia.clear(); servidor = [visa];
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({ providers: [
      { provide: ComprasApi, useValue: { tarjetas: () => of(servidor) } },
      { provide: AuthService, useValue: { sesion: () => ({ empresa: { id: 1 }, usuario: { id: 5 } }) } },
      { provide: LocalDbService, useValue: { guardarTarjetasLocal: async (k: string, v: unknown) => { copia.set(k, v); }, leerTarjetasLocal: async (k: string) => copia.get(k) } },
    ] });
    service = TestBed.inject(TarjetasGuardadasService);
  });

  it('guardar una tarjeta y apagar la red SIN reabrir el checkout: se ofrece (la copia se renueva con la lista del servidor)', async () => {
    expect(await service.locales()).toEqual([]);
    servidor = [visa, master];  // el cliente acaba de guardar la Mastercard al pagar
    await service.refrescar();
    expect((await service.locales()).map((t) => t.ultimos4)).toEqual(['4242', '4444']);
  });

  it('eliminar una tarjeta: ya no se ofrece sin conexión', async () => {
    servidor = [visa, master];
    await service.refrescar();
    await service.quitar(7);
    expect((await service.locales()).map((t) => t.id)).toEqual([8]);
  });
});

describe('Estado legible de la compra pendiente (H)', () => {
  it('con tarjeta guardada dice a cuál se cobrará; sin tarjeta, que quedará por pagar', () => {
    expect(estadoLegible({ tipo: 'COMPRA', estado: 'REGISTRADA_LOCAL', resumen: 'Compra offline: 2 prenda(s) · se cobrará a Visa terminada en 4242' })).toBe('Pendiente de enviar · se cobrará a la Visa 4242 al reconectar');
    expect(estadoLegible({ tipo: 'COMPRA', estado: 'REGISTRADA_LOCAL', resumen: 'Compra offline: 1 prenda(s)' })).toBe('Pendiente de enviar · quedará por pagar al reconectar');
    expect(estadoLegible({ tipo: 'COMPRA', estado: 'ENVIADA', resumen: '' })).toBe('Enviando al servidor…');
    expect(estadoLegible({ tipo: 'RESERVA', estado: 'REGISTRADA_LOCAL', resumen: '' })).toBe('Pendiente de enviar · se enviará al reconectar');
  });
});
