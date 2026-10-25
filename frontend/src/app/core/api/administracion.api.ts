import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { API_URL } from '../api.config';
import { Ciudad, Sucursal, SucursalesRespuesta, Usuario } from '../models';

/** Cliente REST de administración de empresa: usuarios (CU-13) y ciudades/sucursales (CU-14). */
@Injectable({ providedIn: 'root' })
export class AdministracionApi {
  private http = inject(HttpClient);

  usuarios() { return this.http.get<Usuario[]>(`${API_URL}/usuarios`); }
  registrarUsuario(body: unknown) { return this.http.post<Usuario>(`${API_URL}/usuarios`, body); }
  editarUsuario(id: number, body: unknown) { return this.http.put<Usuario>(`${API_URL}/usuarios/${id}`, body); }
  desactivarUsuario(id: number) { return this.http.post<Usuario>(`${API_URL}/usuarios/${id}/desactivar`, {}); }

  sucursales() { return this.http.get<SucursalesRespuesta>(`${API_URL}/sucursales`); }
  crearSucursal(body: unknown) { return this.http.post<Sucursal>(`${API_URL}/sucursales`, body); }
  editarSucursal(id: number, body: unknown) { return this.http.put<Sucursal>(`${API_URL}/sucursales/${id}`, body); }
  activarSucursal(id: number) { return this.http.post<Sucursal>(`${API_URL}/sucursales/${id}/activar`, {}); }
  desactivarSucursal(id: number) { return this.http.post<Sucursal>(`${API_URL}/sucursales/${id}/desactivar`, {}); }

  ciudades() { return this.http.get<Ciudad[]>(`${API_URL}/ciudades`); }
  crearCiudad(body: unknown) { return this.http.post<Ciudad>(`${API_URL}/ciudades`, body); }
}
