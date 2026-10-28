import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { API_URL } from '../api.config';
import {
  Categoria, Coleccion, ColorCatalogo, GrupoTalla, Marca, Pagina, ProductoDetalle, ProductoResumen, Promocion, Talla, Temporada,
  VariantesGeneradas, Variante, ImagenProducto,
} from '../catalogo.models';

/** Cliente REST de la administración del catálogo: CU-16 (atributos), CU-17 (temporadas), CU-18 (productos) y CU-19 (promociones). */
@Injectable({ providedIn: 'root' })
export class CatalogoAdminApi {
  private http = inject(HttpClient);

  // CU-16
  categorias() { return this.http.get<Categoria[]>(`${API_URL}/categorias`); }
  crearCategoria(body: unknown) { return this.http.post<Categoria>(`${API_URL}/categorias`, body); }
  editarCategoria(id: number, body: unknown) { return this.http.put<Categoria>(`${API_URL}/categorias/${id}`, body); }
  eliminarCategoria(id: number) { return this.http.delete<void>(`${API_URL}/categorias/${id}`); }

  grupos() { return this.http.get<GrupoTalla[]>(`${API_URL}/grupos-talla`); }
  crearGrupo(body: unknown) { return this.http.post<GrupoTalla>(`${API_URL}/grupos-talla`, body); }
  eliminarGrupo(id: number) { return this.http.delete<void>(`${API_URL}/grupos-talla/${id}`); }
  crearTalla(body: unknown) { return this.http.post<Talla>(`${API_URL}/tallas`, body); }
  editarTalla(id: number, body: unknown) { return this.http.put<Talla>(`${API_URL}/tallas/${id}`, body); }
  eliminarTalla(id: number) { return this.http.delete<void>(`${API_URL}/tallas/${id}`); }

  colores() { return this.http.get<ColorCatalogo[]>(`${API_URL}/colores`); }
  crearColor(body: unknown) { return this.http.post<ColorCatalogo>(`${API_URL}/colores`, body); }
  editarColor(id: number, body: unknown) { return this.http.put<ColorCatalogo>(`${API_URL}/colores/${id}`, body); }
  eliminarColor(id: number) { return this.http.delete<void>(`${API_URL}/colores/${id}`); }

  marcas() { return this.http.get<Marca[]>(`${API_URL}/marcas`); }
  crearMarca(body: unknown) { return this.http.post<Marca>(`${API_URL}/marcas`, body); }
  eliminarMarca(id: number) { return this.http.delete<void>(`${API_URL}/marcas/${id}`); }

  // CU-17
  temporadas() { return this.http.get<Temporada[]>(`${API_URL}/temporadas`); }
  crearTemporada(body: unknown) { return this.http.post<Temporada>(`${API_URL}/temporadas`, body); }
  editarTemporada(id: number, body: unknown) { return this.http.put<Temporada>(`${API_URL}/temporadas/${id}`, body); }
  eliminarTemporada(id: number) { return this.http.delete<void>(`${API_URL}/temporadas/${id}`); }
  colecciones() { return this.http.get<Coleccion[]>(`${API_URL}/colecciones`); }
  crearColeccion(body: unknown) { return this.http.post<Coleccion>(`${API_URL}/colecciones`, body); }
  editarColeccion(id: number, body: unknown) { return this.http.put<Coleccion>(`${API_URL}/colecciones/${id}`, body); }
  eliminarColeccion(id: number) { return this.http.delete<void>(`${API_URL}/colecciones/${id}`); }

  // CU-18
  productos(f: { q?: string; categoria_id?: number | null; activo?: boolean | null; pagina?: number; tamano?: number }) {
    let params = new HttpParams();
    for (const [k, v] of Object.entries(f)) if (v !== undefined && v !== null && v !== '') params = params.set(k, String(v));
    return this.http.get<Pagina<ProductoResumen>>(`${API_URL}/productos`, { params });
  }
  producto(id: number) { return this.http.get<ProductoDetalle>(`${API_URL}/productos/${id}`); }
  crearProducto(body: unknown) { return this.http.post<ProductoDetalle>(`${API_URL}/productos`, body); }
  editarProducto(id: number, body: unknown) { return this.http.put<ProductoDetalle>(`${API_URL}/productos/${id}`, body); }
  activarProducto(id: number) { return this.http.post<ProductoDetalle>(`${API_URL}/productos/${id}/activar`, {}); }
  desactivarProducto(id: number) { return this.http.post<ProductoDetalle>(`${API_URL}/productos/${id}/desactivar`, {}); }
  generarVariantes(id: number, body: unknown) { return this.http.post<VariantesGeneradas>(`${API_URL}/productos/${id}/variantes`, body); }
  editarVariante(productoId: number, id: number, body: unknown) { return this.http.put<Variante>(`${API_URL}/productos/${productoId}/variantes/${id}`, body); }
  subirImagen(id: number, archivo: File, colorId: number | null, textoAlt: string) {
    const datos = new FormData();
    datos.append('archivo', archivo);
    if (colorId !== null) datos.append('color_id', String(colorId));
    datos.append('texto_alt', textoAlt);
    return this.http.post<ImagenProducto>(`${API_URL}/productos/${id}/imagenes`, datos);
  }
  imagenPrincipal(id: number, imagenId: number) { return this.http.post<ProductoDetalle>(`${API_URL}/productos/${id}/imagenes/${imagenId}/principal`, {}); }
  eliminarImagen(id: number, imagenId: number) { return this.http.delete<void>(`${API_URL}/productos/${id}/imagenes/${imagenId}`); }

  // CU-19
  promociones() { return this.http.get<Promocion[]>(`${API_URL}/promociones`); }
  crearPromocion(body: unknown) { return this.http.post<Promocion>(`${API_URL}/promociones`, body); }
  editarPromocion(id: number, body: unknown) { return this.http.put<Promocion>(`${API_URL}/promociones/${id}`, body); }
  eliminarPromocion(id: number) { return this.http.delete<void>(`${API_URL}/promociones/${id}`); }
}
