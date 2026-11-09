// @ts-ignore: las pruebas corren en Node y el proyecto no incluye los tipos de Node
import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';

const manifiesto = JSON.parse(readFileSync('public/manifest.webmanifest', 'utf-8'));
const configuracionSw = JSON.parse(readFileSync('ngsw-config.json', 'utf-8'));

describe('PWA instalable (§5.2)', () => {
  it('el manifiesto trae nombre, nombre corto, inicio, modo standalone y colores', () => {
    expect(manifiesto.name).toBeTruthy();
    expect(manifiesto.short_name).toBeTruthy();
    expect(manifiesto.start_url).toBe('/');
    expect(manifiesto.display).toBe('standalone');
    expect(manifiesto.theme_color).toMatch(/^#/);
    expect(manifiesto.background_color).toMatch(/^#/);
  });

  it('tiene íconos de 192 y 512 y uno maskable', () => {
    const tamanos = manifiesto.icons.map((i: { sizes: string }) => i.sizes);
    expect(tamanos).toContain('192x192');
    expect(tamanos).toContain('512x512');
    expect(manifiesto.icons.some((i: { purpose: string }) => i.purpose === 'maskable')).toBe(true);
  });

  it('la página de respaldo sin conexión se guarda junto con la app', () => {
    const archivos: string[] = configuracionSw.assetGroups[0].resources.files;
    expect(archivos).toContain('/sin-conexion.html');
  });
});
