import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { API_URL } from '../api.config';
import { Analitica, FiltroReporte, Indicadores, InteraccionCliente, MensajeChat, MiPlan, Outfit, PagosReporte, Privacidad, Recomendaciones, ReporteGenerativo, ReservasReporte, RespuestaChat, VentasReporte } from '../reportes.models';

function parametros(f: object) {
  let params = new HttpParams();
  for (const [k, v] of Object.entries(f)) if (v !== undefined && v !== null && v !== '') params = params.set(k, String(v));
  return params;
}

/** Cliente REST de la Fase G: reportes (CU-21, CU-22), IA (CU-23, CU-42, CU-07) y plan (CU-36). */
@Injectable({ providedIn: 'root' })
export class ReportesApi {
  private http = inject(HttpClient);

  ventas(f: FiltroReporte) { return this.http.get<VentasReporte>(`${API_URL}/reportes/ventas`, { params: parametros(f) }); }
  reservas(f: FiltroReporte) { return this.http.get<ReservasReporte>(`${API_URL}/reportes/reservas`, { params: parametros({ ...f, canal: undefined }) }); }
  pagos(f: FiltroReporte) { return this.http.get<PagosReporte>(`${API_URL}/reportes/pagos`, { params: parametros({ ...f, canal: undefined }) }); }
  exportar(tipo: 'ventas' | 'reservas' | 'pagos', f: FiltroReporte) {
    return this.http.get(`${API_URL}/reportes/exportar/${tipo}`, { params: parametros({ ...f, canal: undefined }), responseType: 'blob' });
  }
  indicadores(dias: number, sucursal: number | null) { return this.http.get<Indicadores>(`${API_URL}/reportes/indicadores`, { params: parametros({ dias, sucursal }) }); }

  generarReporte(prompt: string) { return this.http.post<ReporteGenerativo>(`${API_URL}/ia/reportes`, { prompt }); }
  historialReportes() { return this.http.get<ReporteGenerativo[]>(`${API_URL}/ia/reportes`); }
  analitica(sucursal: number | null) { return this.http.get<Analitica>(`${API_URL}/ia/analitica`, { params: parametros({ sucursal }) }); }

  miPlan() { return this.http.get<MiPlan>(`${API_URL}/mi-plan`); }

  chat(mensajes: MensajeChat[], sucursalId: number | null) {
    return this.http.post<RespuestaChat>(`${API_URL}/asistente/chat`, { mensajes: mensajes.map((m) => ({ rol: m.rol, texto: m.texto })), sucursal_id: sucursalId });
  }
  outfit(productoId: number | null, sucursalId: number | null) { return this.http.get<Outfit>(`${API_URL}/asistente/outfit`, { params: parametros({ producto_id: productoId, sucursal_id: sucursalId }) }); }
  interaccion(body: InteraccionCliente) { return this.http.post<{ registrada: boolean }>(`${API_URL}/asistente/interacciones`, body); }
  privacidad() { return this.http.get<Privacidad>(`${API_URL}/asistente/privacidad`); }
  fijarPrivacidad(personalizar: boolean) { return this.http.put<Privacidad>(`${API_URL}/asistente/privacidad`, { personalizar }); }
  borrarHistorial() { return this.http.delete<Privacidad>(`${API_URL}/asistente/historial`); }
  recomendaciones(sucursalId: number | null) { return this.http.get<Recomendaciones>(`${API_URL}/asistente/recomendaciones`, { params: parametros({ sucursal_id: sucursalId, limite: 6 }) }); }
}
