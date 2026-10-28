import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { API_URL } from '../api.config';
import { Coleccion } from '../catalogo.models';
import { Lote, Propuesta, Proveedor, ResumenAbastecimiento, SucursalDestino, VarianteHabilitada } from '../inventario.models';

function parametros(f: object) {
  let params = new HttpParams();
  for (const [k, v] of Object.entries(f)) if (v !== undefined && v !== null && v !== '' && v !== false) params = params.set(k, String(v));
  return params;
}

/** Cliente REST de proveedores (CU-15) y abastecimiento (CU-31): avisos de remisión y propuestas de producto. */
@Injectable({ providedIn: 'root' })
export class ProveedoresApi {
  private http = inject(HttpClient);

  // CU-15
  proveedores(f: { solo_activos?: boolean; q?: string } = {}) { return this.http.get<Proveedor[]>(`${API_URL}/proveedores`, { params: parametros(f) }); }
  crearProveedor(body: unknown) { return this.http.post<Proveedor>(`${API_URL}/proveedores`, body); }
  editarProveedor(id: number, body: unknown) { return this.http.put<Proveedor>(`${API_URL}/proveedores/${id}`, body); }
  activarProveedor(id: number) { return this.http.post<Proveedor>(`${API_URL}/proveedores/${id}/activar`, {}); }
  desactivarProveedor(id: number) { return this.http.post<Proveedor>(`${API_URL}/proveedores/${id}/desactivar`, {}); }
  crearAcceso(id: number, body: unknown) { return this.http.post<Proveedor>(`${API_URL}/proveedores/${id}/acceso`, body); }
  vincularColeccion(coleccionId: number, proveedorId: number | null) {
    return this.http.put<Coleccion>(`${API_URL}/colecciones/${coleccionId}/proveedor`, { proveedor_id: proveedorId });
  }

  // CU-31
  miProveedor() { return this.http.get<Proveedor>(`${API_URL}/abastecimiento/mi-proveedor`); }
  sucursalesDestino() { return this.http.get<SucursalDestino[]>(`${API_URL}/abastecimiento/sucursales`); }
  variantes(q: string) { return this.http.get<VarianteHabilitada[]>(`${API_URL}/abastecimiento/variantes`, { params: parametros({ q }) }); }
  resumen() { return this.http.get<ResumenAbastecimiento>(`${API_URL}/abastecimiento/resumen`); }
  lotes(f: { estado?: string; proveedor_id?: number | null } = {}) { return this.http.get<Lote[]>(`${API_URL}/abastecimiento/lotes`, { params: parametros(f) }); }
  crearLote(body: unknown) { return this.http.post<Lote>(`${API_URL}/abastecimiento/lotes`, body); }
  cancelarLote(id: number) { return this.http.post<Lote>(`${API_URL}/abastecimiento/lotes/${id}/cancelar`, {}); }
  propuestas(estado = '') { return this.http.get<Propuesta[]>(`${API_URL}/abastecimiento/propuestas`, { params: parametros({ estado }) }); }
  crearPropuesta(body: unknown) { return this.http.post<Propuesta>(`${API_URL}/abastecimiento/propuestas`, body); }
  aprobarPropuesta(id: number, notas: string) { return this.http.post<Propuesta>(`${API_URL}/abastecimiento/propuestas/${id}/aprobar`, { notas }); }
  rechazarPropuesta(id: number, notas: string) { return this.http.post<Propuesta>(`${API_URL}/abastecimiento/propuestas/${id}/rechazar`, { notas }); }
}
