import { DatePipe } from '@angular/common';
import { Component, computed, inject, input } from '@angular/core';
import { RouterLink } from '@angular/router';
import { CatalogoLocalService } from '../../core/offline/catalogo-local.service';
import { ColaOperacionesService } from '../../core/offline/cola-operaciones.service';
import { OperacionLocal, TipoOperacion } from '../../core/offline.models';

export const MSG_AGOTADA = 'La prenda se agotó mientras estaba sin conexión. No se le cobró nada.';

/** Motivo que lee el cliente: si el servidor informó una devolución de dinero se muestra tal cual; si no, el aviso de que no se cobró nada. */
export function motivoParaCliente(o: Pick<OperacionLocal, 'estado' | 'mensaje'>): string {
  if (/devolv/i.test(o.mensaje)) return o.mensaje;
  return o.estado === 'EN_CONFLICTO' ? MSG_AGOTADA : o.mensaje || 'No se pudo realizar la operación.';
}

/** Estado de la devolución del efectivo de una venta de caja con problema (la registra el Encargado al descartarla, CU-40). */
export function devolucionDeEfectivo(o: Pick<OperacionLocal, 'estado' | 'mensaje'>): string {
  if (o.estado === 'EN_CONFLICTO') return 'Pendiente: el Encargado debe reintentarla o descartarla.';
  return /devolv/i.test(o.mensaje) ? 'Efectivo devuelto al cliente.' : 'Sin devolución registrada.';
}

/**
 * Operaciones sin conexión que terminaron EN_CONFLICTO o RECHAZADA, visibles para quien las sufre en su pantalla normal:
 * el Cliente en «Mis compras» y «Mis reservas» (con el botón para elegir otra talla o sucursal) y el Cajero en Caja («Ventas con problema»).
 */
@Component({
  selector: 'app-operaciones-con-problema',
  imports: [RouterLink, DatePipe],
  template: `
    @if (operaciones().length) {
      <section class="card pad stack" role="alert">
        <h3>{{ titulo() }}</h3>
        @for (o of operaciones(); track o.id) {
          <div class="row between problema">
            <div>
              <strong>{{ o.resumen }}</strong> <span class="badge" [class.warn]="o.estado === 'EN_CONFLICTO'" [class.danger]="o.estado === 'RECHAZADA'">{{ o.estado === 'EN_CONFLICTO' ? 'En conflicto' : 'Rechazada' }}</span>
              <p class="small muted">{{ o.creada_en | date: 'dd/MM HH:mm' }} · {{ paraCliente() ? motivo(o) : o.mensaje }}</p>
              @if (!paraCliente()) { <p class="small"><strong>Devolución del efectivo:</strong> {{ devolucion(o) }}</p> }
              @if (o.detalle?.faltantes?.length) { <ul class="small">@for (f of o.detalle!.faltantes; track f.variante_id) { <li>{{ f.producto }} ({{ f.talla }}, {{ f.color }}): pidió {{ f.solicitadas }}, hay {{ f.disponibles }}</li> }</ul> }
            </div>
            @if (paraCliente()) { <a class="btn sm primary" [routerLink]="rutaPrenda(o)">Elegir otra talla o sucursal</a> }
          </div>
        }
      </section>
    }`,
  styles: `.problema + .problema { border-top: 1px solid var(--line); padding-top: .6rem; } ul { margin: .2rem 0 0; padding-left: 1.1rem; }`,
})
export class OperacionesConProblemaComponent {
  private cola = inject(ColaOperacionesService);
  private catalogo = inject(CatalogoLocalService);

  readonly tipos = input.required<TipoOperacion[]>();
  readonly titulo = input('Operaciones con problema');
  readonly paraCliente = input(false);
  readonly operaciones = computed(() => this.cola.operaciones().filter((o) => this.tipos().includes(o.tipo) && (o.estado === 'EN_CONFLICTO' || o.estado === 'RECHAZADA')));
  readonly motivo = motivoParaCliente;
  readonly devolucion = devolucionDeEfectivo;

  /** La prenda de la operación (la primera de su detalle) para que el cliente elija otra talla o sucursal; si no se conoce, el catálogo. */
  rutaPrenda(o: OperacionLocal): unknown[] {
    const varianteId = (o.payload['items'] as { variante_id: number }[] | undefined)?.[0]?.variante_id;
    const producto = this.catalogo.productos().find((p) => p.variantes.some((v) => v.id === varianteId));
    return producto ? ['/tienda/catalogo', producto.id] : ['/tienda/catalogo'];
  }
}
