import { describe, expect, it } from 'vitest';
import { AsistenteLocalService } from './asistente-local.service';
import { ProductoLocal } from '../offline.models';

describe('AsistenteLocalService', () => {
  it('aplica categoría, color, talla, precio máximo, promoción y stock local', () => {
    const productos: ProductoLocal[] = [{
      id: 7, empresa_id: 1, nombre: 'Camisa Oxford', categoria: 'Camisas', genero: 'UNISEX', imagen: '/media/camisa.png',
      variantes: [{ id: 11, sku: 'CAM-S-ROJ', codigo_barras: null, talla_id: 1, color_id: 2, talla: 'S', color: 'Rojo', color_hex: '#ff0000', precio: '100.00', precio_final: '80.00', promocion: 'Oferta', stock: { '4': 3 } }],
    }];
    const respuesta = new AsistenteLocalService().responder('Quiero camisas rojas talla S hasta Bs 90 con oferta', productos, 4);
    expect(respuesta.productos.map((p) => p.id)).toEqual([7]);
    expect(respuesta.respuesta).toContain('Encontré 1 prenda');
  });

  it('no ofrece una variante sin existencias en la sucursal elegida', () => {
    const producto: ProductoLocal = { id: 7, empresa_id: 1, nombre: 'Camisa Oxford', categoria: 'Camisas', genero: 'UNISEX', imagen: null, variantes: [{ id: 11, sku: 'A', codigo_barras: null, talla: 'S', color: 'Rojo', precio: '10.00', precio_final: '10.00', promocion: null, stock: { '4': 0 } }] };
    expect(new AsistenteLocalService().responder('camisa roja', [producto], 4).productos).toHaveLength(0);
  });
});
