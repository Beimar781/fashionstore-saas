import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { API_URL } from '../api.config';
import { FiltrosCatalogo, Opciones, Pagina, Prenda, PrendaDetalle, SucursalCatalogo } from '../catalogo.models';

/** Cliente REST del catálogo para el Cliente: CU-03 (consultar), CU-04 (buscar y filtrar) y las opciones color × talla. */
@Injectable({ providedIn: 'root' })
export class CatalogoApi {
  private http = inject(HttpClient);

  buscar(f: FiltrosCatalogo) {
    let params = new HttpParams();
    for (const [k, v] of Object.entries(f)) if (v !== undefined && v !== null && v !== '' && v !== false) params = params.set(k, String(v));
    return this.http.get<Pagina<Prenda>>(`${API_URL}/catalogo/buscar`, { params });
  }
  prenda(id: number, sucursal: number | null) { return this.http.get<PrendaDetalle>(`${API_URL}/catalogo/productos/${id}`, { params: this.sucursal(sucursal) }); }
  opciones(id: number, sucursal: number | null) { return this.http.get<Opciones>(`${API_URL}/catalogo/productos/${id}/opciones`, { params: this.sucursal(sucursal) }); }
  sucursales() { return this.http.get<SucursalCatalogo[]>(`${API_URL}/catalogo/sucursales`); }

  private sucursal(id: number | null) { return id === null ? new HttpParams() : new HttpParams().set('sucursal', id); }
}
