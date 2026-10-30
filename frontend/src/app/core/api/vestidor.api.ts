import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { API_URL } from '../api.config';
import { Anclaje, ColorVestidor, VestidorProducto } from '../vestidor.models';

/** Cliente REST de CU-06 (vestidor virtual): el Administrador sube el PNG de cada color; el móvil lo consulta. */
@Injectable({ providedIn: 'root' })
export class VestidorApi {
  private http = inject(HttpClient);

  producto(id: number) { return this.http.get<VestidorProducto>(`${API_URL}/vestidor/productos/${id}`); }
  subir(productoId: number, colorId: number, archivo: File, anclaje: Anclaje) {
    const datos = new FormData();
    datos.append('archivo', archivo);
    for (const [k, v] of Object.entries(anclaje)) datos.append(k, String(v));
    return this.http.put<ColorVestidor>(`${API_URL}/vestidor/productos/${productoId}/colores/${colorId}`, datos);
  }
  quitar(productoId: number, colorId: number) { return this.http.delete<void>(`${API_URL}/vestidor/productos/${productoId}/colores/${colorId}`); }
}
