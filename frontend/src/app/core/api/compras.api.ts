import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { API_URL } from '../api.config';
import { Carrito, ConfigPago, Historial, IniciarPago, Pedido, ResultadoPago, TarjetaGuardada, TarjetaSimulada } from '../compras.models';

/** Cliente REST de la compra digital: carrito (CU-08), checkout (CU-11), historial (CU-12) y pago electrónico (CU-32). */
@Injectable({ providedIn: 'root' })
export class ComprasApi {
  private http = inject(HttpClient);

  // CU-08
  carrito() { return this.http.get<Carrito>(`${API_URL}/carrito`); }
  agregar(varianteId: number, cantidad: number, sucursalId: number | null) {
    return this.http.post<Carrito>(`${API_URL}/carrito/items`, { variante_id: varianteId, cantidad, sucursal_id: sucursalId });
  }
  cambiarCantidad(itemId: number, cantidad: number) { return this.http.put<Carrito>(`${API_URL}/carrito/items/${itemId}`, { cantidad }); }
  quitar(itemId: number) { return this.http.delete<Carrito>(`${API_URL}/carrito/items/${itemId}`); }
  elegirSucursal(sucursalId: number) { return this.http.put<Carrito>(`${API_URL}/carrito/sucursal`, { sucursal_id: sucursalId }); }
  vaciar() { return this.http.delete<Carrito>(`${API_URL}/carrito`); }

  // CU-11
  checkout(body: unknown) { return this.http.post<Pedido>(`${API_URL}/compras/checkout`, body); }

  // CU-12
  compras(estado = '') { return this.http.get<Historial>(`${API_URL}/compras`, { params: estado ? new HttpParams().set('estado', estado) : undefined }); }
  compra(id: number) { return this.http.get<Pedido>(`${API_URL}/compras/${id}`); }
  comprobante(id: number) { return this.http.get(`${API_URL}/compras/${id}/comprobante`, { responseType: 'blob' }); }

  // CU-32
  configPago() { return this.http.get<ConfigPago>(`${API_URL}/pagos/config`); }
  tarjetas() { return this.http.get<TarjetaGuardada[]>(`${API_URL}/pagos/tarjetas`); }
  eliminarTarjeta(id: number) { return this.http.delete<void>(`${API_URL}/pagos/tarjetas/${id}`); }
  iniciarPago(pedidoId: number, tarjetaGuardadaId: number | null, guardarTarjeta: boolean) {
    return this.http.post<IniciarPago>(`${API_URL}/pagos/pedidos/${pedidoId}/iniciar`, { tarjeta_guardada_id: tarjetaGuardadaId, guardar_tarjeta: guardarTarjeta });
  }
  confirmarPago(pagoId: number, tarjeta: TarjetaSimulada | null) { return this.http.post<ResultadoPago>(`${API_URL}/pagos/${pagoId}/confirmar`, { tarjeta }); }
  reconciliarPago(pagoId: number) { return this.http.post<ResultadoPago>(`${API_URL}/pagos/${pagoId}/reconciliar`, {}); }
}
