import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { API_URL } from '../api.config';

export interface RegistroBitacora {
  id: number; fecha: string; empresa_id: number | null; empresa: string | null; usuario: string; rol: string | null;
  accion: string; accion_texto: string; tono: 'verde' | 'gris' | 'azul' | 'ambar' | 'rojo' | 'morado'; entidad: string; entidad_id: number | null; detalle: string; ip: string | null;
}
export interface PaginaBitacora { total: number; pagina: number; tamano: number; items: RegistroBitacora[]; }
export interface OpcionesBitacora { usuarios: string[]; entidades: string[]; acciones: { codigo: string; texto: string }[]; empresas: { id: number; nombre: string }[]; }
export interface FiltrosBitacora { usuario?: string; entidad?: string; accion?: string; desde?: string; hasta?: string; q?: string; empresa?: string; pagina?: number; tamano?: number; }

/** Bitácora del sistema (solo lectura): el Administrador ve la de su empresa; el SuperAdministrador, la de todas. */
@Injectable({ providedIn: 'root' })
export class BitacoraApi {
  private http = inject(HttpClient);

  private base(general: boolean) { return `${API_URL}${general ? '/plataforma/bitacora' : '/bitacora'}`; }

  consultar(general: boolean, f: FiltrosBitacora) {
    let params = new HttpParams();
    for (const [k, v] of Object.entries(f)) if (v !== undefined && v !== null && v !== '') params = params.set(k, String(v));
    return this.http.get<PaginaBitacora>(this.base(general), { params });
  }
  opciones(general: boolean) { return this.http.get<OpcionesBitacora>(`${this.base(general)}/opciones`); }
}
