import { beforeEach, describe, expect, it } from 'vitest';
import { ConnectivityService } from './connectivity.service';

describe('Simular sin conexión (§B11)', () => {
  beforeEach(() => localStorage.clear());

  it('fuerza online=false aunque haya Internet y al apagarlo vuelve a true', () => {
    const red = new ConnectivityService();
    expect(red.online()).toBe(true);
    red.simular(true);
    expect(red.online()).toBe(false);
    expect(red.simulado()).toBe(true);
    red.simular(false);
    expect(red.online()).toBe(true);
  });

  it('la simulación se recuerda al recargar la página', () => {
    new ConnectivityService().simular(true);
    expect(new ConnectivityService().simulado()).toBe(true);
  });
});
