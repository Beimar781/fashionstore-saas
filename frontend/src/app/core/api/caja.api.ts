import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { API_URL } from '../api.config';
import { CobroCaja, ProductoCaja, ResumenDia, VentasSucursal } from '../caja.models';
import { Pedido } from '../compras.models';
import { Reserva } from '../reservas.models';

function parametros(f: object) {
  let params = new HttpParams();
  for (const [k, v] of Object.entries(f)) if (v !== undefined && v !== null && v !== '') params = params.set(k, String(v));
  return params;
}

/** Cliente REST del punto de venta: CU-28 (productos en caja), CU-29 (venta presencial), CU-30 (cobro y comprobante) y CU-27 (ventas de la sucursal). */
@Injectable({ providedIn: 'root' })
export class CajaApi {
  private http = inject(HttpClient);

  // CU-28
  buscar(q: string) { return this.http.get<ProductoCaja[]>(`${API_URL}/caja/productos`, { params: parametros({ q }) }); }
  escanear(codigo: string) { return this.http.get<ProductoCaja>(`${API_URL}/caja/productos/codigo/${encodeURIComponent(codigo)}`); }

  // CU-29
  registrarVenta(body: unknown) { return this.http.post<Pedido>(`${API_URL}/caja/ventas`, body); }
  pendientes() { return this.http.get<Pedido[]>(`${API_URL}/caja/ventas/pendientes`); }
  anular(id: number) { return this.http.delete<Pedido>(`${API_URL}/caja/ventas/${id}`); }
  reserva(codigo: string) { return this.http.get<Reserva>(`${API_URL}/caja/reservas/${encodeURIComponent(codigo)}`); }

  // CU-30
  cobrar(id: number, metodo: 'EFECTIVO', montoRecibido: number | null) {
    return this.http.post<CobroCaja>(`${API_URL}/caja/ventas/${id}/cobrar`, { metodo, monto_recibido: montoRecibido });
  }
  comprobante(id: number) { return this.http.get(`${API_URL}/caja/ventas/${id}/comprobante`, { responseType: 'blob' }); }

  // CU-27
  resumen(fecha: string) { return this.http.get<ResumenDia>(`${API_URL}/reportes/sucursal/resumen`, { params: parametros({ fecha }) }); }
  tickets(f: { desde?: string; hasta?: string; canal?: string; metodo?: string }) { return this.http.get<VentasSucursal>(`${API_URL}/reportes/sucursal/ventas`, { params: parametros(f) }); }
  ticket(id: number) { return this.http.get<Pedido>(`${API_URL}/reportes/sucursal/ventas/${id}`); }
}
