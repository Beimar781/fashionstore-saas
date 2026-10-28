import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { API_URL } from '../api.config';
import { AtencionRespuesta, Notificacion, Reserva } from '../reservas.models';

function parametros(f: object) {
  let params = new HttpParams();
  for (const [k, v] of Object.entries(f)) if (v !== undefined && v !== null && v !== '') params = params.set(k, String(v));
  return params;
}

/** Cliente REST de reservas: CU-09/10 (Cliente), CU-24/25 (Encargado) y RF11 (notificaciones). */
@Injectable({ providedIn: 'root' })
export class ReservasApi {
  private http = inject(HttpClient);

  // CU-09 y CU-10 · el Cliente
  reservar(body: unknown) { return this.http.post<Reserva>(`${API_URL}/reservas`, body); }
  misReservas(estado = '') { return this.http.get<Reserva[]>(`${API_URL}/reservas`, { params: parametros({ estado }) }); }
  cancelar(id: number, motivo: string) { return this.http.post<Reserva>(`${API_URL}/reservas/${id}/cancelar`, { motivo }); }

  // CU-24 · el Encargado prepara las reservas de su sucursal
  deMiSucursal(f: { estado?: string; fecha?: string } = {}) { return this.http.get<Reserva[]>(`${API_URL}/reservas-sucursal`, { params: parametros(f) }); }
  preparar(id: number) { return this.http.post<Reserva>(`${API_URL}/reservas-sucursal/${id}/preparar`, {}); }
  noEncontrado(reservaId: number, itemId: number) { return this.http.post<Reserva>(`${API_URL}/reservas-sucursal/${reservaId}/items/${itemId}/no-encontrado`, {}); }

  // CU-25 · atención en el mostrador
  validarCodigo(codigo: string) { return this.http.post<Reserva>(`${API_URL}/atencion-reservas/validar`, { codigo }); }
  atender(id: number) { return this.http.post<Reserva>(`${API_URL}/atencion-reservas/${id}/atender`, {}); }
  completar(id: number, llevaraPrendas: boolean) { return this.http.post<AtencionRespuesta>(`${API_URL}/atencion-reservas/${id}/completar`, { llevara_prendas: llevaraPrendas }); }

  // RF11 · notificaciones
  notificaciones(soloNoLeidas = false) { return this.http.get<Notificacion[]>(`${API_URL}/notificaciones`, { params: parametros({ solo_no_leidas: soloNoLeidas || '' , limite: 30 }) }); }
  sinLeer() { return this.http.get<{ no_leidas: number }>(`${API_URL}/notificaciones/resumen`); }
  leer(id: number) { return this.http.post<Notificacion>(`${API_URL}/notificaciones/${id}/leer`, {}); }
  leerTodas() { return this.http.post<{ no_leidas: number }>(`${API_URL}/notificaciones/leer-todas`, {}); }
}
