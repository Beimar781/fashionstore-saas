import { describe, expect, it } from 'vitest';
import { errorDeConexion, mensajeAuthSinConexion } from './auth-offline';

describe('mensajes de autenticación sin conexión', () => {
  it('distingue el inicio, el registro y la recuperación', () => {
    expect(mensajeAuthSinConexion('iniciar sesión')).toBe(
      'Sin conexión: necesita Internet para iniciar sesión.',
    );
    expect(mensajeAuthSinConexion('crear su cuenta')).toBe(
      'Sin conexión: necesita Internet para crear su cuenta.',
    );
    expect(mensajeAuthSinConexion('recuperar su contraseña')).toBe(
      'Sin conexión: necesita Internet para recuperar su contraseña.',
    );
  });

  it('reconoce un navegador offline o una respuesta de red interrumpida', () => {
    expect(errorDeConexion({ status: 0 }, true)).toBe(true);
    expect(errorDeConexion({ status: 500 }, false)).toBe(true);
    expect(errorDeConexion({ status: 500 }, true)).toBe(false);
  });
});
