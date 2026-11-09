import { Component, computed, inject } from '@angular/core';
import { ColaOperacionesService } from '../../core/offline/cola-operaciones.service';
import { OperacionLocal } from '../../core/offline.models';

/** Resume las ventas de contado de la lista: cantidad, total, efectivo recibido, cambio y desglose por estado. Solo usa datos locales. */
export function resumirTurno(operaciones: OperacionLocal[]) {
  const ventas = operaciones.filter((o) => o.tipo === 'VENTA_CONTADO');
  const por_estado: Record<string, number> = { REGISTRADA_LOCAL: 0, ENVIADA: 0, CONFIRMADA: 0, RECHAZADA: 0, EN_CONFLICTO: 0 };
  let recibido = 0, total = 0;
  for (const v of ventas) {
    por_estado[v.estado] = (por_estado[v.estado] ?? 0) + 1;
    recibido += Number(v.payload['monto_recibido'] ?? 0);
    for (const i of (v.payload['items'] as { cantidad: number; precio_unitario?: string }[] | undefined) ?? []) total += Number(i.precio_unitario ?? 0) * i.cantidad;
  }
  return { ventas: ventas.length, recibido, total, cambio: recibido - total, por_estado };
}

const NOMBRES: Record<string, string> = { REGISTRADA_LOCAL: 'Pendientes de enviar', ENVIADA: 'Enviadas', CONFIRMADA: 'Confirmadas', RECHAZADA: 'Rechazadas', EN_CONFLICTO: 'En conflicto' };

/** B2 · «Resumen de mi turno» (Cajero y Encargado): solo lectura sobre los datos locales, funciona sin conexión; se imprime o se guarda como PDF desde el navegador. */
import { BsPipe } from '../../core/formato-bs';

@Component({
  selector: 'app-resumen-turno',
  imports: [BsPipe],
  template: `
    <div class="card pad stack" id="resumen-turno">
      <div class="row between"><h3>Resumen de mi turno</h3><button class="btn sm primary" (click)="imprimir()">Imprimir / Guardar PDF</button></div>
      @let r = resumen();
      <p><strong>{{ r.ventas }}</strong> venta(s) de contado · Total vendido <strong>{{ r.total | bs }}</strong></p>
      <p>Efectivo recibido <strong>{{ r.recibido | bs }}</strong> · Cambio entregado <strong>{{ r.cambio | bs }}</strong></p>
      <h4>Por estado de sincronización</h4>
      @for (e of estados; track e) { <div class="row between small"><span>{{ nombres[e] }}</span><strong>{{ r.por_estado[e] }}</strong></div> }
      <p class="muted small">Datos de este dispositivo. Generado por FashionStore.</p>
    </div>`,
})
export class ResumenTurnoComponent {
  private cola = inject(ColaOperacionesService);
  readonly resumen = computed(() => resumirTurno(this.cola.operaciones()));
  readonly estados = Object.keys(NOMBRES);
  readonly nombres = NOMBRES;
  imprimir() { window.print(); }
}
