import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { API_URL } from '../api.config';
import { Disponibilidad, Existencia, FiltrosInventario, InventarioPagina, Lote, MovimientosPagina } from '../inventario.models';

function parametros(f: object) {
  let params = new HttpParams();
  for (const [k, v] of Object.entries(f)) if (v !== undefined && v !== null && v !== '' && v !== false) params = params.set(k, String(v));
  return params;
}

/** Cliente REST del inventario: CU-05 (disponibilidad por sucursal), CU-20 (global) y CU-26 (sucursal del Encargado). */
@Injectable({ providedIn: 'root' })
export class InventarioApi {
  private http = inject(HttpClient);

  disponibilidad(productoId: number) { return this.http.get<Disponibilidad>(`${API_URL}/inventario/productos/${productoId}/disponibilidad`); }
  global(f: FiltrosInventario) { return this.http.get<InventarioPagina>(`${API_URL}/inventario/global`, { params: parametros(f) }); }
  deMiSucursal(f: FiltrosInventario) { return this.http.get<InventarioPagina>(`${API_URL}/inventario/sucursal`, { params: parametros(f) }); }
  ajustar(body: unknown) { return this.http.post<Existencia>(`${API_URL}/inventario/sucursal/movimientos`, body); }
  fijarUmbral(varianteId: number, umbral: number) {
    return this.http.put<Existencia>(`${API_URL}/inventario/sucursal/variantes/${varianteId}/umbral`, { umbral_minimo: umbral });
  }
  movimientos(f: { sucursal?: number | null; variante_id?: number | null; tipo?: string; desde?: string; hasta?: string; pagina?: number }) {
    return this.http.get<MovimientosPagina>(`${API_URL}/inventario/movimientos`, { params: parametros(f) });
  }
  recepciones() { return this.http.get<Lote[]>(`${API_URL}/inventario/recepciones`); }
  recibir(loteId: number, items: { item_id: number; cantidad_recibida: number }[]) {
    return this.http.post<Lote>(`${API_URL}/inventario/recepciones/${loteId}/recibir`, { items });
  }
}
