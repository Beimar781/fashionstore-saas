import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { describe, expect, it } from 'vitest';
import { Prenda } from '../catalogo.models';
import { ProductCardComponent } from './product-card.component';

const base: Prenda = {
  id: 1, publico_id: 'p1', nombre: 'Camiseta Verde Oliva Estampada', slug: 'camiseta', categoria: 'Camisetas', marca: 'Andina', genero: 'UNISEX', coleccion: '', temporada: '',
  precio: '100.00', precio_final: '100.00', promocion: null, imagen: null, colores: [], tallas: ['S', 'M', 'L'], disponible: true,
};
const colores = (n: number) => Array.from({ length: n }, (_, i) => ({ id: i + 1, nombre: `C${i}`, codigo_hex: '#123456' }));

function montar(prenda: Partial<Prenda>) {
  TestBed.configureTestingModule({ providers: [provideRouter([])] });
  const f = TestBed.createComponent(ProductCardComponent);
  f.componentRef.setInput('prenda', { ...base, ...prenda });
  f.detectChanges();
  return f.nativeElement as HTMLElement;
}

describe('Tarjeta de prenda', () => {
  it('muestra como máximo 5 colores y «+N» con el resto', () => {
    const t = montar({ colores: colores(8) });
    expect(t.querySelectorAll('.pc-colores .swatch')).toHaveLength(5);
    expect(t.querySelector('.pc-mas')?.textContent).toContain('+3');
  });

  it('sin imagen deja el recuadro del mismo tamaño, con el nombre completo en el título y la insignia de agotada', () => {
    const t = montar({ imagen: null, disponible: false });
    expect(t.querySelector('.pc-foto .pc-vacia')).toBeTruthy();
    expect(t.querySelector('.pc-nombre')?.getAttribute('title')).toBe('Camiseta Verde Oliva Estampada');
    expect(t.querySelector('.pc-agotada')?.textContent).toContain('Agotada');
  });

  it('con una foto usa el nombre como texto alternativo, y con oferta muestra el precio anterior tachado', () => {
    const t = montar({ imagen: '/media/a.jpg', promocion: 'Oferta', precio: '120.00', precio_final: '100.00' });
    expect(t.querySelector('img')?.getAttribute('alt')).toBe('Camiseta Verde Oliva Estampada');
    expect(t.querySelector('s')).toBeTruthy();
    expect(t.querySelector('.pc-oferta')).toBeTruthy();
  });
});
