import { Injectable, inject } from '@angular/core';
import { AuthService } from '../auth/auth.service';
import { ReservaSucursalLocal } from '../offline.models';
import { ToastService } from '../ui/toast.service';
import { CatalogoLocalService } from './catalogo-local.service';
import { ColaOperacionesService } from './cola-operaciones.service';

export type MotivoAjuste = 'CONTEO' | 'MERMA' | 'DAÑO';
export const MOTIVOS_AJUSTE: { valor: MotivoAjuste; texto: string }[] = [{ valor: 'CONTEO', texto: 'Conteo físico' }, { valor: 'MERMA', texto: 'Merma' }, { valor: 'DAÑO', texto: 'Daño' }];

/**
 * Tareas de la sucursal sin conexión (B4 a B6): recepción, ajuste de inventario y atención de reservas. Cada una queda en la cola con su UUID,
 * cambia la copia local al instante y se envía sola al recuperar la red; el servidor vuelve a validar todo al sincronizar (RN11, RN12, RN14).
 * Lo usan «Tareas de la sucursal» (diagnóstico) y las pantallas normales de Inventario, Recepción y Reservas cuando no hay conexión.
 */
@Injectable({ providedIn: 'root' })
export class OperacionesSucursalService {
  private cola = inject(ColaOperacionesService);
  private local = inject(CatalogoLocalService);
  private auth = inject(AuthService);
  private toast = inject(ToastService);

  private get sucursalId() { return this.auth.sesion()?.usuario.sucursal_id ?? null; }

  async recibir(varianteId: number, cantidad: number, referencia: string, nombre: string) {
    await this.cola.registrar('RECEPCION', { variante_id: varianteId, cantidad, referencia: referencia.trim() }, this.sucursalId, `Recepción de ${cantidad}× ${nombre}`);
    await this.local.moverStock(varianteId, this.sucursalId!, cantidad);
    this.toast.ok('Recepción guardada. El inventario sube de forma provisional hasta sincronizar.');
  }

  /** El ajuste viaja como diferencia (+ o −), no como valor absoluto, para no pisar las ventas hechas mientras tanto. */
  async ajustar(varianteId: number, diferencia: number, motivo: MotivoAjuste, nota: string, nombre: string) {
    await this.cola.registrar('AJUSTE_INVENTARIO', { variante_id: varianteId, diferencia, motivo, nota: nota.trim() }, this.sucursalId, `Ajuste de ${diferencia > 0 ? '+' : ''}${diferencia}× ${nombre} (${motivo})`);
    await this.local.moverStock(varianteId, this.sucursalId!, diferencia);
    this.toast.ok('Ajuste guardado. Se enviará como diferencia al recuperar la conexión.');
  }

  private async deReserva(r: ReservaSucursalLocal, tipo: 'PREPARAR_RESERVA' | 'PRENDA_NO_ENCONTRADA' | 'ATENDER_RESERVA', resumen: string, extra: Record<string, unknown>, cambio: (m: ReservaSucursalLocal[]) => void) {
    await this.cola.registrar(tipo, { reserva_id: r.id, ...extra }, this.sucursalId, `${resumen} ${r.codigo}`);
    await this.local.actualizarExtras((m) => cambio(m.reservas_sucursal ?? []));
  }

  preparar(r: ReservaSucursalLocal) {
    return this.deReserva(r, 'PREPARAR_RESERVA', 'Preparación de la reserva', {}, (l) => { for (const x of l) if (x.id === r.id) x.estado = 'PREPARADA'; });
  }

  noEncontrada(r: ReservaSucursalLocal, itemId: number) {
    return this.deReserva(r, 'PRENDA_NO_ENCONTRADA', 'Prenda no encontrada de la reserva', { item_id: itemId }, (l) => { for (const x of l) if (x.id === r.id) for (const i of x.items) if (i.id === itemId) i.estado = 'NO_ENCONTRADO'; });
  }

  /** Atender: si el cliente lleva las prendas la reserva queda EN_PROBADOR (se cobra en Caja); si no, se completa y sale de la copia. */
  async atender(r: ReservaSucursalLocal, lleva: boolean) {
    await this.deReserva(r, 'ATENDER_RESERVA', 'Atención de la reserva', { llevara_prendas: lleva }, (l) => {
      if (lleva) { for (const x of l) if (x.id === r.id) x.estado = 'EN_PROBADOR'; } else l.splice(0, l.length, ...l.filter((x) => x.id !== r.id));
    });
    this.toast.ok(lleva ? 'Atención guardada. Cobre las prendas en Caja con el código de la reserva.' : 'Atención guardada.');
  }
}
