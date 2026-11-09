import { Injectable } from '@angular/core';
import { Prenda } from '../catalogo.models';
import { formatoBs } from '../formato-bs';
import { ProductoLocal } from '../offline.models';

/** Respaldo por reglas del CU-07, equivalente a la intención interpretada por el backend. */
@Injectable({ providedIn: 'root' })
export class AsistenteLocalService {
  responder(texto: string, productos: ProductoLocal[], sucursal: number | null) {
    const t = this.normalizar(texto);
    const categorias = [...new Set(productos.map((p) => p.categoria))].filter((x) => this.contiene(t, x));
    const colores = [...new Set(productos.flatMap((p) => p.variantes.map((v) => v.color)))].filter((x) => this.contiene(t, x));
    const talla = /\btalla\s+([a-z0-9]{1,3})\b|\b(xs|xl|xxl)\b/.exec(t)?.slice(1).find(Boolean)?.toUpperCase();
    const max = /(?:menos de|hasta|maximo|no mas de|por debajo de|bajo)\s+(?:bs\.?\s*)?(\d+(?:[.,]\d+)?)/.exec(t)?.[1];
    const min = /(?:mas de|desde|minimo|por encima de)\s+(?:bs\.?\s*)?(\d+(?:[.,]\d+)?)/.exec(t)?.[1];
    const entre = /entre\s+(\d+(?:[.,]\d+)?)\s+y\s+(\d+(?:[.,]\d+)?)/.exec(t);
    const precioMin = entre ? Math.min(Number(entre[1].replace(',', '.')), Number(entre[2].replace(',', '.'))) : min ? Number(min.replace(',', '.')) : undefined;
    const precioMax = entre ? Math.max(Number(entre[1].replace(',', '.')), Number(entre[2].replace(',', '.'))) : max ? Number(max.replace(',', '.')) : undefined;
    const ocasion = ['formal', 'casual', 'deportiv', 'fiesta', 'oficina', 'playa', 'invierno', 'verano', 'elegante'].find((x) => t.includes(x));
    const genero = /\b(nino|nina|infantil|kids)\b/.test(t) ? 'NINOS' : /\b(mujer|dama|femenin|chica)\b/.test(t) ? 'FEMENINO' : /\b(hombre|varon|masculin|caballero|chico)\b/.test(t) ? 'MASCULINO' : null;
    const ofertas = /\b(oferta|promocion|descuento|rebaja)/.test(t);
    const filtrar = (sin: Set<string> = new Set()) => productos.filter((p) => {
      const vs = p.variantes.filter((v) => (sucursal === null ? Object.values(v.stock).some((n) => n > 0) : (v.stock[String(sucursal)] ?? 0) > 0) && (!talla || sin.has('talla') || v.talla.toLowerCase() === talla.toLowerCase()) && (!colores.length || sin.has('color') || colores.some((c) => this.normalizar(v.color) === this.normalizar(c))) && (precioMax === undefined || sin.has('precio') || Number(v.precio_final) <= precioMax) && (precioMin === undefined || sin.has('precio') || Number(v.precio_final) >= precioMin));
      return vs.length > 0 && (!categorias.length || sin.has('categoria') || categorias.includes(p.categoria)) && (!genero || p.genero === genero || p.genero === 'UNISEX') && (!ocasion || `${p.nombre} ${p.descripcion ?? ''} ${p.material ?? ''}`.toLowerCase().includes(ocasion)) && (!ofertas || vs.some((v) => !!v.promocion));
    });
    let encontrados = filtrar();
    const relajados: string[] = [];
    for (const filtro of ['precio', 'talla', 'color', 'categoria']) if (!encontrados.length) { relajados.push(filtro); encontrados = filtrar(new Set(relajados)); }
    const outfit = /\b(outfit|conjunto|combinar|combinacion|atuendo|look)\b/.test(t);
    if (outfit) encontrados = [...new Map(encontrados.map((p) => [p.categoria, p])).values()];
    const tarjetas: Prenda[] = encontrados.slice(0, 6).map((p) => {
      const v = p.variantes.find((x) => x.promocion) ?? p.variantes[0];
      return { id: p.id, publico_id: p.publico_id ?? String(p.id), nombre: p.nombre, slug: p.slug ?? String(p.id), categoria: p.categoria, marca: p.marca ?? null, genero: p.genero as Prenda['genero'], coleccion: p.coleccion ?? '', temporada: p.temporada ?? '', precio: v?.precio ?? '0', precio_final: v?.precio_final ?? '0', promocion: v?.promocion ?? null, imagen: p.imagen, colores: [], tallas: [...new Set(p.variantes.map((x) => x.talla))], disponible: true };
    });
    const detalle = [categorias, colores].flat().concat(talla ? [`talla ${talla}`] : []).concat(max ? [`hasta ${formatoBs(max)}`] : []).concat(min ? [`desde ${formatoBs(min)}`] : []).concat(ocasion ? [ocasion] : []).join(', ');
    const respuesta = tarjetas.length ? `${outfit ? 'Le armé un conjunto' : `Encontré ${tarjetas.length} prenda(s) disponible(s)`}${detalle ? ` (${detalle})` : ''}${outfit ? `: ${tarjetas.map((p) => p.nombre).join(', ')}.` : '.'}${relajados.length ? ` Amplié la búsqueda sin el filtro de ${relajados.join(', ')}.` : ''}` : ofertas ? 'No encontré ofertas con esas características.' : 'No encontré prendas con esas características.';
    return { respuesta, productos: tarjetas, sugerencias: tarjetas.length ? ['Muéstreme algo más económico', '¿Lo tiene en otro color?', ofertas ? 'Arme un outfit con esto' : 'Muéstreme las ofertas'] : ['Quiero ropa formal', 'Arme un outfit casual'] };
  }

  private normalizar(s: string) { return s.normalize('NFKD').replace(/[\u0300-\u036f]/g, '').toLowerCase().trim(); }
  private contiene(texto: string, termino: string) { const base = this.normalizar(termino); const palabras = new Set(texto.split(/\W+/)); return [base, base.replace(/s$/, ''), `${base}s`, `${base}es`].some((x) => palabras.has(x)); }
}
