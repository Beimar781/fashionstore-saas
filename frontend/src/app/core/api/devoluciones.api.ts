import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { API_URL } from '../api.config';
import { ConfiguracionDevolucion, Devolucion, VentaDevolvible } from '../devoluciones.models';

/** Cliente REST de CU-41 (devoluciones y cambios). */
@Injectable({ providedIn: 'root' })
export class DevolucionesApi {
  private http = inject(HttpClient);

  venta(comprobante: string) { return this.http.get<VentaDevolvible>(`${API_URL}/devoluciones/venta`, { params: new HttpParams().set('comprobante', comprobante) }); }
  iniciarDiferencia(body: unknown) { return this.http.post<unknown>(`${API_URL}/devoluciones/diferencia`, body); }
  registrar(body: unknown) { return this.http.post<Devolucion>(`${API_URL}/devoluciones`, body); }
  listar(f: { desde?: string; hasta?: string } = {}) {
    let params = new HttpParams();
    if (f.desde) params = params.set('desde', f.desde);
    if (f.hasta) params = params.set('hasta', f.hasta);
    return this.http.get<Devolucion[]>(`${API_URL}/devoluciones`, { params });
  }
  nota(id: number) { return this.http.get(`${API_URL}/devoluciones/${id}/nota`, { responseType: 'blob' }); }
  plazo() { return this.http.get<ConfiguracionDevolucion>(`${API_URL}/devoluciones/configuracion`); }
  fijarPlazo(plazo_dias: number) { return this.http.put<ConfiguracionDevolucion>(`${API_URL}/devoluciones/configuracion`, { plazo_dias }); }
}
