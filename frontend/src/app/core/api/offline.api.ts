import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { API_URL } from '../api.config';
import { CatalogoDescargado, OperacionServidor, RespuestaSync } from '../offline.models';

/** Cliente REST de la operación offline: CU-37 (descarga), CU-38 (sincronización), CU-39 (estado) y CU-40 (conflictos). */
@Injectable({ providedIn: 'root' })
export class OfflineApi {
  private http = inject(HttpClient);

  catalogo() { return this.http.get<CatalogoDescargado>(`${API_URL}/offline/catalogo`); }
  sincronizar(operaciones: { id: string; tipo: string; creada_en: string; sucursal_id: number | null; payload: unknown }[]) {
    return this.http.post<RespuestaSync>(`${API_URL}/offline/sincronizar`, { operaciones });
  }
  mias() { return this.http.get<OperacionServidor[]>(`${API_URL}/offline/operaciones`); }
  conflictos() { return this.http.get<OperacionServidor[]>(`${API_URL}/offline/conflictos`); }
  resolver(id: string, accion: 'REINTENTAR' | 'DESCARTAR', motivo?: string) {
    return this.http.post<OperacionServidor>(`${API_URL}/offline/conflictos/${id}/resolver`, { accion, motivo: motivo ?? null });
  }
}
