import { Categoria, GrupoTalla } from '../../../core/catalogo.models';

/** Tallas del grupo de una categoría; si no tiene uno propio, el de su categoría padre (igual que el backend). */
export function tallasDeCategoria(categorias: Categoria[], grupos: GrupoTalla[], categoriaId: number | null) {
  let c = categorias.find((x) => x.id === categoriaId);
  while (c && c.grupo_talla_id === null) {
    const padre: number | null = c.padre_id;
    c = padre === null ? undefined : categorias.find((x) => x.id === padre);
  }
  return grupos.find((g) => g.id === c?.grupo_talla_id)?.tallas ?? [];
}

/** Agrega o quita un id de una lista de selección (chips de tallas y colores). */
export function alternar(lista: number[], id: number) {
  const i = lista.indexOf(id);
  if (i >= 0) lista.splice(i, 1); else lista.push(id);
}
