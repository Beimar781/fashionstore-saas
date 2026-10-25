import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { API_URL } from '../api.config';
import { Empresa, Plan, PlanGuardado, Suscripcion, SuscripcionDetalle } from '../models';

/** Cliente REST del paquete Plataforma SaaS (CU-33, CU-34, CU-35). */
@Injectable({ providedIn: 'root' })
export class PlataformaApi {
  private http = inject(HttpClient);
  private base = `${API_URL}/plataforma`;

  // CU-33
  empresas() { return this.http.get<Empresa[]>(`${this.base}/empresas`); }
  registrarEmpresa(body: unknown) { return this.http.post<Empresa>(`${this.base}/empresas`, body); }
  editarEmpresa(id: number, body: unknown) { return this.http.put<Empresa>(`${this.base}/empresas/${id}`, body); }
  suspenderEmpresa(id: number) { return this.http.post<Empresa>(`${this.base}/empresas/${id}/suspender`, {}); }
  reactivarEmpresa(id: number) { return this.http.post<Empresa>(`${this.base}/empresas/${id}/reactivar`, {}); }

  // CU-34
  planes() { return this.http.get<Plan[]>(`${this.base}/planes`); }
  crearPlan(body: unknown) { return this.http.post<PlanGuardado>(`${this.base}/planes`, body); }
  modificarPlan(id: number, body: unknown) { return this.http.put<PlanGuardado>(`${this.base}/planes/${id}`, body); }
  inactivarPlan(id: number) { return this.http.post<Plan>(`${this.base}/planes/${id}/inactivar`, {}); }

  // CU-35
  suscripcion(empresaId: number) { return this.http.get<SuscripcionDetalle>(`${this.base}/empresas/${empresaId}/suscripcion`); }
  asignarPlan(empresaId: number, body: unknown) { return this.http.post<Suscripcion>(`${this.base}/empresas/${empresaId}/suscripciones`, body); }
  suspenderSuscripcion(empresaId: number, estado: 'SUSPENDIDA' | 'CANCELADA') {
    return this.http.post<Suscripcion>(`${this.base}/empresas/${empresaId}/suscripcion/suspender`, { estado });
  }
}
